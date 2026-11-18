import datetime
from typing import Tuple, Optional, List, Dict, Any
from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
from app.models import Profile, User
from app.schemas.profile import ProfileUpdate, ProfileResponse
from app.schemas.resume import ResumeUploadResponse, ProfileReviewApprovalRequest, ResumeExtractedData
from app.services.resume_storage import ResumeStorageService
from app.services.resume_parser import ResumeParserService

class ProfileService:
    @staticmethod
    def calculate_completion(profile: Profile) -> int:
        score = 0
        if profile.full_name:
            score += 10
        if (profile.career_interests and len(profile.career_interests) > 0) or profile.profession:
            score += 10
        if profile.headline:
            score += 10
        if profile.skills and len(profile.skills) > 0:
            score += 20
        if profile.preferred_roles and len(profile.preferred_roles) > 0:
            score += 15
        if profile.total_experience_years is not None:
            score += 15
        if profile.work_arrangements and len(profile.work_arrangements) > 0:
            score += 10
        if profile.work_experience and len(profile.work_experience) > 0:
            score += 10
        if profile.education and len(profile.education) > 0:
            score += 10
        if profile.resume_storage_path:
            score += 10
        return min(score, 100)

    @classmethod
    def get_or_create_profile(cls, db: Session, user: User) -> Profile:
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        if not profile:
            profile = Profile(
                user_id=user.id,
                skills=[],
                preferred_roles=[],
                career_interests=[],
                recent_searches=[],
                preferred_countries=[],
                preferred_locations=[],
                work_arrangements=[],
                employment_types=[],
                profile_completion_pct=10
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        return profile

    @classmethod
    def update_profile(cls, db: Session, user: User, profile_in: ProfileUpdate) -> Profile:
        profile = cls.get_or_create_profile(db, user)
        update_data = profile_in.model_dump(exclude_unset=True)

        # Synchronize career_interests and primary profession
        if "career_interests" in update_data and update_data["career_interests"]:
            first_interest = update_data["career_interests"][0]
            if isinstance(first_interest, dict) and "profession" in first_interest:
                if not update_data.get("profession"):
                    update_data["profession"] = first_interest["profession"]

        for field, value in update_data.items():
            setattr(profile, field, value)

        profile.profile_completion_pct = cls.calculate_completion(profile)
        profile.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        db.refresh(profile)
        return profile

    @classmethod
    def upload_resume(cls, db: Session, user: User, file: UploadFile) -> Tuple[Profile, str, Dict[str, Any], Dict[str, Any], List[str], str]:
        profile = cls.get_or_create_profile(db, user)
        
        # Delete old resume if present
        if profile.resume_storage_path:
            ResumeStorageService.delete_resume_file(profile.resume_storage_path)

        original_name, storage_path, _ = ResumeStorageService.save_resume(file, user.id)

        try:
            content_bytes = ResumeStorageService.read_resume_content(storage_path)
            raw_text = ResumeParserService.extract_text_from_file(content_bytes, original_name)
            extracted_data = ResumeParserService.parse_resume_data(raw_text)
        except Exception:
            # Safely handle unparseable, empty, encrypted, or image-only documents without deleting uploaded resume file
            raw_text = ""
            extracted_data = ResumeParserService.parse_resume_data("")

        # Capture existing profile data snapshot
        existing_data = {
            "full_name": profile.full_name,
            "headline": profile.headline,
            "phone_number": profile.phone_number,
            "current_location": profile.current_location,
            "profession": profile.profession,
            "skills": list(profile.skills or []),
            "preferred_roles": list(profile.preferred_roles or []),
            "total_experience_years": float(profile.total_experience_years) if profile.total_experience_years is not None else None,
            "work_experience": list(profile.work_experience or []),
            "education": list(profile.education or []),
            "projects": list(profile.projects or []),
            "certifications": list(profile.certifications or [])
        }

        # Detect conflicts between extracted data and existing profile
        conflicts = ResumeParserService.detect_conflicts(extracted_data, existing_data)

        # Persist extracted data without destructively overwriting user's manually entered fields
        profile.resume_filename = original_name
        profile.resume_storage_path = storage_path
        profile.resume_uploaded_at = datetime.datetime.now(datetime.timezone.utc)
        profile.extracted_resume_data = extracted_data
        profile.profile_completion_pct = cls.calculate_completion(profile)
        
        db.commit()
        db.refresh(profile)

        # Generate signed download token
        token = ResumeStorageService.generate_signed_download_token(user.id, original_name)
        download_url = f"/api/v1/profile/resume/download?token={token}"
        raw_preview = raw_text[:1200] if raw_text else ""
        return profile, download_url, extracted_data, existing_data, conflicts, raw_preview

    @classmethod
    def approve_extracted_profile(cls, db: Session, user: User, request: ProfileReviewApprovalRequest) -> Profile:
        profile = cls.get_or_create_profile(db, user)

        if request.full_name is not None and request.full_name.strip():
            profile.full_name = request.full_name.strip()
        if request.headline is not None and request.headline.strip():
            profile.headline = request.headline.strip()
        if request.phone_number is not None and request.phone_number.strip():
            profile.phone_number = request.phone_number.strip()
        if request.current_location is not None and request.current_location.strip():
            profile.current_location = request.current_location.strip()
        
        if request.skills is not None:
            seen = set()
            unique_skills = []
            for s in request.skills:
                if s and isinstance(s, str):
                    s_clean = s.strip()
                    if s_clean and s_clean.lower() not in seen:
                        seen.add(s_clean.lower())
                        unique_skills.append(s_clean)
            profile.skills = unique_skills

        if request.preferred_roles is not None:
            seen = set()
            unique_roles = []
            for r in request.preferred_roles:
                if r and isinstance(r, str):
                    r_clean = r.strip()
                    if r_clean and r_clean.lower() not in seen:
                        seen.add(r_clean.lower())
                        unique_roles.append(r_clean)
            profile.preferred_roles = unique_roles

        if request.profession is not None and request.profession.strip():
            profile.profession = request.profession.strip()
        if request.total_experience_years is not None:
            profile.total_experience_years = float(request.total_experience_years)
        if request.work_experience is not None:
            profile.work_experience = request.work_experience
        if request.education is not None:
            profile.education = request.education
        if request.projects is not None:
            profile.projects = request.projects
        if request.certifications is not None:
            profile.certifications = request.certifications

        # Synchronize career_interests
        if not profile.career_interests and profile.profession:
            profile.career_interests = [{
                "profession": profile.profession,
                "preferred_roles": profile.preferred_roles or [],
                "skills": profile.skills or [],
                "experience_years": profile.total_experience_years
            }]
        elif profile.career_interests and isinstance(profile.career_interests, list) and len(profile.career_interests) > 0:
            first = dict(profile.career_interests[0])
            if profile.profession:
                first["profession"] = profile.profession
            if profile.skills:
                first["skills"] = profile.skills
            if profile.preferred_roles:
                first["preferred_roles"] = profile.preferred_roles
            if profile.total_experience_years is not None:
                first["experience_years"] = profile.total_experience_years
            profile.career_interests = [first] + profile.career_interests[1:]

        profile.profile_completion_pct = cls.calculate_completion(profile)
        profile.updated_at = datetime.datetime.now(datetime.timezone.utc)
        db.commit()
        db.refresh(profile)
        return profile

    @classmethod
    def delete_resume(cls, db: Session, user: User) -> Profile:
        profile = cls.get_or_create_profile(db, user)
        if profile.resume_storage_path:
            ResumeStorageService.delete_resume_file(profile.resume_storage_path)
            profile.resume_filename = None
            profile.resume_storage_path = None
            profile.resume_uploaded_at = None
            profile.extracted_resume_data = {}
            profile.profile_completion_pct = cls.calculate_completion(profile)
            db.commit()
            db.refresh(profile)
        return profile
