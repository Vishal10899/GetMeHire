from typing import List, Optional
from pydantic import BaseModel, Field
from app.schemas.job import JobListResponseItem

class MatchBreakdown(BaseModel):
    skill_score: float
    role_score: float
    location_score: float
    experience_score: float
    total_score: float
    matched_skills: List[str] = Field(default_factory=list)
    missing_skills: List[str] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    has_sufficient_data: bool = True
    insufficient_data_reasons: List[str] = Field(default_factory=list)
    location_eligibility: Optional[str] = None
    experience_alignment: Optional[str] = None
    score_disclaimer: str = "Match score reflects qualification fit and profile alignment; it does not indicate hiring probability."

class RecommendationItem(BaseModel):
    job: JobListResponseItem
    match_score: int  # 0 to 100
    match_breakdown: MatchBreakdown

class RecommendationResponse(BaseModel):
    algorithm_version: str = "v2.0-evidence-based-matching"
    items: List[RecommendationItem]
    total: int
    has_sufficient_data: bool = True
    insufficient_data_reasons: List[str] = Field(default_factory=list)
    disclaimer: str = "Match scores reflect qualification fit and profile alignment; they do not represent hiring probability."
