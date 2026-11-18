import re
from typing import Dict, List, Any, Optional, Tuple
from app.schemas.resume_studio import ResumeAnalysisResponse, ResumeAnalysisFinding
from app.services.resume_parser import CANONICAL_SKILLS, TECH_SKILLS_SET, TOOLS_TECH_SET

ACTION_VERBS = {
    "architected", "engineered", "developed", "built", "spearheaded", "accelerated",
    "automated", "designed", "optimized", "implemented", "scaled", "reduced",
    "increased", "mentored", "orchestrated", "delivered", "deployed", "transformed",
    "streamlined", "formulated", "executed", "launched", "integrated", "negotiated"
}

WEAK_OPENINGS = [
    r"^responsible\s+for",
    r"^assisted\s+(?:with|in)",
    r"^helped\s+(?:with|to)",
    r"^worked\s+(?:on|with)",
    r"^participated\s+in",
    r"^duties\s+included",
    r"^tasked\s+with",
    r"^handled",
]

CLICHES = [
    "hardworking", "team player", "go-getter", "detail-oriented", "synergy",
    "think outside the box", "self-starter", "results-driven", "fast-paced environment"
]

class ResumeAnalyzerService:
    """
    Smart algorithmic ATS and resume quality analyzer.
    Evaluates resumes deterministically without paid cloud AI APIs.
    """

    @classmethod
    def analyze_resume(cls, content: Dict[str, Any]) -> ResumeAnalysisResponse:
        findings: List[ResumeAnalysisFinding] = []
        finding_idx = 1

        # ----------------------------------------------------------------------
        # 1. Contact Information Analysis (Weight: 15 points)
        # ----------------------------------------------------------------------
        contact_score = 15
        full_name = (content.get("full_name") or "").strip()
        email = (content.get("email") or "").strip()
        phone = (content.get("phone") or "").strip()
        location = (content.get("location") or "").strip()
        linkedin = (content.get("linkedin_url") or "").strip()

        if not full_name:
            contact_score -= 5
            findings.append(ResumeAnalysisFinding(
                id=f"CNT-{finding_idx}",
                category="contact",
                severity="CRITICAL",
                title="Missing Candidate Name",
                explanation="Your resume must clearly state your full legal or professional name at the top.",
                suggested_correction="Add your full name as the primary top header (e.g., 'Jane Doe').",
                evidence=None
            ))
            finding_idx += 1

        if not email or "@" not in email:
            contact_score -= 5
            findings.append(ResumeAnalysisFinding(
                id=f"CNT-{finding_idx}",
                category="contact",
                severity="CRITICAL",
                title="Missing or Invalid Email Address",
                explanation="Recruiters and automated ATS systems communicate primarily via email.",
                suggested_correction="Provide a professional personal email (e.g., 'first.last@gmail.com').",
                evidence=email or "Missing"
            ))
            finding_idx += 1

        if not phone:
            contact_score -= 2
            findings.append(ResumeAnalysisFinding(
                id=f"CNT-{finding_idx}",
                category="contact",
                severity="WARNING",
                title="Missing Phone Number",
                explanation="Many recruiting pipelines perform initial outreach or screening via phone/SMS.",
                suggested_correction="Add an international-format telephone number (e.g., '+1 (555) 012-3456').",
                evidence=None
            ))
            finding_idx += 1

        if not location:
            contact_score -= 2
            findings.append(ResumeAnalysisFinding(
                id=f"CNT-{finding_idx}",
                category="contact",
                severity="WARNING",
                title="Missing Geographic Location",
                explanation="ATS parsers filter candidate records by geographic eligibility, tax jurisdiction, or timezone.",
                suggested_correction="Include your City and Country or State (e.g., 'London, United Kingdom' or 'Bengaluru, India').",
                evidence=None
            ))
            finding_idx += 1

        if not linkedin:
            contact_score -= 1
            findings.append(ResumeAnalysisFinding(
                id=f"CNT-{finding_idx}",
                category="contact",
                severity="INFO",
                title="No LinkedIn or Portfolio URL",
                explanation="Adding a verified professional profile URL increases candidate trust and engagement.",
                suggested_correction="Include a direct link to your LinkedIn profile or GitHub/portfolio.",
                evidence=None
            ))
            finding_idx += 1

        contact_score = max(0, contact_score)

        # ----------------------------------------------------------------------
        # 2. Professional Summary Analysis (Weight: 15 points)
        # ----------------------------------------------------------------------
        summary_score = 15
        summary = (content.get("summary") or "").strip()

        if not summary:
            summary_score = 4
            findings.append(ResumeAnalysisFinding(
                id=f"SUM-{finding_idx}",
                category="summary",
                severity="WARNING",
                title="Missing Professional Summary",
                explanation="A concise 3-4 sentence professional summary provides human recruiters with immediate context and highlights your target value proposition.",
                suggested_correction="Draft a punchy summary highlighting your title, core technical specialties, years of experience, and primary accomplishments.",
                evidence=None
            ))
            finding_idx += 1
        else:
            word_count = len(summary.split())
            if word_count < 25:
                summary_score -= 4
                findings.append(ResumeAnalysisFinding(
                    id=f"SUM-{finding_idx}",
                    category="summary",
                    severity="WARNING",
                    title="Professional Summary Too Brief",
                    explanation=f"Your summary is only {word_count} words. It may not provide enough context or relevant keywords for ATS parsing.",
                    suggested_correction="Expand to 40-75 words emphasizing your primary domain, key technical skills, and high-impact accomplishments.",
                    evidence=summary
                ))
                finding_idx += 1
            elif word_count > 120:
                summary_score -= 3
                findings.append(ResumeAnalysisFinding(
                    id=f"SUM-{finding_idx}",
                    category="summary",
                    severity="INFO",
                    title="Professional Summary Lengthy",
                    explanation=f"Your summary is {word_count} words. Recruiters spend an average of 6-8 seconds on initial review and prefer concise overviews.",
                    suggested_correction="Trim the summary to 3-4 focused sentences (around 50-80 words).",
                    evidence=summary[:120] + "..."
                ))
                finding_idx += 1

            # First person pronoun check
            first_person = re.findall(r"\b(I|me|my|we|our)\b", summary, re.IGNORECASE)
            if first_person:
                summary_score -= 2
                findings.append(ResumeAnalysisFinding(
                    id=f"SUM-{finding_idx}",
                    category="summary",
                    severity="INFO",
                    title="First-Person Pronouns in Summary",
                    explanation="Modern resume standards avoid first-person pronouns ('I', 'my', 'we').",
                    suggested_correction="Rephrase in implied third-person (e.g., replace 'I have 5 years experience' with 'Software Engineer with 5+ years of experience').",
                    evidence=f"Found: {', '.join(set(first_person))}"
                ))
                finding_idx += 1

            # Cliché check
            matched_cliches = [c for c in CLICHES if c in summary.lower()]
            if matched_cliches:
                summary_score -= 2
                findings.append(ResumeAnalysisFinding(
                    id=f"SUM-{finding_idx}",
                    category="summary",
                    severity="INFO",
                    title="Generic Buzzwords in Summary",
                    explanation=f"Found overused buzzwords: {', '.join(matched_cliches)}. These reduce credibility compared to concrete technical competencies.",
                    suggested_correction="Replace generic adjectives with specific technical domains, frameworks, or measurable capabilities.",
                    evidence=f"Contains: {', '.join(matched_cliches)}"
                ))
                finding_idx += 1

        summary_score = max(0, summary_score)

        # ----------------------------------------------------------------------
        # 3. Work Experience Quality Analysis (Weight: 30 points)
        # ----------------------------------------------------------------------
        exp_score = 30
        experiences = content.get("work_experience") or []
        projects = content.get("projects") or []
        is_early_career = content.get("is_early_career") or bool(re.search(r"\b(?:fresher|student|graduate|entry[- ]level|intern)\b", str(content.get("summary") or "") + " " + str(content.get("headline") or ""), re.IGNORECASE))

        if not experiences:
            if projects:
                # Early Career Profile: evaluate projects as primary practical experience
                exp_score = min(28, 18 + len(projects) * 3)
                findings.append(ResumeAnalysisFinding(
                    id=f"EXP-{finding_idx}",
                    category="experience",
                    severity="INFO",
                    title="Early Career Profile: Practical Projects Evaluated",
                    explanation=f"No corporate work history listed, but {len(projects)} practical project(s) identified. Evaluated under Early Career Intelligence standards.",
                    suggested_correction="Ensure each project highlights architecture, tools/libraries used, and measurable results or active repository links.",
                    evidence=f"{len(projects)} project(s) listed"
                ))
                finding_idx += 1
            else:
                exp_score = 5
                findings.append(ResumeAnalysisFinding(
                    id=f"EXP-{finding_idx}",
                    category="experience",
                    severity="CRITICAL",
                    title="No Work Experience or Projects Listed",
                    explanation="Professional work experience is the single highest-weighted section on an ATS resume.",
                    suggested_correction="Add your current or past employment, internships, or relevant consulting engagements.",
                    evidence=None
                ))
                finding_idx += 1
        else:
            total_bullets = 0
            weak_verb_bullets = []
            action_verb_bullets = 0
            metric_bullets = 0

            metric_pattern = re.compile(
                r"\b(?:\d+(?:\.\d+)?%|\$\d+(?:,\d+)*(?:\.\d+)?|\d+\s*(?:k|m|million|billion|users|customers|requests|qps|tb|gb|hours|days|x))\b|\b\d{2,}\b",
                re.IGNORECASE
            )

            for exp in experiences:
                raw_lines = []
                if isinstance(exp.get("bullets"), list):
                    raw_lines.extend([str(b).strip() for b in exp.get("bullets") if str(b).strip()])
                if exp.get("description"):
                    raw_lines.extend([l.strip() for l in re.split(r"[\n•\-\*]", str(exp.get("description"))) if l.strip()])

                total_bullets += len(raw_lines)

                for line in raw_lines:
                    first_word = line.split()[0].lower().rstrip(",:;.")
                    if first_word in ACTION_VERBS:
                        action_verb_bullets += 1

                    for weak_pat in WEAK_OPENINGS:
                        if re.search(weak_pat, line, re.IGNORECASE):
                            weak_verb_bullets.append(line)
                            break

                    if metric_pattern.search(line):
                        metric_bullets += 1

            if total_bullets < 3:
                exp_score -= 8
                findings.append(ResumeAnalysisFinding(
                    id=f"EXP-{finding_idx}",
                    category="experience",
                    severity="WARNING",
                    title="Sparse Experience Descriptions",
                    explanation=f"Found only {total_bullets} bullet point(s) across all positions. ATS scanners expect detailed accomplishment statements.",
                    suggested_correction="Provide 3-5 achievement bullet points for each recent role.",
                    evidence=None
                ))
                finding_idx += 1

            if weak_verb_bullets:
                penalty = min(8, len(weak_verb_bullets) * 2)
                exp_score -= penalty
                sample_weak = weak_verb_bullets[0]
                findings.append(ResumeAnalysisFinding(
                    id=f"EXP-{finding_idx}",
                    category="experience",
                    severity="WARNING",
                    title="Passive Openings in Experience Bullets",
                    explanation=f"{len(weak_verb_bullets)} bullet(s) start with passive phrases (e.g. 'Responsible for', 'Assisted with').",
                    suggested_correction="Use strong action verbs such as 'Architected', 'Automated', 'Spearheaded', 'Optimized', or 'Engineered'.",
                    evidence=sample_weak[:90] + "..." if len(sample_weak) > 90 else sample_weak
                ))
                finding_idx += 1

            if total_bullets > 0 and metric_bullets == 0:
                exp_score -= 8
                findings.append(ResumeAnalysisFinding(
                    id=f"EXP-{finding_idx}",
                    category="experience",
                    severity="WARNING",
                    title="No Quantifiable Metrics in Work Experience",
                    explanation="None of your experience statements include measurable numbers, percentages, or scale metrics. Top resumes quantify impact.",
                    suggested_correction="Include tangible metrics (e.g., 'Reduced query latency by 45%', 'Scaled backend to 500k DAU', 'Saved 12 engineering hours/week').",
                    evidence=None
                ))
                finding_idx += 1
            elif total_bullets > 0 and (metric_bullets / total_bullets) < 0.3:
                exp_score -= 3
                findings.append(ResumeAnalysisFinding(
                    id=f"EXP-{finding_idx}",
                    category="experience",
                    severity="INFO",
                    title="Low Percentage of Quantified Achievements",
                    explanation=f"Only {metric_bullets} of {total_bullets} bullets ({int(metric_bullets/total_bullets*100)}%) contain quantifiable results.",
                    suggested_correction="Aim for at least 40-50% of bullet points to feature measurable outcomes.",
                    evidence=None
                ))
                finding_idx += 1

        exp_score = max(0, exp_score)

        # ----------------------------------------------------------------------
        # 4. Skills Coverage Analysis (Weight: 20 points)
        # ----------------------------------------------------------------------
        skills_score = 20
        skills = content.get("skills") or []
        tech_skills = content.get("technical_skills") or []
        tools_tech = content.get("tools_technologies") or []
        all_skills_combined = list(dict.fromkeys(skills + tech_skills + tools_tech))

        if len(all_skills_combined) == 0:
            skills_score = 2
            findings.append(ResumeAnalysisFinding(
                id=f"SKL-{finding_idx}",
                category="skills",
                severity="CRITICAL",
                title="Missing Skills Section",
                explanation="ATS parsers rely heavily on a structured skills section to calculate query relevance.",
                suggested_correction="Add 8 to 20 relevant technical, platform, and domain skills to your profile.",
                evidence=None
            ))
            finding_idx += 1
        elif len(all_skills_combined) < 6:
            skills_score -= 8
            findings.append(ResumeAnalysisFinding(
                id=f"SKL-{finding_idx}",
                category="skills",
                severity="WARNING",
                title="Limited Skills Listed",
                explanation=f"Only {len(all_skills_combined)} skills listed. This lowers your keyword match rate across related job openings.",
                suggested_correction="Add foundational languages, databases, cloud tools, and frameworks you actively use.",
                evidence=f"Current: {', '.join(all_skills_combined)}"
            ))
            finding_idx += 1
        elif len(all_skills_combined) > 35:
            skills_score -= 4
            findings.append(ResumeAnalysisFinding(
                id=f"SKL-{finding_idx}",
                category="skills",
                severity="INFO",
                title="Excessive Skills Listed (Keyword Stuffing Risk)",
                explanation=f"Listing {len(all_skills_combined)} skills can appear as keyword stuffing to human hiring managers and dilute your core strengths.",
                suggested_correction="Curate your top 12-25 most proficient and relevant skills.",
                evidence=f"Found {len(all_skills_combined)} skills"
            ))
            finding_idx += 1

        skills_score = max(0, skills_score)

        # ----------------------------------------------------------------------
        # 5. Education & Credentials Analysis (Weight: 10 points)
        # ----------------------------------------------------------------------
        edu_score = 10
        education = content.get("education") or []
        certs = content.get("certifications") or []

        if not education:
            edu_score -= 6
            findings.append(ResumeAnalysisFinding(
                id=f"EDU-{finding_idx}",
                category="education",
                severity="WARNING",
                title="No Education Listed",
                explanation="Many ATS screening filters require at least one degree, diploma, or educational milestone.",
                suggested_correction="Add your degree, field of study, and institution name.",
                evidence=None
            ))
            finding_idx += 1
        else:
            for ed in education:
                if not ed.get("institution"):
                    edu_score -= 2
                    findings.append(ResumeAnalysisFinding(
                        id=f"EDU-{finding_idx}",
                        category="education",
                        severity="WARNING",
                        title="Missing Educational Institution",
                        explanation="Each education entry should specify the university, college, or school.",
                        suggested_correction="Add the university or institution name.",
                        evidence=str(ed)
                    ))
                    finding_idx += 1
                    break

        edu_score = max(0, edu_score)

        # ----------------------------------------------------------------------
        # 6. Structure & ATS Formatting (Weight: 10 points)
        # ----------------------------------------------------------------------
        struct_score = 10
        projects = content.get("projects") or []

        if len(projects) == 0 and len(experiences) <= 1:
            struct_score -= 3
            findings.append(ResumeAnalysisFinding(
                id=f"STR-{finding_idx}",
                category="structure",
                severity="INFO",
                title="Add a Projects Section",
                explanation="For junior to mid-level engineers, showcasing open-source or production projects demonstrates practical expertise.",
                suggested_correction="Add 1-3 technical projects highlighting key architecture and tools.",
                evidence=None
            ))
            finding_idx += 1

        overall_score = contact_score + summary_score + exp_score + skills_score + edu_score + struct_score
        overall_score = max(5, min(100, overall_score))

        if overall_score >= 85:
            compatibility = "EXCELLENT"
        elif overall_score >= 70:
            compatibility = "GOOD"
        elif overall_score >= 50:
            compatibility = "NEEDS_IMPROVEMENT"
        else:
            compatibility = "POOR"

        score_breakdown = {
            "contact_information": contact_score,
            "professional_summary": summary_score,
            "work_experience": exp_score,
            "skills_coverage": skills_score,
            "education_and_credentials": edu_score,
            "ats_readability_structure": struct_score,
        }

        disclaimer = (
            "This score represents an algorithmic structural audit of ATS readability, completeness, "
            "and keyword balance. It does not represent an actual employer's hiring decision."
        )

        return ResumeAnalysisResponse(
            overall_score=overall_score,
            score_breakdown=score_breakdown,
            ats_compatibility=compatibility,
            findings=findings,
            disclaimer=disclaimer
        )
