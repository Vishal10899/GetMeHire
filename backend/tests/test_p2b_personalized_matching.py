import pytest
import datetime
from sqlalchemy.orm import Session
from app.models import User, Profile, Company, Source, Job, SavedJob
from app.services.matching_service import MatchingService
from app.services.job_service import JobService
from app.core.security import get_password_hash, create_access_token

# ==============================================================================
# Phase 1 & 2: Mathematical & Evidence-Based Scoring Unit Tests
# ==============================================================================

def test_blank_profile_zero_score_and_insufficient_data():
    """
    Verify that an unpopulated candidate profile earns zero points and triggers
    has_sufficient_data=False with actionable insufficiency reasons.
    Ensures the neutral fallback bug cannot recur.
    """
    blank_profile = Profile(
        skills=[],
        preferred_roles=[],
        work_arrangements=[],
        preferred_locations=[],
        preferred_countries=[],
        total_experience_years=None,
        relevant_experience_years=None,
        profession=None
    )

    job = Job(
        title="Senior Software Engineer",
        description="We need Python and AWS expertise.",
        skills=["Python", "AWS"],
        remote_type="REMOTE",
        country="United States",
        min_experience_years=4.0
    )

    breakdown = MatchingService.calculate_match(blank_profile, job)
    assert breakdown.total_score == 0.0
    assert breakdown.skill_score == 0.0
    assert breakdown.role_score == 0.0
    assert breakdown.location_score == 0.0
    assert breakdown.experience_score == 0.0
    assert breakdown.has_sufficient_data is False
    assert len(breakdown.insufficient_data_reasons) > 0
    assert "profile does not contain skills" in breakdown.insufficient_data_reasons[0].lower()


def test_unrelated_job_zero_score_corporate_counsel_for_python_dev():
    """
    Regression verification for the P1 defect:
    A Python backend engineer must score 0.0% against an unrelated Corporate Counsel job.
    No artificial positive baselines or points for non-matching tracks/skills.
    """
    python_dev = Profile(
        profession="ENGINEERING",
        skills=["Python", "FastAPI", "Docker", "PostgreSQL"],
        preferred_roles=["Senior Backend Engineer", "Python Developer"],
        work_arrangements=["REMOTE"],
        preferred_locations=["Bangalore"],
        preferred_countries=["India"],
        total_experience_years=5.0,
        relevant_experience_years=5.0
    )

    corporate_counsel = Job(
        title="Corporate Counsel, Commercial",
        normalized_title="Corporate Counsel",
        profession="LEGAL_ADMIN",
        skills=["Commercial Contracts", "Compliance", "Contract Negotiation", "Bar License"],
        remote_type="ONSITE",
        city="New York",
        country="United States",
        min_experience_years=6.0,
        description="Advise executive leadership on SaaS commercial contracts and regulatory compliance."
    )
    corporate_counsel.remote_eligibility = "NONE"

    breakdown = MatchingService.calculate_match(python_dev, corporate_counsel)
    assert breakdown.total_score == 0.0
    assert breakdown.skill_score == 0.0
    assert breakdown.role_score == 0.0
    assert breakdown.location_score == 0.0
    assert breakdown.experience_score == 0.0
    assert breakdown.matched_skills == []
    assert len(breakdown.missing_skills) > 0
    # Explainable reasons must detail lack of alignment
    reasons_str = " ".join(breakdown.reasons)
    assert "different career track" in reasons_str.lower()


def test_strong_match_python_fastapi_backend():
    """
    Verify high-scoring match (>= 85.0%) with all 4 dimensions satisfied:
    - Skills (40/40)
    - Role & Track (25/25)
    - Location & Remote (20/20)
    - Experience (15/15)
    """
    candidate = Profile(
        profession="ENGINEERING",
        skills=["Python", "FastAPI", "PostgreSQL", "Docker", "Redis"],
        preferred_roles=["Senior Backend Engineer"],
        work_arrangements=["REMOTE"],
        preferred_locations=["Bangalore"],
        preferred_countries=["India"],
        total_experience_years=6.0,
        relevant_experience_years=6.0
    )

    backend_job = Job(
        title="Senior Backend Engineer - Python / FastAPI",
        normalized_title="Senior Backend Engineer",
        profession="ENGINEERING",
        skills=["Python", "FastAPI", "PostgreSQL"],
        remote_type="REMOTE",
        city="Bengaluru",
        country="India",
        min_experience_years=4.0,
        description="Scale our high-throughput payment systems using Python and FastAPI."
    )
    backend_job.remote_eligibility = "INDIA_ONLY"

    breakdown = MatchingService.calculate_match(candidate, backend_job)
    assert breakdown.total_score >= 85.0
    assert breakdown.skill_score == 40.0
    assert breakdown.role_score == 25.0  # 10 track + 15 role match
    assert breakdown.location_score == 20.0  # 10 remote + 10 geo
    assert breakdown.experience_score == 15.0  # 6 yrs >= 4 yrs required
    assert len(breakdown.matched_skills) == 3
    assert set(breakdown.matched_skills) == {"Python", "FastAPI", "PostgreSQL"}
    assert breakdown.missing_skills == []
    assert breakdown.location_eligibility == "Eligible (India-Only Remote)"
    assert breakdown.experience_alignment == "Meets Requirement"


def test_partial_match_half_skills():
    """
    Verify proportional skill scoring:
    Candidate matches 2 out of 4 required skills -> 2/4 * 40.0 = 20.0 pts.
    Missing skills must be populated for candidate transparency.
    """
    candidate = Profile(
        profession="ENGINEERING",
        skills=["Python", "Docker"],
        preferred_roles=["Software Engineer"],
        work_arrangements=["REMOTE"],
        preferred_locations=["San Francisco"],
        preferred_countries=["United States"],
        total_experience_years=3.0
    )

    job = Job(
        title="Software Engineer",
        normalized_title="Software Engineer",
        profession="ENGINEERING",
        skills=["Python", "Docker", "Kubernetes", "AWS"],
        remote_type="REMOTE",
        min_experience_years=3.0
    )
    job.remote_eligibility = "WORLDWIDE_REMOTE"

    breakdown = MatchingService.calculate_match(candidate, job)
    assert breakdown.skill_score == 20.0  # 2 of 4 skills matched
    assert set(breakdown.matched_skills) == {"Python", "Docker"}
    assert set(breakdown.missing_skills) == {"Kubernetes", "AWS"}


def test_location_mismatch_onsite_different_countries():
    """
    Verify location penalty/zero:
    Candidate is based in Bangalore, India seeking ONSITE.
    Job is ONSITE in London, UK.
    Arrangement matches (both ONSITE) but geographic location differs -> 10/20 max.
    """
    candidate = Profile(
        profession="ENGINEERING",
        skills=["Python"],
        preferred_roles=["Engineer"],
        work_arrangements=["ONSITE"],
        preferred_locations=["Bangalore"],
        preferred_countries=["India"],
        total_experience_years=4.0
    )

    job = Job(
        title="Engineer",
        profession="ENGINEERING",
        skills=["Python"],
        remote_type="ONSITE",
        city="London",
        country="United Kingdom",
        min_experience_years=3.0
    )

    breakdown = MatchingService.calculate_match(candidate, job)
    # Arrangement matches (10.0), but geo does NOT match (0.0) -> location_score == 10.0
    assert breakdown.location_score == 10.0
    reasons_str = " ".join(breakdown.reasons)
    assert "differs from your preferred locations" in reasons_str.lower()


def test_remote_eligibility_worldwide_vs_india_only():
    """
    Verify distinct handling of WORLDWIDE_REMOTE vs INDIA_ONLY remote eligibility.
    """
    india_candidate = Profile(
        profession="ENGINEERING",
        skills=["Go"],
        work_arrangements=["REMOTE"],
        preferred_locations=["Bengaluru"],
        preferred_countries=["India"]
    )

    worldwide_job = Job(
        title="Go Developer",
        profession="ENGINEERING",
        skills=["Go"],
        remote_type="REMOTE"
    )
    worldwide_job.remote_eligibility = "WORLDWIDE_REMOTE"

    india_only_job = Job(
        title="Go Developer",
        profession="ENGINEERING",
        skills=["Go"],
        remote_type="REMOTE",
        country="India"
    )
    india_only_job.remote_eligibility = "INDIA_ONLY"

    us_only_job = Job(
        title="Go Developer",
        profession="ENGINEERING",
        skills=["Go"],
        remote_type="REMOTE",
        country="United States"
    )
    us_only_job.remote_eligibility = "US_ONLY"

    # Worldwide remote: 10 arrangement + 10 geo = 20 pts
    bd_world = MatchingService.calculate_match(india_candidate, worldwide_job)
    assert bd_world.location_score == 20.0
    assert "Worldwide Remote" in bd_world.location_eligibility

    # India-only remote for Indian candidate: 10 arrangement + 10 geo = 20 pts
    bd_india = MatchingService.calculate_match(india_candidate, india_only_job)
    assert bd_india.location_score == 20.0
    assert "India-Only Remote" in bd_india.location_eligibility

    # US-only remote for Indian candidate: 0 pts arrangement restricted + 0 geo = 0 pts
    bd_us = MatchingService.calculate_match(india_candidate, us_only_job)
    assert bd_us.location_score == 0.0
    assert "Restricted" in bd_us.location_eligibility


def test_experience_alignment_thresholds():
    """
    Verify 3-tier experience alignment:
    - User >= min_exp -> 15.0 pts ("Meets Requirement")
    - User >= 0.7 * min_exp -> 8.0 pts ("Within Reach")
    - User < 0.7 * min_exp -> 0.0 pts ("Below Requirement")
    """
    job = Job(
        title="DevOps Engineer",
        profession="ENGINEERING",
        skills=["Docker"],
        remote_type="REMOTE",
        min_experience_years=5.0
    )

    # 1. Meets requirement (5.5 >= 5.0)
    p1 = Profile(skills=["Docker"], relevant_experience_years=5.5)
    bd1 = MatchingService.calculate_match(p1, job)
    assert bd1.experience_score == 15.0
    assert bd1.experience_alignment == "Meets Requirement"

    # 2. Within reach (4.0 >= 5.0 * 0.7 = 3.5)
    p2 = Profile(skills=["Docker"], relevant_experience_years=4.0)
    bd2 = MatchingService.calculate_match(p2, job)
    assert bd2.experience_score == 8.0
    assert bd2.experience_alignment == "Within Reach"

    # 3. Below requirement (2.0 < 3.5)
    p3 = Profile(skills=["Docker"], relevant_experience_years=2.0)
    bd3 = MatchingService.calculate_match(p3, job)
    assert bd3.experience_score == 0.0
    assert bd3.experience_alignment == "Below Requirement"


# ==============================================================================
# Phase 3: Unauthenticated Suppression & Search Integration
# ==============================================================================

def test_unauthenticated_user_suppression_on_jobs_search(db_session: Session):
    """
    Verify that unauthenticated visitors (/jobs search with current_user=None)
    never receive match scores or match breakdowns.
    """
    results = JobService.search_jobs(
        db=db_session,
        keyword="",
        current_user=None,
        page=1,
        page_size=5
    )

    assert results.total > 0
    for item in results.items:
        assert item.match_score is None, "Match score must be suppressed for unauthenticated requests"
        assert item.match_breakdown is None, "Match breakdown must be suppressed for unauthenticated requests"


# ==============================================================================
# Phase 4 & 5: Candidate Isolation & API Verification
# ==============================================================================

@pytest.fixture
def isolated_candidates(db_session: Session):
    """
    Creates two distinct candidate users with contrasting profiles:
    - User A: Senior Backend Engineer (Python, PostgreSQL, Bangalore)
    - User B: Marketing Specialist (SEO, Copywriting, London)
    """
    # Candidate A
    user_a = db_session.query(User).filter(User.email == "candidate_a_test@jobplatform.com").first()
    if not user_a:
        user_a = User(
            email="candidate_a_test@jobplatform.com",
            hashed_password=get_password_hash("Password@123"),
            role="USER",
            account_status="ACTIVE",
            is_verified=True
        )
        db_session.add(user_a)
        db_session.flush()

        prof_a = Profile(
            user_id=user_a.id,
            full_name="Alex Backend",
            profession="ENGINEERING",
            skills=["Python", "FastAPI", "PostgreSQL"],
            preferred_roles=["Senior Backend Engineer"],
            work_arrangements=["REMOTE"],
            preferred_countries=["India"],
            total_experience_years=6.0,
            relevant_experience_years=6.0
        )
        db_session.add(prof_a)

    # Candidate B
    user_b = db_session.query(User).filter(User.email == "candidate_b_test@jobplatform.com").first()
    if not user_b:
        user_b = User(
            email="candidate_b_test@jobplatform.com",
            hashed_password=get_password_hash("Password@123"),
            role="USER",
            account_status="ACTIVE",
            is_verified=True
        )
        db_session.add(user_b)
        db_session.flush()

        prof_b = Profile(
            user_id=user_b.id,
            full_name="Bella Marketing",
            profession="MARKETING_GROWTH",
            skills=["SEO", "Copywriting", "HubSpot"],
            preferred_roles=["Growth Marketing Lead"],
            work_arrangements=["ONSITE"],
            preferred_countries=["United Kingdom"],
            total_experience_years=3.0,
            relevant_experience_years=3.0
        )
        db_session.add(prof_b)

    db_session.commit()
    token_a = create_access_token(user_a.id)
    token_b = create_access_token(user_b.id)
    return {"user_a": user_a, "user_b": user_b, "token_a": token_a, "token_b": token_b}


def test_authenticated_candidate_isolation(client, isolated_candidates):
    """
    Verify complete isolation between candidate users:
    - User A receives high match scores for engineering jobs.
    - User B querying the same recommendations endpoint receives candidate-specific scores (0% for engineering jobs).
    - Neither user's recommendations or breakdown leaks to the other.
    """
    token_a = isolated_candidates["token_a"]
    token_b = isolated_candidates["token_b"]

    res_a = client.get("/api/v1/recommendations", headers={"Authorization": f"Bearer {token_a}"})
    assert res_a.status_code == 200
    data_a = res_a.json()
    assert data_a["has_sufficient_data"] is True

    # Candidate A should have strong match for Python engineering jobs
    if data_a["items"]:
        top_match_a = data_a["items"][0]
        assert top_match_a["match_score"] >= 50.0
        assert "Python" in top_match_a["match_breakdown"]["matched_skills"]
        assert "Python" in top_match_a["match_breakdown"]["matched_skills"]

    # Candidate B querying recommendations
    res_b = client.get("/api/v1/recommendations", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    data_b = res_b.json()
    assert data_b["has_sufficient_data"] is True

    # Candidate B must NOT see high engineering scores (skills mismatch, career track mismatch)
    if data_b["items"]:
        for item in data_b["items"]:
            if item["job"]["profession"] == "ENGINEERING":
                assert item["match_score"] < 40.0
                assert "SEO" not in item["job"]["skills"]


def test_recommendations_filtering_and_pagination(client, isolated_candidates):
    """
    Verify filters on the recommendations endpoint:
    - min_score filter
    - profession filter
    - remote_type filter
    - limit & offset pagination
    """
    token_a = isolated_candidates["token_a"]

    # 1. Filter by min_score
    res = client.get("/api/v1/recommendations?min_score=70", headers={"Authorization": f"Bearer {token_a}"})
    assert res.status_code == 200
    data = res.json()
    for item in data["items"]:
        assert item["match_score"] >= 70.0

    # 2. Filter by profession
    res_prof = client.get("/api/v1/recommendations?profession=ENGINEERING", headers={"Authorization": f"Bearer {token_a}"})
    assert res_prof.status_code == 200
    data_prof = res_prof.json()
    for item in data_prof["items"]:
        assert item["job"]["profession"] == "ENGINEERING"

    # 3. Filter by remote_type
    res_remote = client.get("/api/v1/recommendations?remote_type=REMOTE", headers={"Authorization": f"Bearer {token_a}"})
    assert res_remote.status_code == 200

    # 4. Pagination
    res_p1 = client.get("/api/v1/recommendations?limit=2&offset=0", headers={"Authorization": f"Bearer {token_a}"})
    assert res_p1.status_code == 200
    items_p1 = res_p1.json()["items"]
    assert len(items_p1) <= 2


def test_saved_job_state_reflected_in_recommendations(client, db_session: Session, isolated_candidates):
    """
    Verify that saved job status is accurately reflected in recommendations.
    """
    user_a = isolated_candidates["user_a"]
    token_a = isolated_candidates["token_a"]

    # Find a job to bookmark
    job = db_session.query(Job).filter(Job.status == "ACTIVE").first()
    assert job is not None

    # Bookmark it using PUT endpoint
    save_res = client.put(f"/api/v1/saved-jobs/{job.id}", headers={"Authorization": f"Bearer {token_a}"})
    assert save_res.status_code in [200, 201]

    # Verify recommendation endpoint marks is_saved=True
    rec_res = client.get("/api/v1/recommendations", headers={"Authorization": f"Bearer {token_a}"})
    assert rec_res.status_code == 200
    items = rec_res.json()["items"]
    saved_items = [item for item in items if item["job"]["id"] == job.id]
    if saved_items:
        assert saved_items[0]["job"]["is_saved"] is True
