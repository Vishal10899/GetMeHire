from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.deps import get_db, get_current_user
from app.models import User
from app.schemas.recommendation import RecommendationResponse
from app.services.matching_service import MatchingService

router = APIRouter()

@router.get("", response_model=RecommendationResponse)
@router.get("/matches", response_model=RecommendationResponse)
def get_recommendations(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    profession: Optional[str] = Query(None, description="Scope recommendations to a specific career interest track"),
    min_score: Optional[int] = Query(None, ge=0, le=100, description="Filter jobs with at least this match score"),
    remote_type: Optional[str] = Query(None, description="Filter by remote work arrangement (REMOTE, HYBRID, ONSITE)"),
    location: Optional[str] = Query(None, description="Filter by location keyword or country"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """
    Returns personalized, explainable job matches ranked by evidence-based match score.
    Supports filtering by career track, minimum match score, remote eligibility, and location.
    Requires authenticated candidate session to ensure multi-tenant candidate isolation.
    """
    return MatchingService.get_recommendations_for_user(
        db,
        current_user,
        profession=profession,
        min_score=min_score,
        remote_type=remote_type,
        location=location,
        limit=limit,
        offset=offset
    )
