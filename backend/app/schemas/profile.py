from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from decimal import Decimal
from app.schemas.resume import ResumeUploadResponse, ResumeExtractedData, WorkExperienceItem, EducationItem, ProjectItem

class CareerInterest(BaseModel):
    profession: str
    preferred_roles: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    experience_years: Optional[float] = None

class ProfileBase(BaseModel):
    full_name: Optional[str] = None
    headline: Optional[str] = None
    phone_number: Optional[str] = None
    current_location: Optional[str] = None
    linkedin_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    profession: Optional[str] = None
    skills: List[str] = Field(default_factory=list)
    preferred_roles: List[str] = Field(default_factory=list)
    career_interests: List[CareerInterest] = Field(default_factory=list)
    recent_searches: List[str] = Field(default_factory=list)
    total_experience_years: Optional[float] = None
    relevant_experience_years: Optional[float] = None
    preferred_countries: List[str] = Field(default_factory=list)
    preferred_locations: List[str] = Field(default_factory=list)
    work_arrangements: List[str] = Field(default_factory=list)  # REMOTE, HYBRID, ONSITE
    employment_types: List[str] = Field(default_factory=list)  # FULL_TIME, PART_TIME, CONTRACT, INTERNSHIP
    salary_expectation_min: Optional[Decimal] = None
    salary_expectation_max: Optional[Decimal] = None
    salary_currency: Optional[str] = "USD"
    salary_period: Optional[str] = "YEAR"
    work_experience: List[Dict[str, Any]] = Field(default_factory=list)
    education: List[Dict[str, Any]] = Field(default_factory=list)
    projects: List[Dict[str, Any]] = Field(default_factory=list)
    certifications: List[Any] = Field(default_factory=list)
    extracted_resume_data: Dict[str, Any] = Field(default_factory=dict)

class ProfileUpdate(ProfileBase):
    pass

class ProfileResponse(ProfileBase):
    id: int
    user_id: int
    resume_filename: Optional[str] = None
    resume_uploaded_at: Optional[datetime] = None
    profile_completion_pct: int
    visited_jobs_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
