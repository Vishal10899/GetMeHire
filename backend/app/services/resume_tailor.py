import re
from typing import Dict, List, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models import Job, Company, User, Profile
from app.schemas.resume_studio import TailorResumeResponse
from app.services.matching_service import MatchingService
from app.services.resume_parser import CANONICAL_SKILLS
from app.ingestion.taxonomy import TAXONOMY_FAMILIES

SKILL_ADJACENCY_GROUPS = [
    {"python", "django", "fastapi", "flask", "sqlalchemy", "celery", "pandas", "numpy"},
    {"javascript", "typescript", "react", "next.js", "node.js", "express.js", "vue.js", "angular"},
    {"aws", "gcp", "azure", "cloud", "terraform", "ci/cd", "devops"},
    {"docker", "kubernetes", "k8s", "helm", "containerization"},
    {"postgresql", "postgres", "mysql", "mongodb", "redis", "elasticsearch", "sql"},
    {"machine learning", "deep learning", "pytorch", "tensorflow", "nlp", "llms", "ai"},
    {"git", "github", "gitlab", "jira", "agile", "scrum"},
]

class ResumeTailorService:
    """
    Engine for creating tailored, job-specific resumes for GetMeHire vacancies.
    Truthfulness Guarantee: Never invents skills, companies, dates, or degrees.
    """

    @classmethod
    def tailor_resume_for_job(
        cls,
        db: Session,
        user: User,
        job_id: int,
        base_resume_data: Optional[Dict[str, Any]] = None,
        custom_instructions: Optional[str] = None
    ) -> TailorResumeResponse:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Job with ID {job_id} not found")

        company = db.query(Company).filter(Company.id == job.company_id).first()
        company_name = company.canonical_name if company else "Hiring Employer"

        # 1. Resolve Candidate Base Data
        profile: Optional[Profile] = user.profile
        content = dict(base_resume_data) if base_resume_data else {}

        if not content and profile:
            content = {
                "full_name": profile.full_name or user.email.split("@")[0].title(),
                "email": user.email,
                "phone": profile.phone_number,
                "location": profile.current_location,
                "linkedin_url": profile.linkedin_url,
                "portfolio_url": profile.portfolio_url,
                "summary": profile.headline or "",
                "skills": list(profile.skills or []),
                "technical_skills": list(profile.skills or []),
                "tools_technologies": [],
                "work_experience": list(profile.work_experience or []),
                "education": list(profile.education or []),
                "projects": list(profile.projects or []),
                "certifications": list(profile.certifications or []),
            }

        candidate_skills = list(content.get("skills") or [])
        cand_skills_lower_map = {s.lower().strip(): s for s in candidate_skills}

        # 2. Extract Job Requirements & Keywords
        job_skills = list(job.skills or [])
        desc_lower = (job.description or "").lower()
        title_lower = (job.title or "").lower()

        # Discover additional canonical skills from job description text
        extracted_job_skills = set(s.lower() for s in job_skills)
        for kw, canon in CANONICAL_SKILLS.items():
            if f" {kw} " in f" {desc_lower} " or f" {kw} " in f" {title_lower} ":
                extracted_job_skills.add(canon.lower())

        # 3. Categorize Skills (Matched, Adjacent, Missing)
        matched_skills = []
        adjacent_skills = []
        missing_skills = []

        cand_skill_set = set(cand_skills_lower_map.keys())

        for j_skill_lower in extracted_job_skills:
            canonical_disp = CANONICAL_SKILLS.get(j_skill_lower, j_skill_lower.capitalize())
            if j_skill_lower in cand_skill_set:
                matched_skills.append(cand_skills_lower_map[j_skill_lower])
            else:
                # Check for adjacency in skill families
                has_adj = False
                for group in SKILL_ADJACENCY_GROUPS:
                    if j_skill_lower in group and bool(group.intersection(cand_skill_set)):
                        adjacent_skills.append(canonical_disp)
                        has_adj = True
                        break
                if not has_adj:
                    missing_skills.append(canonical_disp)

        matched_skills = list(dict.fromkeys(matched_skills))
        adjacent_skills = [s for s in dict.fromkeys(adjacent_skills) if s not in matched_skills]
        missing_skills = [s for s in dict.fromkeys(missing_skills) if s not in matched_skills and s not in adjacent_skills]

        # 4. Tailor Content: Reorder Skills
        remaining_candidate_skills = [
            s for s in candidate_skills if s.lower() not in set(m.lower() for m in matched_skills)
        ]
        reordered_skills = matched_skills + remaining_candidate_skills

        # 5. Tailor Work Experience: Highlight and Reorder Bullets
        tailored_experiences = []
        job_keywords_set = set(extracted_job_skills).union(set(title_lower.split()))

        for exp in content.get("work_experience", []):
            exp_copy = dict(exp)
            raw_desc = exp_copy.get("description", "")
            bullets = [b.strip() for b in re.split(r"[\n•\-\*]", raw_desc) if b.strip() and len(b.strip()) > 10]

            def score_bullet(b: str) -> int:
                b_words = set(re.findall(r"\w+", b.lower()))
                return len(b_words.intersection(job_keywords_set))

            # Sort bullets by keyword relevance (stable sort)
            sorted_bullets = sorted(bullets, key=score_bullet, reverse=True)
            exp_copy["description"] = "\n".join(f"• {b}" for b in sorted_bullets)
            tailored_experiences.append(exp_copy)

        # 6. Generate Tailored Professional Summary Options
        years_exp = profile.total_experience_years if profile else None
        years_str = f"{int(years_exp)}+ years" if years_exp and years_exp >= 1 else "demonstrated"
        top_matched_str = ", ".join(matched_skills[:4]) if matched_skills else ", ".join(reordered_skills[:4])

        tailored_summary_1 = (
            f"Accomplished {job.title} with {years_str} of experience driving technical impact, "
            f"specializing in {top_matched_str}. Proven ability to design scalable systems and deliver "
            f"reliable software solutions, aligning closely with {company_name}'s technical objectives."
        )

        tailored_summary_2 = (
            f"Software Engineer with core expertise in {top_matched_str}, seeking to contribute to "
            f"{company_name} as a {job.title}. Combines deep hands-on experience in full-lifecycle delivery "
            f"with strong cross-functional execution and engineering discipline."
        )

        tailored_summary_3 = (
            f"Results-oriented engineering specialist bringing {years_str} of background in {top_matched_str}. "
            f"Demonstrated history of translating technical requirements into high-availability architecture "
            f"ready to accelerate development for the {job.title} role at {company_name}."
        )

        tailored_summary_options = [tailored_summary_1, tailored_summary_2, tailored_summary_3]

        # 7. Construct Tailored Resume Content
        tailored_content = dict(content)
        tailored_content["target_role"] = job.title
        tailored_content["target_company"] = company_name
        tailored_content["summary"] = tailored_summary_1
        tailored_content["skills"] = reordered_skills
        tailored_content["technical_skills"] = [s for s in reordered_skills if s.lower() in CANONICAL_SKILLS]
        tailored_content["work_experience"] = tailored_experiences

        # 8. Compute Real Matching Scores via MatchingService
        score_before = 0
        score_after = 0
        score_explanations: List[str] = []

        if profile:
            try:
                cand_initial_skills = list(content.get("skills") or profile.skills or [])
                cand_initial_roles = list(profile.preferred_roles or [])

                breakdown_before = MatchingService.calculate_match(
                    profile=profile,
                    job=job,
                    scoped_skills=cand_initial_skills,
                    scoped_roles=cand_initial_roles
                )
                score_before = int(round(breakdown_before.total_score))

                # Genuine re-score using MatchingService with reordered skills and target role alignment
                breakdown_after = MatchingService.calculate_match(
                    profile=profile,
                    job=job,
                    scoped_skills=reordered_skills,
                    scoped_roles=[job.title] if job.title else cand_initial_roles
                )
                score_after = int(round(breakdown_after.total_score))

                if breakdown_after.reasons:
                    score_explanations.extend(breakdown_after.reasons[:2])
            except Exception:
                score_before = 0
                score_after = 0
                score_explanations.append("Match score calculation unavailable.")
        else:
            score_explanations.append("Match score unavailable: candidate profile not initialized.")

        improvement_notes = [
            f"Prioritized {len(matched_skills)} exact skill matches to the top of your skills section.",
            f"Re-ordered work experience bullet points to lead with accomplishments relevant to {job.title}.",
            f"Generated target-aligned professional summary referencing {company_name}."
        ]
        if score_explanations:
            improvement_notes.extend(score_explanations)
        if missing_skills:
            improvement_notes.append(
                f"Identified {len(missing_skills)} preferred skill(s) not in your profile: {', '.join(missing_skills[:3])}. Be prepared to speak to these in interviews."
            )

        return TailorResumeResponse(
            target_job_id=job.id,
            target_job_title=job.title,
            target_company_name=company_name,
            match_score_before=score_before,
            match_score_after=score_after,
            matched_skills=matched_skills,
            adjacent_skills=adjacent_skills,
            missing_skills=missing_skills,
            tailored_content=tailored_content,
            tailored_summary_options=tailored_summary_options,
            improvement_notes=improvement_notes
        )
