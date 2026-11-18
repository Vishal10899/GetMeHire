import pytest
from app.services.matching_service import MatchingService
from app.models import Profile, Job

def test_explainable_match_score_calculation():
    profile = Profile(
        skills=["Python", "FastAPI", "React", "AWS"],
        preferred_roles=["Senior Software Engineer"],
        work_arrangements=["REMOTE"],
        preferred_countries=["United States"],
        relevant_experience_years=5.0
    )

    perfect_job = Job(
        title="Senior Software Engineer - Python",
        description="Looking for Python, FastAPI, and AWS skills.",
        remote_type="REMOTE",
        country="United States",
        min_experience_years=4.0,
        skills=["Python", "FastAPI", "AWS"]
    )

    breakdown = MatchingService.calculate_match(profile, perfect_job)
    assert breakdown.total_score >= 80.0
    assert len(breakdown.matched_skills) >= 2
    assert len(breakdown.reasons) >= 3

def test_matching_with_missing_fields():
    # Verify neutral fallback defect is fixed: missing candidate info earns 0 positive points
    blank_profile = Profile(
        skills=[],
        preferred_roles=[],
        work_arrangements=[]
    )

    job_no_skills = Job(
        title="General Engineer",
        description="General description.",
        remote_type="ONSITE",
        skills=[]
    )

    breakdown = MatchingService.calculate_match(blank_profile, job_no_skills)
    assert breakdown.total_score == 0.0
    assert breakdown.has_sufficient_data is False
    assert len(breakdown.insufficient_data_reasons) > 0
    assert isinstance(breakdown.reasons, list)

def test_recommendation_endpoint(client, candidate_token):
    res = client.get("/api/v1/recommendations", headers={"Authorization": f"Bearer {candidate_token}"})
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "algorithm_version" in data
    assert "v2.0" in data["algorithm_version"]
    if data["items"]:
        item = data["items"][0]
        assert "match_score" in item
        assert "match_breakdown" in item
        assert "reasons" in item["match_breakdown"]
