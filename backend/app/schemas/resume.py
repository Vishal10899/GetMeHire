from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

class WorkExperienceItem(BaseModel):
    company: str
    title: str
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    description: Optional[str] = None

class EducationItem(BaseModel):
    institution: str
    degree: Optional[str] = None
    field_of_study: Optional[str] = None
    graduation_year: Optional[int] = None

class ProjectItem(BaseModel):
    title: str
    description: Optional[str] = None
    technologies: List[str] = Field(default_factory=list)

class ResumeExtractedData(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    headline: Optional[str] = None
    summary: Optional[str] = None
    profession: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    technical_skills: List[str] = Field(default_factory=list)
    tools_technologies: List[str] = Field(default_factory=list)
    work_experience: List[WorkExperienceItem] = Field(default_factory=list)
    education: List[EducationItem] = Field(default_factory=list)
    projects: List[ProjectItem] = Field(default_factory=list)
    certifications: List[str] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    total_experience_years: Optional[float] = None

class ResumeUploadResponse(BaseModel):
    message: str
    filename: str
    profile_completion_pct: int
    download_url: str
    raw_text_preview: Optional[str] = None
    extracted_data: Optional[ResumeExtractedData] = None
    existing_data: Optional[Dict[str, Any]] = None
    conflicts: List[str] = Field(default_factory=list)

class ProfileReviewApprovalRequest(BaseModel):
    full_name: Optional[str] = None
    headline: Optional[str] = None
    phone_number: Optional[str] = None
    current_location: Optional[str] = None
    skills: Optional[List[str]] = None
    preferred_roles: Optional[List[str]] = None
    profession: Optional[str] = None
    total_experience_years: Optional[float] = None
    work_experience: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    projects: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[str]] = None
