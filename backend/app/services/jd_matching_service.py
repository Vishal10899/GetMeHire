"""
Advanced Bidirectional Job Description & ATS Deep Matching Service.

Performs deep semantic comparison between Job Descriptions (from GetMeHire database
or pasted by user) and candidate resumes.
Evaluates:
- Skills compatibility (required hard skills vs preferred/bonus skills vs adjacent skills)
- Experience compatibility (candidate actual years vs JD minimum required years)
- Education alignment (degree level vs JD minimum degree requirement)
- Keyword density & domain phrasing
- ATS parsing friction & formatting risks
- Concrete, actionable, prioritized suggestions for ATS optimization.
"""

import re
import datetime
from typing import Dict, List, Any, Optional, Tuple, Set
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models import Job, Company, User, Profile, ResumeVersion
from app.schemas.resume_studio import (
    JDMatchRequest,
    JDMatchResponse,
    MatchedSkillDetail,
    MissingSkillDetail,
    ExperienceAnalysis,
    EducationAnalysis,
    ATSFrictionPoint,
)
from app.services.resume_parser import CANONICAL_SKILLS, TECH_SKILLS_SET, TOOLS_TECH_SET, DEGREE_PATTERNS
from app.services.resume_tailor import SKILL_ADJACENCY_GROUPS
from app.services.resume_template_intelligence import (
    ROLE_TEMPLATE_REGISTRY,
    detect_optimal_template_for_role,
)

# Common action verbs that signal strong accomplishment bullets
STRONG_ACTION_VERBS = {
    "architected", "engineered", "developed", "built", "spearheaded", "accelerated",
    "automated", "designed", "optimized", "implemented", "scaled", "reduced",
    "increased", "mentored", "orchestrated", "delivered", "deployed", "transformed",
    "streamlined", "formulated", "executed", "launched", "integrated", "negotiated",
    "established", "directed", "managed", "led", "generated", "achieved", "championed"
}

# Weak phrasing patterns that ATS and recruiters downgrade
WEAK_BULLET_STARTS = [
    (r"^responsible\s+for", "Replace passive 'Responsible for' with active impact verbs like 'Led', 'Architected', or 'Executed'."),
    (r"^assisted\s+(?:with|in)", "Quantify your specific contribution rather than saying 'Assisted with'."),
    (r"^helped\s+(?:with|to)", "Replace 'Helped to' with direct action verbs showing your ownership."),
    (r"^worked\s+(?:on|with)", "Specify your exact role and deliverable rather than 'Worked on'."),
    (r"^participated\s+in", "State what you personally delivered instead of 'Participated in'."),
    (r"^duties\s+included", "Focus on achievements and metrics rather than a list of job duties."),
]

# Section headers for requirement vs preferred segregation in JDs
REQUIREMENTS_HEADERS = [
    r"(?:minimum\s+|basic\s+|required\s+)?qualifications",
    r"requirements",
    r"what\s+you(?:'ll)?\s+need",
    r"must\s+have",
    r"what\s+you\s+bring",
    r"who\s+you\s+are",
    r"what\s+we(?:'re)?\s+looking\s+for",
]

PREFERRED_HEADERS = [
    r"preferred\s+qualifications",
    r"nice\s+to\s+have",
    r"bonus\s+(?:points|qualifications|skills)",
    r"what\s+sets\s+you\s+apart",
    r"desired\s+(?:skills|qualifications)",
    r"plus",
]


class JDMatchingService:
    """Authoritative bidirectional JD vs Resume matching engine."""

    @classmethod
    def match(
        cls,
        db: Session,
        user: User,
        request: JDMatchRequest,
    ) -> JDMatchResponse:
        # 1. Resolve Target Job & Description
        job_title = (request.job_title or "").strip()
        job_description = (request.job_description_text or "").strip()
        company_name = (request.company_name or "").strip()
        job_skills: List[str] = []

        if request.job_id is not None:
            job = db.query(Job).filter(Job.id == request.job_id).first()
            if not job:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Job listing with ID {request.job_id} not found"
                )
            job_title = job.title or job_title
            job_description = job.description or job_description
            job_skills = list(job.skills or [])
            if job.company_id:
                comp = db.query(Company).filter(Company.id == job.company_id).first()
                if comp and comp.canonical_name:
                    company_name = comp.canonical_name

        if not job_title:
            job_title = "Target Professional Role"
        if not company_name:
            company_name = "Target Employer"

        # 2. Resolve Candidate Resume Content
        resume_content: Dict[str, Any] = {}
        if request.version_id is not None:
            v = (
                db.query(ResumeVersion)
                .filter(ResumeVersion.id == request.version_id, ResumeVersion.user_id == user.id)
                .first()
            )
            if v and v.content:
                resume_content = dict(v.content)

        if not resume_content and request.resume_content:
            resume_content = dict(request.resume_content)

        if not resume_content:
            profile: Optional[Profile] = user.profile
            if profile:
                resume_content = {
                    "full_name": profile.full_name or user.email.split("@")[0].replace(".", " ").title(),
                    "headline": profile.headline or "",
                    "email": user.email,
                    "phone": profile.phone_number or "",
                    "location": profile.current_location or "",
                    "linkedin_url": profile.linkedin_url or "",
                    "portfolio_url": profile.portfolio_url or "",
                    "summary": profile.headline or "",
                    "skills": list(profile.skills or []),
                    "technical_skills": list(profile.skills or []),
                    "tools_technologies": [],
                    "work_experience": list(profile.work_experience or []),
                    "education": list(profile.education or []),
                    "projects": list(profile.projects or []),
                    "certifications": list(profile.certifications or []),
                }
            else:
                resume_content = {
                    "full_name": user.email.split("@")[0].replace(".", " ").title(),
                    "email": user.email,
                    "skills": [],
                    "work_experience": [],
                    "education": [],
                }

        # 3. Extract Job Description Specifications
        parsed_jd = cls._parse_job_description(job_title, job_description, explicit_skills=job_skills)

        # 4. Extract Candidate Specifications
        parsed_candidate = cls._parse_candidate_resume(resume_content)

        # 5. Compute Skills Match & Gaps
        skills_match_data = cls._evaluate_skills(
            jd_required_skills=parsed_jd["required_skills"],
            jd_preferred_skills=parsed_jd["preferred_skills"],
            candidate_skills=parsed_candidate["all_skills"],
            candidate_text_evidence=parsed_candidate["text_corpus"],
        )

        # 6. Compute Experience Alignment
        exp_analysis = cls._evaluate_experience(
            jd_req_years=parsed_jd["required_years"],
            cand_years=parsed_candidate["total_experience_years"],
        )

        # 7. Compute Education Alignment
        edu_analysis = cls._evaluate_education(
            jd_req_degree=parsed_jd["required_degree"],
            cand_highest_degree=parsed_candidate["highest_degree"],
        )

        # 8. Compute ATS Friction Points & Formatting
        ats_friction = cls._evaluate_ats_friction(
            resume_content=resume_content,
            parsed_candidate=parsed_candidate,
            parsed_jd=parsed_jd,
            missing_skills=skills_match_data["missing_skills"],
        )

        # 9. Compute Keyword & Domain Phrase Density
        keyword_density_score = cls._calculate_keyword_density(
            parsed_jd=parsed_jd,
            candidate_text_corpus=parsed_candidate["text_corpus"],
        )

        # 10. Scoring Aggregation
        skills_score = skills_match_data["score"]
        experience_score = exp_analysis["score"]
        education_score = edu_analysis["score"]
        formatting_score = max(0, 100 - (len([f for f in ats_friction if f.severity == "CRITICAL"]) * 20 + len([f for f in ats_friction if f.severity == "WARNING"]) * 10))

        # Overall composite match score:
        # 40% Skills + 25% Experience + 15% Education + 10% Keyword Density + 10% ATS Formatting
        overall_score = int(
            round(
                0.40 * skills_score +
                0.25 * experience_score +
                0.15 * education_score +
                0.10 * keyword_density_score +
                0.10 * formatting_score
            )
        )
        overall_score = max(5, min(99, overall_score))

        # 11. Prioritized Action Items
        action_items = cls._generate_prioritized_action_items(
            missing_skills=skills_match_data["missing_skills"],
            exp_analysis=exp_analysis,
            edu_analysis=edu_analysis,
            ats_friction=ats_friction,
            keyword_score=keyword_density_score,
        )

        # 12. Recommend Optimal Template from 16+ Architecture Registry
        rec_template_meta = detect_optimal_template_for_role(job_title)

        return JDMatchResponse(
            target_job_title=job_title,
            target_company_name=company_name,
            overall_match_score=overall_score,
            score_breakdown={
                "skills": skills_score,
                "experience": experience_score,
                "education": education_score,
                "keyword_density": keyword_density_score,
                "formatting": formatting_score,
            },
            matched_skills=skills_match_data["matched_skills"],
            missing_skills=skills_match_data["missing_skills"],
            adjacent_skills=skills_match_data["adjacent_skills"],
            experience_analysis=ExperienceAnalysis(
                jd_required_years=parsed_jd["required_years"],
                candidate_years=parsed_candidate["total_experience_years"],
                status=exp_analysis["status"],
                explanation=exp_analysis["explanation"],
            ),
            education_analysis=EducationAnalysis(
                jd_required_degree=parsed_jd["required_degree"],
                candidate_highest_degree=parsed_candidate["highest_degree"],
                status=edu_analysis["status"],
                explanation=edu_analysis["explanation"],
            ),
            ats_friction_points=ats_friction,
            prioritized_action_items=action_items,
            recommended_template={
                "id": rec_template_meta["id"],
                "name": rec_template_meta["name"],
                "profession": rec_template_meta["profession"],
                "description": rec_template_meta["description"],
                "recommended_sections_order": rec_template_meta["recommended_sections_order"],
                "color_palette": rec_template_meta["color_palette"],
            },
            disclaimer="Match analysis provides qualification alignment heuristics and ATS formatting recommendations; it does not guarantee interview shortlisting or employment offers."
        )

    # --------------------------------------------------------------------------
    # Internal Parsing & Extraction Logic
    # --------------------------------------------------------------------------

    @classmethod
    def _parse_job_description(
        cls,
        title: str,
        desc: str,
        explicit_skills: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Deeply parses JD text to extract required skills, preferred skills, experience, and degree."""
        title_clean = title.lower()
        desc_clean = desc.lower()

        required_skills: Set[str] = set()
        preferred_skills: Set[str] = set()

        if explicit_skills:
            for s in explicit_skills:
                canon = CANONICAL_SKILLS.get(s.lower(), s.strip())
                required_skills.add(canon)

        # 1. Segment Description into Requirements vs Preferred sections if present
        req_text = desc_clean
        pref_text = ""

        pref_matches = list(re.finditer(r"(?:" + "|".join(PREFERRED_HEADERS) + r")", desc_clean))
        if pref_matches:
            first_pref_idx = pref_matches[0].start()
            req_text = desc_clean[:first_pref_idx]
            pref_text = desc_clean[first_pref_idx:]

        # 2. Extract Canonical Skills from texts
        for kw, canon in CANONICAL_SKILLS.items():
            pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
            if re.search(pattern, title_clean) or re.search(pattern, req_text):
                required_skills.add(canon)
            elif pref_text and re.search(pattern, pref_text):
                if canon not in required_skills:
                    preferred_skills.add(canon)

        # Fallback: if no required skills found in text, search the whole description
        if not required_skills and not preferred_skills:
            for kw, canon in CANONICAL_SKILLS.items():
                if re.search(r"(?<!\w)" + re.escape(kw) + r"(?!\w)", desc_clean):
                    required_skills.add(canon)

        # 3. Extract Experience Requirement (e.g. '5+ years of experience', '3-5 years', 'minimum 7 years')
        required_years: Optional[float] = None
        exp_patterns = [
            r"(\d+)\+?\s*(?:to\s*(\d+))?\s*(?:years?|yrs?)(?:\s+of)?(?:\s+(?:relevant|hands-on|professional|work)?\s+experience)?",
            r"(?:minimum|at\s+least)\s+(\d+)\+?\s*(?:years?|yrs?)",
        ]
        candidates_years = []
        for p in exp_patterns:
            matches = re.finditer(p, req_text if req_text else desc_clean)
            for m in matches:
                try:
                    val = float(m.group(1))
                    if 0 < val <= 25:
                        candidates_years.append(val)
                except (ValueError, IndexError):
                    pass

        if candidates_years:
            # Take the lowest required threshold if a range like 3-5 was specified
            required_years = min(candidates_years)

        # 4. Extract Degree Requirement
        required_degree: Optional[str] = None
        if re.search(r"\b(?:ph\.?d\.?|doctorate|doctoral)\b", desc_clean):
            required_degree = "Doctorate / Ph.D."
        elif re.search(r"\b(?:master'?s?|m\.?s\.?|m\.?tech\.?|m\.?e\.?|m\.?b\.?a\.?)\b", desc_clean):
            required_degree = "Master's Degree"
        elif re.search(r"\b(?:bachelor'?s?|b\.?s\.?|b\.?tech\.?|b\.?e\.?|b\.?a\.?|undergraduate)\b", desc_clean):
            required_degree = "Bachelor's Degree"
        elif re.search(r"\b(?:associate|diploma)\b", desc_clean):
            required_degree = "Associate Degree / Diploma"

        return {
            "required_skills": sorted(list(required_skills)),
            "preferred_skills": sorted(list(preferred_skills)),
            "required_years": required_years,
            "required_degree": required_degree,
        }

    @classmethod
    def _parse_candidate_resume(cls, content: Dict[str, Any]) -> Dict[str, Any]:
        """Extracts candidate skills, calculated experience years, highest degree, and full text corpus."""
        # 1. Candidate Skills
        all_skills: Set[str] = set()
        for k in ["skills", "technical_skills", "tools_technologies"]:
            val = content.get(k) or []
            if isinstance(val, list):
                for item in val:
                    if isinstance(item, str) and item.strip():
                        all_skills.add(item.strip())

        # 2. Text Corpus for Evidence & Keyword Scanning
        corpus_parts: List[str] = []
        if content.get("headline"):
            corpus_parts.append(str(content["headline"]))
        if content.get("summary"):
            corpus_parts.append(str(content["summary"]))

        work_exp = content.get("work_experience") or []
        for exp in work_exp:
            if isinstance(exp, dict):
                corpus_parts.append(exp.get("title") or "")
                corpus_parts.append(exp.get("company") or "")
                corpus_parts.append(exp.get("description") or "")
                bullets = exp.get("bullets") or []
                for b in bullets:
                    corpus_parts.append(str(b))

        projects = content.get("projects") or []
        for proj in projects:
            if isinstance(proj, dict):
                corpus_parts.append(proj.get("name") or proj.get("title") or "")
                corpus_parts.append(proj.get("description") or "")
                for b in proj.get("bullets") or []:
                    corpus_parts.append(str(b))

        full_corpus = " ".join(corpus_parts)
        full_corpus_lower = full_corpus.lower()

        # Also add any canonical skills mentioned in the resume text
        for kw, canon in CANONICAL_SKILLS.items():
            pattern = r"(?<!\w)" + re.escape(kw) + r"(?!\w)"
            if re.search(pattern, full_corpus_lower):
                all_skills.add(canon)

        # 3. Calculate Total Experience Years from Work Experience Dates
        total_exp_years = cls._calculate_total_experience_years(work_exp)

        # 4. Extract Highest Education Degree
        highest_degree = cls._extract_candidate_degree(content.get("education") or [])

        return {
            "all_skills": sorted(list(all_skills)),
            "total_experience_years": total_exp_years,
            "highest_degree": highest_degree,
            "text_corpus": full_corpus,
            "work_experience": work_exp,
        }

    @classmethod
    def _calculate_total_experience_years(cls, work_experience: List[Dict[str, Any]]) -> float:
        """Parses start and end dates from work history and sums duration with overlap coalescing."""
        if not work_experience:
            return 0.0

        current_year = datetime.datetime.now().year
        intervals: List[Tuple[float, float]] = []

        year_pattern = re.compile(r"\b(19\d{2}|20\d{2})\b")

        for item in work_experience:
            if not isinstance(item, dict):
                continue
            start_str = str(item.get("start_date") or "")
            end_str = str(item.get("end_date") or "")

            start_matches = year_pattern.findall(start_str)
            end_matches = year_pattern.findall(end_str)

            start_val: Optional[float] = None
            end_val: Optional[float] = None

            if start_matches:
                start_val = float(start_matches[0])
            if end_matches:
                end_val = float(end_matches[0])
            elif "present" in end_str.lower() or "current" in end_str.lower() or not end_str:
                end_val = float(current_year) + (datetime.datetime.now().month / 12.0)

            if start_val and end_val and end_val >= start_val:
                intervals.append((start_val, end_val))

        if not intervals:
            # Fallback heuristic: 1.5 years per job entry if dates are unparseable
            return round(min(15.0, len(work_experience) * 1.5), 1)

        # Merge overlapping intervals
        intervals.sort(key=lambda x: x[0])
        merged = []
        curr_start, curr_end = intervals[0]

        for s, e in intervals[1:]:
            if s <= curr_end:
                curr_end = max(curr_end, e)
            else:
                merged.append((curr_start, curr_end))
                curr_start, curr_end = s, e
        merged.append((curr_start, curr_end))

        total_years = sum(e - s for s, e in merged)
        return round(max(0.5, total_years), 1)

    @classmethod
    def _extract_candidate_degree(cls, education: List[Dict[str, Any]]) -> Optional[str]:
        """Identifies highest academic credential from candidate education entries."""
        if not education:
            return None

        degree_hierarchy = [
            ("Doctorate / Ph.D.", [r"\b(?:ph\.?d\.?|doctorate|doctoral)\b"]),
            ("Master's Degree", [r"\b(?:master|m\.?s\.?|m\.?tech\.?|m\.?e\.?|m\.?b\.?a\.?|postgraduate)\b"]),
            ("Bachelor's Degree", [r"\b(?:bachelor|b\.?s\.?|b\.?tech\.?|b\.?e\.?|b\.?a\.?|undergraduate)\b"]),
            ("Associate Degree / Diploma", [r"\b(?:associate|diploma)\b"]),
        ]

        text_to_check = []
        for edu in education:
            if isinstance(edu, dict):
                text_to_check.append(str(edu.get("degree") or ""))
                text_to_check.append(str(edu.get("field_of_study") or ""))
                text_to_check.append(str(edu.get("institution") or ""))

        combined = " ".join(text_to_check).lower()

        for deg_name, patterns in degree_hierarchy:
            for pat in patterns:
                if re.search(pat, combined):
                    return deg_name

        return "Completed Higher Education"

    # --------------------------------------------------------------------------
    # Evaluation Engines
    # --------------------------------------------------------------------------

    @classmethod
    def _evaluate_skills(
        cls,
        jd_required_skills: List[str],
        jd_preferred_skills: List[str],
        candidate_skills: List[str],
        candidate_text_evidence: str,
    ) -> Dict[str, Any]:
        """Computes skill matches, missing skills, adjacent skill bridges, and skill score."""
        cand_map_lower = {s.lower(): s for s in candidate_skills}
        cand_set = set(cand_map_lower.keys())

        matched_skills: List[MatchedSkillDetail] = []
        missing_skills: List[MissingSkillDetail] = []
        adjacent_skills: List[str] = []

        total_req_points = len(jd_required_skills) * 1.0
        total_pref_points = len(jd_preferred_skills) * 0.5
        earned_points = 0.0

        # Evaluate Required Skills
        for req_skill in jd_required_skills:
            req_lower = req_skill.lower()
            if req_lower in cand_set:
                earned_points += 1.0
                # Extract snippet from candidate text as evidence
                evidence = cls._find_evidence_snippet(req_skill, candidate_text_evidence)
                matched_skills.append(MatchedSkillDetail(
                    skill=req_skill,
                    in_resume=True,
                    is_required=True,
                    resume_evidence=evidence or f"Explicitly listed under candidate skills."
                ))
            else:
                # Check for adjacent skill in family
                adj_found = False
                for group in SKILL_ADJACENCY_GROUPS:
                    if req_lower in group and bool(group.intersection(cand_set)):
                        earned_points += 0.5  # Partial credit for related skill
                        adjacent_skills.append(f"{req_skill} (Candidate has related skill in same domain)")
                        adj_found = True
                        break

                missing_skills.append(MissingSkillDetail(
                    skill=req_skill,
                    importance="CRITICAL" if not adj_found else "HIGH",
                    is_required=True,
                    suggestion=(
                        f"Target JD explicitly requires '{req_skill}'. If you have experience with this technology or concept, "
                        f"add it directly to your technical skills section and reference it in an accomplishment bullet."
                        if not adj_found else
                        f"Target JD emphasizes '{req_skill}'. You possess related technologies; bridge the gap by emphasizing transferable workflows."
                    )
                ))

        # Evaluate Preferred Skills
        for pref_skill in jd_preferred_skills:
            pref_lower = pref_skill.lower()
            if pref_lower in cand_set:
                earned_points += 0.5
                evidence = cls._find_evidence_snippet(pref_skill, candidate_text_evidence)
                matched_skills.append(MatchedSkillDetail(
                    skill=pref_skill,
                    in_resume=True,
                    is_required=False,
                    resume_evidence=evidence or "Listed in candidate competencies."
                ))
            else:
                missing_skills.append(MissingSkillDetail(
                    skill=pref_skill,
                    importance="NICE_TO_HAVE",
                    is_required=False,
                    suggestion=f"Target JD lists '{pref_skill}' as a preferred qualification or bonus."
                ))

        total_possible = total_req_points + total_pref_points
        if total_possible > 0:
            score = int(round((earned_points / total_possible) * 100))
        else:
            score = 85  # Neutral default if no specific skills in JD

        return {
            "score": max(10, min(100, score)),
            "matched_skills": matched_skills,
            "missing_skills": missing_skills,
            "adjacent_skills": list(set(adjacent_skills)),
        }

    @classmethod
    def _find_evidence_snippet(cls, skill: str, text: str) -> Optional[str]:
        """Finds a 120-character contextual snippet in resume where skill is mentioned."""
        if not text:
            return None
        pattern = r"(?<!\w)" + re.escape(skill) + r"(?!\w)"
        match = re.search(pattern, text, re.IGNORECASE)
        if match:
            start = max(0, match.start() - 40)
            end = min(len(text), match.end() + 60)
            snippet = text[start:end].strip()
            return f"...{snippet}..."
        return None

    @classmethod
    def _evaluate_experience(
        cls,
        jd_req_years: Optional[float],
        cand_years: float,
    ) -> Dict[str, Any]:
        """Evaluates whether candidate meets, exceeds, or falls short of required experience years."""
        if jd_req_years is None:
            return {
                "score": 100,
                "status": "UNSPECIFIED",
                "explanation": f"Candidate possesses approximately {cand_years} years of documented professional experience. No strict minimum years required by job description."
            }

        if jd_req_years == 0.0:
            return {
                "score": 100,
                "status": "MATCHED",
                "explanation": f"Target job is suitable for freshers / early-career candidates (0 years required). Candidate meets baseline criteria."
            }

        if cand_years >= jd_req_years:
            diff = round(cand_years - jd_req_years, 1)
            status_text = "SURPASSED" if diff >= 2.0 else "MATCHED"
            return {
                "score": 100,
                "status": status_text,
                "explanation": f"Candidate has {cand_years} years of documented experience, satisfying the {jd_req_years}+ years requirement (+{diff} years)."
            }
        else:
            deficit = round(jd_req_years - cand_years, 1)
            if deficit <= 1.0:
                score = 85
                explanation = f"Candidate has {cand_years} years vs {jd_req_years} required. Minor gap ({deficit} yr) easily compensated by strong project achievements."
            elif deficit <= 2.5:
                score = 65
                explanation = f"Candidate has {cand_years} years vs {jd_req_years} required. Moderate gap ({deficit} yrs); highlight senior-level complexity and leadership."
            else:
                score = 40
                explanation = f"Candidate has {cand_years} years vs {jd_req_years} required ({deficit} yrs deficit). Focus on high-impact production deliverables."

            return {
                "score": score,
                "status": "BELOW_REQUIREMENT",
                "explanation": explanation
            }

    @classmethod
    def _evaluate_education(
        cls,
        jd_req_degree: Optional[str],
        cand_highest_degree: Optional[str],
    ) -> Dict[str, Any]:
        """Evaluates degree level compatibility."""
        if not jd_req_degree:
            return {
                "score": 100,
                "status": "UNSPECIFIED",
                "explanation": f"No strict formal degree prerequisite specified in the job posting."
            }

        degree_levels = {
            "Doctorate / Ph.D.": 4,
            "Master's Degree": 3,
            "Bachelor's Degree": 2,
            "Associate Degree / Diploma": 1,
            "Completed Higher Education": 1,
        }

        req_level = degree_levels.get(jd_req_degree, 2)
        cand_level = degree_levels.get(cand_highest_degree or "", 0)

        if cand_level >= req_level:
            return {
                "score": 100,
                "status": "MATCHED",
                "explanation": f"Candidate's degree ({cand_highest_degree}) fulfills the requirement ({jd_req_degree})."
            }
        elif cand_level > 0:
            return {
                "score": 75,
                "status": "PARTIAL",
                "explanation": f"Candidate possesses {cand_highest_degree}, whereas the posting requests {jd_req_degree}. Often accepted with relevant equivalent industry experience."
            }
        else:
            return {
                "score": 50,
                "status": "BELOW_REQUIREMENT",
                "explanation": f"Posting requests {jd_req_degree}, but candidate resume does not clearly specify an accredited degree."
            }

    @classmethod
    def _evaluate_ats_friction(
        cls,
        resume_content: Dict[str, Any],
        parsed_candidate: Dict[str, Any],
        parsed_jd: Dict[str, Any],
        missing_skills: List[MissingSkillDetail],
    ) -> List[ATSFrictionPoint]:
        """Identifies specific parsing friction points, formatting bottlenecks, and ATS risks."""
        friction_points: List[ATSFrictionPoint] = []

        # 1. Contact Info Verification
        if not resume_content.get("email"):
            friction_points.append(ATSFrictionPoint(
                rule="CONTACT_EMAIL",
                severity="CRITICAL",
                explanation="Missing candidate email address. Automated applicant tracking systems reject applications without contact identifiers.",
                recommendation="Add a professional email address at the top of your resume."
            ))

        if not resume_content.get("phone"):
            friction_points.append(ATSFrictionPoint(
                rule="CONTACT_PHONE",
                severity="WARNING",
                explanation="Missing phone number. Many ATS parsers require phone verification for recruiter SMS and screening stages.",
                recommendation="Include an international telephone number (+Country Code)."
            ))

        # 2. Metric and Quantification in Experience Bullets
        work_exp = parsed_candidate.get("work_experience") or []
        unquantified_bullets_count = 0
        total_bullets_count = 0
        weak_openings_found = []

        for exp in work_exp:
            bullets = exp.get("bullets") or []
            if isinstance(bullets, list):
                for b in bullets:
                    b_str = str(b).strip()
                    if not b_str:
                        continue
                    total_bullets_count += 1
                    # Check for metrics (% or $ or digits or multipliers like 3x)
                    if not re.search(r"(\d+%|\$\d+|\b\d+\b|\b\d+x\b)", b_str):
                        unquantified_bullets_count += 1

                    # Check for weak openings
                    for pat, msg in WEAK_BULLET_STARTS:
                        if re.search(pat, b_str.lower()):
                            weak_openings_found.append((b_str[:30], msg))
                            break

        if total_bullets_count > 0 and (unquantified_bullets_count / total_bullets_count) > 0.6:
            friction_points.append(ATSFrictionPoint(
                rule="UNQUANTIFIED_ACHIEVEMENTS",
                severity="WARNING",
                explanation=f"{unquantified_bullets_count} of {total_bullets_count} experience bullets lack quantifiable numbers, percentages, or revenue metrics.",
                recommendation="Adopt Google's XYZ formula: 'Accomplished [X] as measured by [Y], by doing [Z]' (e.g. 'Reduced API response latency by 42% by indexing PostgreSQL queries')."
            ))

        if weak_openings_found:
            sample_snippet, sample_fix = weak_openings_found[0]
            friction_points.append(ATSFrictionPoint(
                rule="WEAK_VERBS",
                severity="WARNING",
                explanation=f"Detected passive verb openings (e.g., '{sample_snippet}...').",
                recommendation=sample_fix
            ))

        # 3. Missing Critical Core Skills
        crit_missing = [s.skill for s in missing_skills if s.importance == "CRITICAL"]
        if crit_missing:
            friction_points.append(ATSFrictionPoint(
                rule="KEYWORD_ATS_DROP",
                severity="CRITICAL",
                explanation=f"Resume is missing essential JD keywords ({', '.join(crit_missing[:3])}). Many ATS algorithms apply strict keyword threshold gating.",
                recommendation=f"Incorporate verified experience with {', '.join(crit_missing[:3])} in your summary and experience bullet points."
            ))

        # 4. Professional Summary Check
        summary = (resume_content.get("summary") or "").strip()
        if not summary or len(summary) < 50:
            friction_points.append(ATSFrictionPoint(
                rule="MISSING_SUMMARY",
                severity="INFO",
                explanation="A concise professional summary aligned with the target role increases recruiter dwell time by 30%.",
                recommendation="Add a 2-3 sentence summary highlighting your core expertise, years in industry, and major domain impact."
            ))

        return friction_points

    @classmethod
    def _calculate_keyword_density(
        cls,
        parsed_jd: Dict[str, Any],
        candidate_text_corpus: str,
    ) -> int:
        """Calculates keyword density and domain terminology presence in candidate text."""
        req_skills = parsed_jd["required_skills"]
        if not req_skills:
            return 80

        corpus_lower = candidate_text_corpus.lower()
        found_count = 0

        for s in req_skills:
            pat = r"(?<!\w)" + re.escape(s.lower()) + r"(?!\w)"
            if re.search(pat, corpus_lower):
                found_count += 1

        density_pct = int(round((found_count / len(req_skills)) * 100))
        return max(15, min(100, density_pct))

    @classmethod
    def _generate_prioritized_action_items(
        cls,
        missing_skills: List[MissingSkillDetail],
        exp_analysis: Dict[str, Any],
        edu_analysis: Dict[str, Any],
        ats_friction: List[ATSFrictionPoint],
        keyword_score: int,
    ) -> List[str]:
        """Produces a ranked list of the top 3-5 high-yield actions for candidate to optimize resume."""
        items: List[str] = []

        # 1. Critical Missing Skills
        crit_missing = [s.skill for s in missing_skills if s.importance == "CRITICAL"]
        if crit_missing:
            items.append(f"Add key required technical competencies: incorporate verified hands-on experience with {', '.join(crit_missing[:3])}.")

        # 2. ATS Friction points (Critical first)
        for f in ats_friction:
            if f.severity == "CRITICAL":
                items.append(f"{f.rule}: {f.recommendation}")

        # 3. Experience Gap Compensation if needed
        if exp_analysis.get("status") == "BELOW_REQUIREMENT":
            items.append("Bridge experience delta by highlighting high-complexity deliverables, ownership, and measurable velocity.")

        # 4. Quantification & Metrics
        for f in ats_friction:
            if f.rule == "UNQUANTIFIED_ACHIEVEMENTS":
                items.append("Quantify bullet points: add metrics (e.g. % efficiency gains, $ cost savings, headcount led) to your work history.")
                break

        # 5. Summary Alignment
        if keyword_score < 70:
            items.append("Align resume summary with target job title and domain terminology to improve ATS semantic relevance scoring.")

        return items[:5]
