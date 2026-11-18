"""
GetMeHire Early Career Intelligence Engine.
Advanced classification, experience extraction, and discovery intelligence
for Freshers, Recent Graduates, Interns, Trainees, and Early-Career Professionals.
"""

import re
from typing import Dict, List, Any, Optional, Tuple

# ---------------------------------------------------------------------------
# 1. TITLE PATTERNS & LEXICAL SIGNALS
# ---------------------------------------------------------------------------

TRUE_FRESHER_TITLE_PATTERNS = [
    r"\bfreshers?\b",
    r"\bzero\s*[- ]?experience\b",
    r"\bno\s*[- ]?experience\b",
    r"\bfirst\s*[- ]?time\s*(?:job\s*)?seekers?\b",
]

GRADUATE_TITLE_PATTERNS = [
    r"\b(?:recent|fresh|new)\s*graduates?\b",
    r"\bnew\s*grad\b",
    r"\buniversity\s*graduates?\b",
    r"\bgraduate\s*(?:engineer\s*)?trainee\b",
    r"\bgraduate\s*(?:program|programme|scheme|development|rotational)\b",
    r"\bcampus\s*(?:hiring|recruitment|drive)\b",
    r"\boff\s*[- ]?campus\b",
    r"\buniversity\s*recruiting\b",
    r"\bleadership\s*development\s*program\b",
    r"\bldp\b",
]

TRAINEE_TITLE_PATTERNS = [
    r"\bmanagement\s*trainee\b",
    r"\btechnical\s*trainee\b",
    r"\boperations\s*trainee\b",
    r"\bfinance\s*trainee\b",
    r"\bsales\s*trainee\b",
    r"\bhr\s*trainee\b",
    r"\btrainee\s*(?:associate|engineer|analyst|executive|officer)\b",
    r"\bget\b",  # Graduate Engineer Trainee
    r"\bmt\b",   # Management Trainee
]

INTERNSHIP_TITLE_PATTERNS = [
    r"\binternships?\b",
    r"\bintern\b",
    r"\bco-?op\b",
    r"\bcooperative\s*education\b",
    r"\bsummer\s*analyst\b",
    r"\bsummer\s*associate\b",
    r"\bstudent\s*worker\b",
    r"\bworking\s*student\b",
    r"\bfellowship\b",
    r"\bresearch\s*intern\b",
]

APPRENTICESHIP_TITLE_PATTERNS = [
    r"\bapprenticeships?\b",
    r"\bapprentice\b",
    r"\bausbildung\b",  # German dual education apprenticeship
    r"\bapprenti(?:e)?\b",
]

ENTRY_LEVEL_TITLE_PATTERNS = [
    r"\bentry\s*[- ]?level\b",
    r"\bassociate\b",
    r"\bjunior\b",
    r"\bjr\.?\b",
    r"\banalyst\s*(?:i|1)\b",
    r"\bengineer\s*(?:i|1)\b",
    r"\bdeveloper\s*(?:i|1)\b",
    r"\bsoftware\s*engineer\s*(?:i|1)\b",
    r"\bassistant\b",
    r"\bcoordinator\b",
    r"\bsupport\s*specialist\b",
    r"\bearly\s*(?:career|talent)\b",
]

SENIOR_EXCLUSION_TITLE_PATTERNS = [
    r"\bsenior\b",
    r"\bsr\.?\b",
    r"\blead\b",
    r"\bprincipal\b",
    r"\bstaff\b",
    r"\bdirector\b",
    r"\bvp\b",
    r"\bvice\s*president\b",
    r"\bhead\s*of\b",
    r"\bchief\b",
    r"\bmanager\b",
    r"\barchitect\b",
    r"\bii\b",
    r"\biii\b",
    r"\biv\b",
    r"\b2\b",
    r"\b3\b",
    r"\b4\b",
    r"\b5\b",
]

# ---------------------------------------------------------------------------
# 2. JOB DESCRIPTION EXPERIENCE EXTRACTION PATTERNS
# ---------------------------------------------------------------------------

EXPLICIT_ZERO_EXP_PATTERNS = [
    r"\b0\s*(?:years?|yrs?|months?)\s*(?:of\s+)?(?:experience|prior\s+experience)",
    r"\bzero\s*(?:years?|prior\s+experience|experience)",
    r"\bno\s*(?:prior\s+)?(?:work\s+)?experience\s*(?:is\s+)?(?:required|necessary|needed)",
    r"\bfreshers?\s*(?:are\s+)?(?:welcome|eligible|encouraged\s+to\s+apply)",
    r"\bopen\s*to\s*(?:freshers|recent\s*graduates|new\s*grads)",
    r"\bno\s*previous\s*employment\s*required\b",
    r"\bfirst\s*[- ]?time\s*(?:job\s*)?seekers?\b",
]

MANDATORY_EXP_REGEXES = [
    # "3+ years of experience required"
    re.compile(r"(\d+(?:\.\d+)?)\s*(?:\+|-\s*\d+)?\s*(?:to\s*\d+\s*)?(?:years?|yrs?)\s*(?:of\s+)?(?:relevant\s+|professional\s+|prior\s+|work\s+)?experience\s*(?:is\s+)?(?:required|mandatory|minimum|must\s+have)", re.IGNORECASE),
    # "requires a minimum of 2 years"
    re.compile(r"(?:requires?|must\s+have|minimum\s+of|at\s+least|with\s+at\s+least)\s*(\d+(?:\.\d+)?)\s*(?:\+|-\s*\d+)?\s*(?:years?|yrs?)", re.IGNORECASE),
    # "Minimum Qualifications: ... 5 years"
    re.compile(r"(?:minimum|basic|required)\s*qualifications?[\s\S]{0,120}?\b(\d+(?:\.\d+)?)\s*(?:\+|-\s*\d+)?\s*(?:years?|yrs?)", re.IGNORECASE),
    # "2-4 years experience"
    re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:-|to)\s*\d+\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience)", re.IGNORECASE),
    # "2+ years experience"
    re.compile(r"\b(\d+(?:\.\d+)?)\+\s*(?:years?|yrs?)\s*(?:of\s+)?(?:experience|work)", re.IGNORECASE),
]

PREFERRED_EXP_REGEXES = [
    re.compile(r"(?:preferred|nice\s+to\s+have|bonus|ideal|plus)[\s\S]{0,60}?\b(\d+(?:\.\d+)?)\s*(?:\+|-\s*\d+)?\s*(?:years?|yrs?)", re.IGNORECASE),
    re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:\+|-\s*\d+)?\s*(?:years?|yrs?)[\s\S]{0,60}?(?:is\s+a\s+plus|preferred|desired)", re.IGNORECASE),
]

ACADEMIC_EQUIVALENCE_PATTERNS = [
    r"academic\s*projects?",
    r"personal\s*projects?",
    r"coursework\s*(?:or|and)\s*projects?",
    r"internships?\s*(?:experience\s*)?(?:counts?|accepted|considered)",
    r"classroom\s*or\s*internship\s*experience",
    r"open\s*source\s*(?:contributions?|projects?)",
    r"hackathons?\s*(?:or|and)\s*competitions?",
    r"equivalent\s*combination\s*of\s*education",
    r"school\s*projects?",
    r"capstone\s*projects?",
]

TRAINING_PROVIDED_PATTERNS = [
    r"training\s*(?:will\s*be\s*)?provided",
    r"comprehensive\s*training\s*program",
    r"structured\s*mentorship",
    r"mentorship\s*from\s*senior",
    r"on\s*[- ]?the\s*[- ]?job\s*training",
    r"rotational\s*program",
    r"graduate\s*(?:development\s*)?program",
    r"we\s*(?:will\s*)?train\s*you",
    r"learn\s*on\s*the\s*job",
]

BATCH_YEAR_PATTERNS = [
    re.compile(r"\b(202[3-7])\s*(?:batch|passout|graduates?|graduating|pass-?outs?)", re.IGNORECASE),
    re.compile(r"(?:batch|graduating\s*class)\s*(?:of\s*)?(202[3-7])", re.IGNORECASE),
    re.compile(r"graduating\s*(?:between|in)\s*(?:winter|spring|summer|fall|december|may)?\s*(202[3-7])", re.IGNORECASE),
]


class EarlyCareerIntelligence:
    """
    Authoritative classification and deep requirement evaluation engine
    for early-career, fresher, graduate, and internship opportunities.
    """

    @classmethod
    def evaluate_job(
        cls,
        title: str,
        description: str,
        employment_type: Optional[str] = None,
        source_experience_level: Optional[str] = None,
        source_min_years: Optional[float] = None,
    ) -> Tuple[str, Dict[str, Any]]:
        """
        Deeply inspects job title, full description, and existing metadata.
        Returns:
            category: Canonical early career category string.
            metadata: Detailed dictionary containing extracted experience bounds,
                      eligibility flags, training signals, and transparent recommendations.
        """
        raw_title = (title or "").strip()
        t_lower = raw_title.lower()
        raw_desc = (description or "").strip()
        d_lower = raw_desc.lower()

        # -------------------------------------------------------------------
        # 1. Experience Requirements Extraction
        # -------------------------------------------------------------------
        extracted_mandatory_min: Optional[float] = None
        extracted_preferred_min: Optional[float] = None
        explicit_zero_exp = False
        training_provided = False
        academic_projects_accepted = False
        internships_count_as_exp = False
        eligible_graduation_years: List[int] = []

        # Check explicit 0-experience text
        for pat in EXPLICIT_ZERO_EXP_PATTERNS:
            if re.search(pat, d_lower) or re.search(pat, t_lower):
                explicit_zero_exp = True
                extracted_mandatory_min = 0.0
                break

        # Check training provided
        for pat in TRAINING_PROVIDED_PATTERNS:
            if re.search(pat, d_lower):
                training_provided = True
                break

        # Check academic/personal project acceptance
        for pat in ACADEMIC_EQUIVALENCE_PATTERNS:
            if re.search(pat, d_lower):
                academic_projects_accepted = True
                if "internship" in pat:
                    internships_count_as_exp = True

        # Check graduation batch years
        for reg in BATCH_YEAR_PATTERNS:
            matches = reg.findall(raw_desc)
            for m in matches:
                try:
                    yr = int(m)
                    if yr not in eligible_graduation_years:
                        eligible_graduation_years.append(yr)
                except (ValueError, TypeError):
                    pass

        # Split text to separate minimum qualifications vs preferred qualifications
        req_text, pref_text = cls._split_requirements_sections(raw_desc)

        # Check PhD/Doctorate requirement (PhD research interns are distinct from zero-experience freshers)
        is_phd_required = bool(re.search(r"\b(?:ph\.?d\.?|doctorate|doctoral)\b", raw_title, re.IGNORECASE))
        if not is_phd_required and req_text:
            is_phd_required = bool(re.search(r"\b(?:ph\.?d\.?|doctorate|doctoral\s+degree)\s*(?:in|or|required|mandatory)\b", req_text, re.IGNORECASE))

        # Check preferred experience
        if pref_text:
            # Inside dedicated preferred section, any mentioned year is preferred experience
            pref_matches = re.findall(r"\b(\d+(?:\.\d+)?)\s*(?:\+|-\s*\d+)?\s*(?:years?|yrs?)", pref_text, re.IGNORECASE)
            for m in pref_matches:
                try:
                    val = float(m)
                    if 0 <= val <= 30:
                        if extracted_preferred_min is None or val < extracted_preferred_min:
                            extracted_preferred_min = val
                except (ValueError, TypeError):
                    pass
        for reg in PREFERRED_EXP_REGEXES:
            m = reg.search(pref_text or raw_desc)
            if m:
                try:
                    val = float(m.group(1))
                    if extracted_preferred_min is None or val < extracted_preferred_min:
                        extracted_preferred_min = val
                except (ValueError, TypeError):
                    pass

        # Check mandatory experience (prioritize requirements section)
        if not explicit_zero_exp:
            search_target = req_text if req_text else raw_desc
            for reg in MANDATORY_EXP_REGEXES:
                for match in reg.finditer(search_target):
                    try:
                        val = float(match.group(1))
                        # Filter out unrealistic years (e.g. 2024 as year)
                        if 0 <= val <= 30:
                            if extracted_mandatory_min is None or val > extracted_mandatory_min:
                                extracted_mandatory_min = val
                    except (ValueError, TypeError):
                        pass

        # Reconcile with source_min_years if provided
        final_min_years: Optional[float] = extracted_mandatory_min
        if final_min_years is None and source_min_years is not None:
            final_min_years = float(source_min_years)

        # -------------------------------------------------------------------
        # 2. Title Signal Analysis
        # -------------------------------------------------------------------
        is_true_fresher_title = any(re.search(p, t_lower) for p in TRUE_FRESHER_TITLE_PATTERNS)
        is_grad_title = any(re.search(p, t_lower) for p in GRADUATE_TITLE_PATTERNS)
        is_trainee_title = any(re.search(p, t_lower) for p in TRAINEE_TITLE_PATTERNS)
        is_intern_title = any(re.search(p, t_lower) for p in INTERNSHIP_TITLE_PATTERNS)
        is_apprentice_title = any(re.search(p, t_lower) for p in APPRENTICESHIP_TITLE_PATTERNS)
        is_entry_title = any(re.search(p, t_lower) for p in ENTRY_LEVEL_TITLE_PATTERNS)
        is_senior_title = any(re.search(p, t_lower) for p in SENIOR_EXCLUSION_TITLE_PATTERNS)

        # Employment type checks
        emp_clean = (employment_type or "").upper().strip()
        is_intern_emp = emp_clean in ("INTERNSHIP", "CO-OP", "COOP")
        is_apprentice_emp = emp_clean == "APPRENTICESHIP"

        # -------------------------------------------------------------------
        # 3. Mislabelled Entry Level Detection (Critical Requirement)
        # -------------------------------------------------------------------
        is_mislabelled = False
        mislabelled_warning = None

        if is_entry_title or is_grad_title or is_trainee_title:
            if (final_min_years is not None and final_min_years >= 3.0) or (is_senior_title and not is_intern_title):
                is_mislabelled = True
                mislabelled_warning = (
                    f"Title suggests early career ('{raw_title}'), but description strictly requires "
                    f"{final_min_years or 3}+ years of mandatory professional experience."
                )

        # -------------------------------------------------------------------
        # 4. Canonical Category Classification
        # -------------------------------------------------------------------
        category = "UNCERTAIN"
        reasons: List[str] = []

        if is_mislabelled:
            category = "MISLABELLED_ENTRY_LEVEL"
            reasons.append(mislabelled_warning or "Requires 3+ years experience despite entry-level title.")

        elif is_senior_title and not is_intern_title and not is_trainee_title:
            category = "EXPERIENCED"
            reasons.append(f"Senior functional title ('{raw_title}').")

        elif is_intern_title or is_intern_emp:
            category = "INTERNSHIP"
            reasons.append("Dedicated student, university, or graduate internship role.")
            if "paid" in t_lower or "stipend" in d_lower or "paid" in d_lower:
                reasons.append("Compensation/stipend mentioned.")

        elif is_apprentice_title or is_apprentice_emp:
            category = "APPRENTICESHIP"
            reasons.append("Structured practical training / apprenticeship program.")

        elif is_true_fresher_title or explicit_zero_exp:
            category = "TRUE_FRESHER"
            reasons.append("Explicitly requires 0 prior professional experience.")
            if training_provided:
                reasons.append("Comprehensive training provided on the job.")
            if academic_projects_accepted:
                reasons.append("Academic coursework, personal projects, or hackathons welcomed.")

        elif is_grad_title or eligible_graduation_years:
            category = "GRADUATE"
            reasons.append("Specifically designed for university students and recent graduates.")
            if eligible_graduation_years:
                reasons.append(f"Targeting graduation batches: {', '.join(str(y) for y in sorted(eligible_graduation_years))}.")
            if training_provided:
                reasons.append("Structured mentorship and rotational training scheme.")

        elif is_trainee_title:
            category = "TRAINEE"
            reasons.append("Structured corporate or technical trainee program.")
            if training_provided:
                reasons.append("On-the-job training provided.")

        elif final_min_years is not None and final_min_years <= 1.0:
            category = "ENTRY_LEVEL"
            reasons.append(f"Entry-level opportunity (requires {final_min_years} years or less).")
            if final_min_years == 0:
                category = "TRUE_FRESHER"

        elif final_min_years is not None and final_min_years <= 2.0:
            category = "EARLY_CAREER"
            reasons.append(f"Early-career opportunity (requires {final_min_years} years experience).")

        elif is_entry_title:
            if final_min_years is None:
                category = "ENTRY_LEVEL"
                reasons.append("Designated as Entry Level / Associate with flexible experience expectations.")
            elif final_min_years <= 2.0:
                category = "JUNIOR"
                reasons.append(f"Junior position with {final_min_years} years expected experience.")

        elif academic_projects_accepted and (final_min_years is None or final_min_years <= 1.5):
            category = "EXPERIENCE_FLEXIBLE"
            reasons.append("Prior professional employment flexible; academic or personal projects accepted.")

        elif not is_senior_title and final_min_years is None and ((extracted_preferred_min is not None and extracted_preferred_min <= 2.0) or training_provided):
            category = "EXPERIENCE_FLEXIBLE"
            reasons.append("No mandatory experience required; early-career suitable.")

        elif final_min_years is not None and final_min_years >= 3.0:
            category = "EXPERIENCED"
            reasons.append(f"Requires {final_min_years}+ years of professional experience.")

        else:
            category = "UNCERTAIN"

        # Determine broader boolean flag
        is_fresher_friendly = category in [
            "TRUE_FRESHER", "GRADUATE", "ENTRY_LEVEL", "EARLY_CAREER", "JUNIOR", "TRAINEE",
            "INTERNSHIP", "APPRENTICESHIP", "EXPERIENCE_FLEXIBLE"
        ] and not is_mislabelled

        # Build rich metadata
        metadata = {
            "is_fresher_friendly": is_fresher_friendly,
            "category": category,
            "min_experience_years": final_min_years,
            "preferred_experience_years": extracted_preferred_min,
            "is_experience_mandatory": (final_min_years is not None and final_min_years > 0 and not academic_projects_accepted),
            "academic_projects_accepted": academic_projects_accepted,
            "internships_count_as_exp": internships_count_as_exp,
            "training_provided": training_provided,
            "eligible_graduation_years": eligible_graduation_years,
            "is_phd_required": is_phd_required,
            "education_level": "PHD" if is_phd_required else "BACHELOR_OR_GENERAL",
            "is_mislabelled": is_mislabelled,
            "mislabelled_warning": mislabelled_warning,
            "recommendation_reasons": reasons,
        }

        return category, metadata

    @staticmethod
    def _split_requirements_sections(text: str) -> Tuple[str, str]:
        """
        Splits job description into explicit requirements vs preferred sections.
        """
        req_parts = []
        pref_parts = []
        
        lines = text.split("\n")
        current_section = "general"
        
        for line in lines:
            line_l = line.lower().strip()
            if any(k in line_l for k in ["preferred qualifications", "nice to have", "bonus points", "desired skills", "what sets you apart"]):
                current_section = "preferred"
                continue
            elif any(k in line_l for k in ["minimum qualifications", "basic qualifications", "requirements", "must have", "what you'll need"]):
                current_section = "requirements"
                continue
            elif any(k in line_l for k in ["about us", "company benefits", "perks", "equal opportunity"]):
                current_section = "other"
                continue
                
            if current_section == "requirements":
                req_parts.append(line)
            elif current_section == "preferred":
                pref_parts.append(line)
                
        return "\n".join(req_parts), "\n".join(pref_parts)
