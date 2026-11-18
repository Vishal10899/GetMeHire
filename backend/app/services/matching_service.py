import re
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_
from app.models import Job, User, Profile, Company, Source, SavedJob
from app.schemas.job import JobListResponseItem
from app.schemas.recommendation import MatchBreakdown, RecommendationItem, RecommendationResponse
from app.ingestion.taxonomy import TAXONOMY_FAMILIES, resolve_profession_key

class MatchingService:
    VERSION = "v2.0-evidence-based-matching"

    @classmethod
    def calculate_match(
        cls,
        profile: Profile,
        job: Job,
        scoped_skills: Optional[List[str]] = None,
        scoped_roles: Optional[List[str]] = None,
        scoped_exp: Optional[float] = None,
        target_profession: Optional[str] = None
    ) -> MatchBreakdown:
        reasons: List[str] = []

        # Candidate attributes
        cand_raw_skills = scoped_skills if scoped_skills is not None else (profile.skills or [])
        candidate_skills = [s.strip() for s in cand_raw_skills if s and isinstance(s, str) and s.strip()]
        candidate_skills_lower = {s.lower() for s in candidate_skills}

        cand_raw_roles = scoped_roles if scoped_roles is not None else (profile.preferred_roles or [])
        preferred_roles = [r.strip() for r in cand_raw_roles if r and isinstance(r, str) and r.strip()]
        preferred_roles_lower = [r.lower() for r in preferred_roles]

        user_exp = scoped_exp if scoped_exp is not None else (profile.relevant_experience_years if profile.relevant_experience_years is not None else profile.total_experience_years)
        active_prof = target_profession or profile.profession

        candidate_arrangements = {a.upper().strip() for a in (profile.work_arrangements or []) if a and isinstance(a, str) and a.strip()}
        candidate_locations = [loc.strip() for loc in (profile.preferred_locations or []) + (profile.preferred_countries or []) if loc and isinstance(loc, str) and loc.strip()]

        # -------------------------------------------------------------------
        # Guard: Check for Sufficient Meaningful Information
        # Missing candidate information must not earn positive matching points.
        # -------------------------------------------------------------------
        has_meaningful_info = bool(
            candidate_skills or preferred_roles or active_prof or (user_exp is not None) or candidate_arrangements or candidate_locations
        )

        if not has_meaningful_info:
            return MatchBreakdown(
                skill_score=0.0,
                role_score=0.0,
                location_score=0.0,
                experience_score=0.0,
                total_score=0.0,
                matched_skills=[],
                missing_skills=[],
                reasons=[],
                has_sufficient_data=False,
                insufficient_data_reasons=[
                    "Candidate profile does not contain skills, preferred roles, or location preferences. Add details in your profile to compute match scores."
                ],
                location_eligibility="Unknown",
                experience_alignment="Unknown",
                score_disclaimer="Match scores reflect qualification fit and profile alignment; they do not indicate hiring probability."
            )

        # -------------------------------------------------------------------
        # Dimension 1: Skills & Technologies (Max 40.0 pts)
        # -------------------------------------------------------------------
        skill_score = 0.0
        matched_skills: List[str] = []
        missing_skills: List[str] = []

        job_raw_skills = job.skills or []
        job_skills = [s.strip() for s in job_raw_skills if s and isinstance(s, str) and s.strip()]
        job_skills_lower = {s.lower(): s for s in job_skills}

        if candidate_skills_lower and job_skills_lower:
            matched_keys = candidate_skills_lower.intersection(job_skills_lower.keys())
            matched_skills = [job_skills_lower[k] for k in matched_keys]
            missing_skills = [v for k, v in job_skills_lower.items() if k not in candidate_skills_lower]

            overlap_ratio = len(matched_keys) / len(job_skills_lower)
            skill_score = round(min(40.0, overlap_ratio * 40.0), 1)

            if matched_skills:
                reasons.append(f"Matched {len(matched_skills)} of {len(job_skills)} core skills: {', '.join(matched_skills[:4])}")
            if missing_skills:
                reasons.append(f"Missing {len(missing_skills)} required skill(s): {', '.join(missing_skills[:3])}")
            if not matched_skills:
                reasons.append(f"No required skills matched (missing: {', '.join(missing_skills[:3])})")
        elif candidate_skills_lower and not job_skills_lower:
            # Job did not list skills in job.skills array. Look for candidate skills mentioned in description
            desc_lower = (job.description or "").lower()
            found_in_desc = []
            for s in candidate_skills:
                if len(s) > 1 and re.search(r"\b" + re.escape(s.lower()) + r"\b", desc_lower):
                    found_in_desc.append(s)
            if found_in_desc:
                matched_skills = found_in_desc[:5]
                skill_score = round(min(40.0, len(found_in_desc) * 10.0), 1)
                reasons.append(f"Matched {len(found_in_desc)} skill(s) mentioned in job listing: {', '.join(found_in_desc[:3])}")
            else:
                skill_score = 0.0
                reasons.append("Job description does not specify technical skill requirements (neutral)")
        elif not candidate_skills_lower and job_skills_lower:
            skill_score = 0.0
            missing_skills = job_skills[:5]
            reasons.append(f"Add skills to profile (job seeks: {', '.join(job_skills[:3])})")
        else:
            skill_score = 0.0

        # -------------------------------------------------------------------
        # Dimension 2: Title & Career Track Alignment (Max 25.0 pts)
        # -------------------------------------------------------------------
        role_score = 0.0
        job_title_lower = (job.normalized_title or job.title or "").lower()

        # 2a. Career Track Alignment (Max 10 pts)
        if active_prof and job.profession:
            cand_prof_key = resolve_profession_key(active_prof)
            job_prof_key = resolve_profession_key(job.profession)
            if cand_prof_key == job_prof_key:
                role_score += 10.0
                reasons.append(f"Direct match with your '{cand_prof_key.replace('_', ' ').title()}' career track")
            else:
                reasons.append(f"Different career track ({job_prof_key.replace('_', ' ').title()} vs {cand_prof_key.replace('_', ' ').title()})")

        # 2b. Role / Title Match (Max 15 pts)
        if preferred_roles_lower:
            exact_role_match = None
            for pr in preferred_roles_lower:
                if pr in job_title_lower or job_title_lower in pr:
                    exact_role_match = pr
                    break

            if exact_role_match:
                role_score += 15.0
                reasons.append(f"Title directly matches preferred role '{exact_role_match.title()}'")
            else:
                title_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", job_title_lower))
                keyword_match = None
                for pr in preferred_roles_lower:
                    pr_words = set(re.findall(r"\b[a-zA-Z]{4,}\b", pr))
                    common = title_words.intersection(pr_words)
                    if common:
                        keyword_match = list(common)[0]
                        break
                if keyword_match:
                    role_score += 8.0
                    reasons.append(f"Role keyword '{keyword_match.title()}' aligns with your preferred roles")

        # -------------------------------------------------------------------
        # Dimension 3: Location & Remote Eligibility (Max 20.0 pts)
        # -------------------------------------------------------------------
        location_score = 0.0
        location_eligibility = "Unknown"
        job_remote = (job.remote_type or "ONSITE").upper().strip()
        job_eligibility = (getattr(job, "remote_eligibility", None) or "UNKNOWN").upper().strip()
        job_loc_str = f"{job.city or ''} {job.region or ''} {job.country or ''} {job.location or ''}".lower()

        # Remote / Arrangement (Max 10 pts)
        if candidate_arrangements:
            if job_remote == "REMOTE":
                if "REMOTE" in candidate_arrangements:
                    if job_eligibility == "WORLDWIDE_REMOTE":
                        location_score += 10.0
                        location_eligibility = "Eligible (Worldwide Remote)"
                        reasons.append("Worldwide remote — 100% location flexibility")
                    elif job_eligibility == "INDIA_ONLY":
                        cand_loc_str = " ".join(candidate_locations).lower()
                        if "india" in cand_loc_str or any(c in cand_loc_str for c in ["bengaluru", "bangalore", "mumbai", "delhi", "hyderabad", "pune", "chennai", "gurgaon", "noida", "kolkata"]):
                            location_score += 10.0
                            location_eligibility = "Eligible (India-Only Remote)"
                            reasons.append("India-eligible remote position")
                        else:
                            location_score += 0.0
                            location_eligibility = "Restricted (India-Only)"
                            reasons.append("Remote eligibility restricted to India residents")
                    elif job_eligibility in ["US_ONLY", "USA_ONLY"] or (job.country and "united states" in job.country.lower() and candidate_locations and any("india" in l.lower() for l in candidate_locations) and not any("united states" in l.lower() for l in candidate_locations)):
                        location_score += 0.0
                        location_eligibility = f"Restricted ({job.country or job_eligibility})"
                        reasons.append(f"Remote position restricted to {job.country or job_eligibility}")
                    else:
                        location_score += 10.0
                        location_eligibility = "Eligible (Remote)"
                        reasons.append("Matches your Remote work arrangement preference")
                else:
                    location_score += 0.0
                    location_eligibility = "Mismatched Arrangement"
                    reasons.append("Remote job does not match your on-site/hybrid preference")
            elif job_remote in candidate_arrangements:
                location_score += 10.0
                location_eligibility = f"Eligible ({job_remote.title()})"
                reasons.append(f"Work arrangement ({job_remote.title()}) matches your preference")
            else:
                location_score += 0.0
                location_eligibility = "Mismatched Arrangement"
                reasons.append(f"Work arrangement ({job_remote.title()}) differs from your preference")
        else:
            location_eligibility = "Not Specified"

        # Geographic Location (Max 10 pts)
        if candidate_locations:
            if job_eligibility == "WORLDWIDE_REMOTE":
                location_score += 10.0
            else:
                cand_locs_lower = [l.lower() for l in candidate_locations]
                matched_loc = next((l for l in cand_locs_lower if l in job_loc_str), None)
                if matched_loc:
                    location_score += 10.0
                    reasons.append(f"Located in preferred location '{matched_loc.title()}'")
                else:
                    if job.city or job.country:
                        reasons.append(f"Location ({job.city or job.country}) differs from your preferred locations")

        # -------------------------------------------------------------------
        # Dimension 4: Relevant Experience & Seniority (Max 15.0 pts)
        # -------------------------------------------------------------------
        exp_score = 0.0
        experience_alignment = "Not Specified"

        # Check track and skill relevance: experience in an unrelated field with 0 matching skills does not count
        is_unrelated_field = False
        if active_prof and job.profession:
            cand_prof_key = resolve_profession_key(active_prof)
            job_prof_key = resolve_profession_key(job.profession)
            if cand_prof_key != job_prof_key and skill_score == 0.0:
                is_unrelated_field = True

        if is_unrelated_field:
            exp_score = 0.0
            experience_alignment = "Unrelated Field"
            reasons.append("Experience in a different career track does not satisfy requirements for this role")
        elif user_exp is not None and job.min_experience_years is not None:
            if user_exp >= job.min_experience_years:
                exp_score = 15.0
                experience_alignment = "Meets Requirement"
                reasons.append(f"Experience ({user_exp:g} yrs) satisfies requirement ({job.min_experience_years:g} yrs)")
            elif user_exp >= job.min_experience_years * 0.7:
                exp_score = 8.0
                experience_alignment = "Within Reach"
                reasons.append(f"Close experience alignment ({user_exp:g} yrs vs {job.min_experience_years:g} yrs required)")
            else:
                exp_score = 0.0
                experience_alignment = "Below Requirement"
                reasons.append(f"Experience ({user_exp:g} yrs) is below requirement ({job.min_experience_years:g} yrs)")
        elif user_exp is not None and job.experience_level:
            exp_level = (job.experience_level or "").upper()
            aligned = False
            if exp_level in ["ENTRY", "INTERN", "JUNIOR"] and user_exp <= 2.5:
                aligned = True
            elif exp_level in ["MID", "INTERMEDIATE"] and 1.5 <= user_exp <= 5.5:
                aligned = True
            elif exp_level in ["SENIOR"] and user_exp >= 3.5:
                aligned = True
            elif exp_level in ["LEAD", "STAFF", "PRINCIPAL"] and user_exp >= 5.5:
                aligned = True
            elif exp_level in ["DIRECTOR", "EXECUTIVE", "VP"] and user_exp >= 8.0:
                aligned = True

            if aligned:
                exp_score = 15.0
                experience_alignment = f"Aligns with {exp_level.title()}"
                reasons.append(f"Experience level ({user_exp:g} yrs) aligns with {exp_level.title()} role")
            else:
                exp_score = 5.0
                experience_alignment = f"Different Seniority ({exp_level.title()})"
        elif user_exp is not None:
            exp_score = 0.0
            experience_alignment = "Not Specified in Job"
        else:
            exp_score = 0.0
            experience_alignment = "Candidate Experience Unknown"

        total = round(min(100.0, max(0.0, skill_score + role_score + location_score + exp_score)), 1)

        return MatchBreakdown(
            skill_score=round(skill_score, 1),
            role_score=round(role_score, 1),
            location_score=round(location_score, 1),
            experience_score=round(exp_score, 1),
            total_score=total,
            matched_skills=matched_skills[:8],
            missing_skills=missing_skills[:5],
            reasons=reasons,
            has_sufficient_data=True,
            insufficient_data_reasons=[],
            location_eligibility=location_eligibility,
            experience_alignment=experience_alignment,
            score_disclaimer="Match score reflects qualification fit and profile alignment; it does not indicate hiring probability."
        )

    @classmethod
    def get_recommendations_for_user(
        cls,
        db: Session,
        user: User,
        profession: Optional[str] = None,
        min_score: Optional[int] = None,
        remote_type: Optional[str] = None,
        location: Optional[str] = None,
        limit: int = 20,
        offset: int = 0
    ) -> RecommendationResponse:
        profile = db.query(Profile).filter(Profile.user_id == user.id).first()
        if not profile:
            return RecommendationResponse(
                algorithm_version=cls.VERSION,
                items=[],
                total=0,
                has_sufficient_data=False,
                insufficient_data_reasons=["Candidate profile not found. Please log in and set up your candidate profile."],
                disclaimer="Match scores reflect qualification fit and profile alignment; they do not represent hiring probability."
            )

        # Check for sufficient data
        has_meaningful_info = bool(
            profile.skills or profile.preferred_roles or profile.profession or (profile.total_experience_years is not None) or profile.work_arrangements or profile.preferred_locations
        )
        if not has_meaningful_info:
            return RecommendationResponse(
                algorithm_version=cls.VERSION,
                items=[],
                total=0,
                has_sufficient_data=False,
                insufficient_data_reasons=[
                    "Your profile does not yet contain skills, career tracks, or preferences. Complete your profile or upload a resume to calculate personalized matches."
                ],
                disclaimer="Match scores reflect qualification fit and profile alignment; they do not represent hiring probability."
            )

        # Scoped preference lookup from career_interests if specified
        target_prof = resolve_profession_key(profession) if profession else resolve_profession_key(profile.profession)
        scoped_skills = None
        scoped_roles = None
        scoped_exp = None

        if target_prof and profile.career_interests:
            for ci in profile.career_interests:
                if isinstance(ci, dict) and resolve_profession_key(ci.get("profession")) == target_prof:
                    scoped_skills = ci.get("skills")
                    scoped_roles = ci.get("preferred_roles")
                    scoped_exp = ci.get("experience_years")
                    break

        # Saved jobs lookup for current user
        user_saved = db.query(SavedJob.job_id).filter(SavedJob.user_id == user.id).all()
        saved_job_ids = {s[0] for s in user_saved}

        # Base query for active jobs
        job_query = db.query(Job).join(Job.company).join(Job.source).filter(
            Job.status.in_(["ACTIVE", "POSSIBLY_STALE"])
        )

        # Apply database filters if provided
        if target_prof:
            match_keys = [target_prof]
            if target_prof in TAXONOMY_FAMILIES:
                match_keys.extend(TAXONOMY_FAMILIES[target_prof].get("legacy_aliases", []))
            job_query = job_query.filter(Job.profession.in_(match_keys))

        if remote_type:
            job_query = job_query.filter(Job.remote_type == remote_type.upper().strip())

        if location:
            loc_clean = location.strip().lower()
            job_query = job_query.filter(
                (Job.city.ilike(f"%{loc_clean}%")) |
                (Job.country.ilike(f"%{loc_clean}%")) |
                (Job.location.ilike(f"%{loc_clean}%"))
            )

        # Pull candidate jobs pool for scoring
        candidate_pool = job_query.order_by(
            Job.posting_date.desc().nullslast(), Job.id.desc()
        ).limit(250).all()

        scored_items = []
        for job in candidate_pool:
            breakdown = cls.calculate_match(
                profile,
                job,
                scoped_skills=scoped_skills,
                scoped_roles=scoped_roles,
                scoped_exp=scoped_exp,
                target_profession=target_prof
            )

            # Filter out completely unrelated 0% matches or uninformative entries
            if breakdown.total_score <= 0.0 and not breakdown.matched_skills:
                continue

            if min_score is not None and breakdown.total_score < min_score:
                continue

            job_item = JobListResponseItem(
                id=job.id,
                title=job.title,
                normalized_title=job.normalized_title or job.title,
                department=job.department,
                profession=job.profession,
                classification_confidence=job.classification_confidence or 1.0,
                system_summary=job.system_summary,
                location=job.location,
                city=job.city,
                region=job.region,
                country=job.country,
                remote_type=job.remote_type,
                employment_type=job.employment_type,
                experience_level=job.experience_level,
                min_experience_years=job.min_experience_years,
                skills=job.skills or [],
                salary_min=job.salary_min,
                salary_max=job.salary_max,
                salary_currency=job.salary_currency,
                salary_period=job.salary_period,
                posting_date=job.posting_date,
                status=job.status,
                application_url=job.application_url,
                company_id=job.company_id,
                company_name=job.company.canonical_name,
                company_logo=job.company.logo_url,
                source_name=job.source.source_name,
                first_seen_at=job.first_seen_at,
                last_verified_at=job.last_verified_at,
                is_saved=(job.id in saved_job_ids),
                is_demo=bool((job.raw_source_data and isinstance(job.raw_source_data, dict) and job.raw_source_data.get("seed") is True) or job.id <= 7),
                match_score=breakdown.total_score,
                match_reasons=breakdown.reasons,
                match_breakdown=breakdown.model_dump()
            )

            scored_items.append(
                RecommendationItem(
                    job=job_item,
                    match_score=int(round(breakdown.total_score)),
                    match_breakdown=breakdown
                )
            )

        # Sort descending by match score, then id desc
        scored_items.sort(key=lambda x: (x.match_score, x.job.id), reverse=True)

        total_count = len(scored_items)
        paged_items = scored_items[offset: offset + limit]

        return RecommendationResponse(
            algorithm_version=cls.VERSION,
            items=paged_items,
            total=total_count,
            has_sufficient_data=True,
            insufficient_data_reasons=[],
            disclaimer="Match scores reflect qualification fit and profile alignment; they do not represent hiring probability."
        )
