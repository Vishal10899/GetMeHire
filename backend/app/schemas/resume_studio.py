from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from datetime import datetime

# Authoritative Allowed Template IDs (Legacy + 16 Role-Specific Architectures)
AllowedTemplateId = Literal[
    "classic_single",
    "modern_professional",
    "compact_technical",
    "data_analytics",
    "executive_leadership",
    "software_engineering",
    "ai_ml_engineer",
    "data_analyst",
    "data_scientist",
    "product_manager",
    "business_analyst",
    "banking_finance",
    "accountant_audit",
    "enterprise_sales",
    "marketing_growth",
    "healthcare_nursing",
    "doctor_surgeon",
    "human_resources",
    "legal_compliance",
    "operations_supply_chain",
]

class ResumeContentSchema(BaseModel):
    full_name: str
    headline: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    technical_skills: List[str] = Field(default_factory=list)
    tools_technologies: List[str] = Field(default_factory=list)
    work_experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[Any] = Field(default_factory=list)
    target_role: Optional[str] = None
    target_company: Optional[str] = None

class ResumeAnalysisFinding(BaseModel):
    id: str
    category: str  # contact, summary, experience, skills, education, structure
    severity: str  # CRITICAL, WARNING, INFO
    title: str
    explanation: str
    suggested_correction: str
    evidence: Optional[str] = None

class ResumeAnalysisResponse(BaseModel):
    overall_score: int
    score_breakdown: Dict[str, int]
    ats_compatibility: str  # EXCELLENT, GOOD, NEEDS_IMPROVEMENT, POOR
    findings: List[ResumeAnalysisFinding]
    disclaimer: str

class TailorResumeRequest(BaseModel):
    job_id: int
    base_version_id: Optional[int] = None
    custom_instructions: Optional[str] = None

class TailorResumeResponse(BaseModel):
    target_job_id: int
    target_job_title: str
    target_company_name: str
    match_score_before: int
    match_score_after: int
    matched_skills: List[str]
    adjacent_skills: List[str]
    missing_skills: List[str]
    tailored_content: Dict[str, Any]
    tailored_summary_options: List[str]
    improvement_notes: List[str]

class ImproveBulletRequest(BaseModel):
    bullet_text: str
    role_title: Optional[str] = None
    target_keywords: Optional[List[str]] = None

class ImproveBulletResponse(BaseModel):
    original: str
    improved_options: List[Dict[str, str]]
    coaching_questions: List[str]

class ImproveSummaryRequest(BaseModel):
    current_summary: Optional[str] = None
    target_role: Optional[str] = None
    years_of_experience: Optional[float] = None
    top_skills: Optional[List[str]] = None

class ImproveSummaryResponse(BaseModel):
    options: List[Dict[str, str]]

class SaveResumeVersionRequest(BaseModel):
    version_title: str
    target_job_id: Optional[int] = None
    template_id: AllowedTemplateId = "classic_single"
    content: Dict[str, Any]
    is_master: Optional[bool] = False

class ResumeVersionResponse(BaseModel):
    id: int
    version_title: str
    version_number: int
    target_job_id: Optional[int] = None
    target_job_title: Optional[str] = None
    target_company_name: Optional[str] = None
    template_id: str
    content: Dict[str, Any]
    analysis: Optional[Dict[str, Any]] = None
    is_master: bool
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Bidirectional Job Description & ATS Deep Matching Schemas
# ---------------------------------------------------------------------------

class JDMatchRequest(BaseModel):
    job_id: Optional[int] = None
    job_title: Optional[str] = None
    job_description_text: Optional[str] = None
    company_name: Optional[str] = None
    version_id: Optional[int] = None
    resume_content: Optional[Dict[str, Any]] = None


class MatchedSkillDetail(BaseModel):
    skill: str
    in_resume: bool
    is_required: bool
    resume_evidence: Optional[str] = None


class MissingSkillDetail(BaseModel):
    skill: str
    importance: str  # CRITICAL, HIGH, MEDIUM, NICE_TO_HAVE
    is_required: bool
    suggestion: str


class ExperienceAnalysis(BaseModel):
    jd_required_years: Optional[float] = None
    candidate_years: float
    status: str  # MATCHED, SURPASSED, BELOW_REQUIREMENT, UNSPECIFIED
    explanation: str


class EducationAnalysis(BaseModel):
    jd_required_degree: Optional[str] = None
    candidate_highest_degree: Optional[str] = None
    status: str  # MATCHED, SURPASSED, PARTIAL, UNSPECIFIED
    explanation: str


class ATSFrictionPoint(BaseModel):
    rule: str
    severity: str  # CRITICAL, WARNING, INFO
    explanation: str
    recommendation: str


class JDMatchResponse(BaseModel):
    target_job_title: str
    target_company_name: str
    overall_match_score: int  # 0-100
    score_breakdown: Dict[str, int]  # skills, experience, education, keyword_density, formatting
    matched_skills: List[MatchedSkillDetail]
    missing_skills: List[MissingSkillDetail]
    adjacent_skills: List[str]
    experience_analysis: ExperienceAnalysis
    education_analysis: EducationAnalysis
    ats_friction_points: List[ATSFrictionPoint]
    prioritized_action_items: List[str]
    recommended_template: Dict[str, Any]
    disclaimer: str


# ---------------------------------------------------------------------------
# Role-Specific Resume Template Schemas
# ---------------------------------------------------------------------------

class RoleTemplateItem(BaseModel):
    id: str
    name: str
    profession: str
    description: str
    recommended_sections_order: List[str]
    section_titles: Dict[str, str]
    color_palette: Dict[str, str]
    content_guidelines: List[str]
    power_verbs: List[str]
    ats_priority_keywords: List[str]


class RoleTemplatesResponse(BaseModel):
    templates: List[RoleTemplateItem]
    total: int

