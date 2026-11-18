import pytest
from app.models import Job, User, VisitedJob

def test_track_job_visit_authenticated(client, candidate_token, db_session):
    headers = {"Authorization": f"Bearer {candidate_token}"}
    job = db_session.query(Job).first()
    assert job is not None

    # Clean prior test state for this user/job
    user = db_session.query(User).filter(User.email == "candidate@example.com").first()
    db_session.query(VisitedJob).filter(VisitedJob.user_id == user.id, VisitedJob.job_id == job.id).delete()
    db_session.commit()

    # First visit
    res1 = client.post(f"/api/v1/jobs/{job.id}/visit", headers=headers)
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["job_id"] == job.id
    assert data1["redirect_url"] == job.application_url
    assert data1["visit_count"] == 1
    assert "not mean an application was submitted" in data1["disclaimer"]

    # Second visit (idempotent tracking / deduplication)
    res2 = client.post(f"/api/v1/jobs/{job.id}/visit", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["visit_count"] == 2

    # Clean up
    db_session.query(VisitedJob).filter(VisitedJob.user_id == user.id, VisitedJob.job_id == job.id).delete()
    db_session.commit()

def test_track_job_visit_unauthenticated_rejected(client, db_session):
    job = db_session.query(Job).first()
    assert job is not None

    res = client.post(f"/api/v1/jobs/{job.id}/visit")
    assert res.status_code == 401

def test_open_redirect_protection_and_direct_apply(client, db_session):
    job = db_session.query(Job).first()
    assert job is not None

    # Test direct apply-redirect endpoint (follows 307 temporary redirect to official employer application_url)
    res = client.get(f"/api/v1/jobs/{job.id}/apply-redirect", follow_redirects=False)
    assert res.status_code == 307
    assert res.headers["location"] == job.application_url

def test_profile_visited_jobs_list(client, candidate_token, db_session):
    headers = {"Authorization": f"Bearer {candidate_token}"}
    user = db_session.query(User).filter(User.email == "candidate@example.com").first()
    jobs = db_session.query(Job).limit(2).all()
    assert len(jobs) >= 2

    # Clean prior state
    db_session.query(VisitedJob).filter(VisitedJob.user_id == user.id).delete()
    db_session.commit()

    # Track visits to 2 distinct jobs
    client.post(f"/api/v1/jobs/{jobs[0].id}/visit", headers=headers)
    client.post(f"/api/v1/jobs/{jobs[0].id}/visit", headers=headers)  # second visit to job 0
    client.post(f"/api/v1/jobs/{jobs[1].id}/visit", headers=headers)

    # Inspect visited-jobs list
    res = client.get("/api/v1/profile/visited-jobs", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_unique_visited"] == 2
    assert data["total_clicks"] == 3
    assert len(data["items"]) == 2
    assert "not mean an application was submitted" in data["disclaimer"]

    # Verify profile summary reflects visited_jobs_count
    prof_res = client.get("/api/v1/profile", headers=headers)
    assert prof_res.status_code == 200
    assert prof_res.json()["visited_jobs_count"] == 2

    # Clean up
    db_session.query(VisitedJob).filter(VisitedJob.user_id == user.id).delete()
    db_session.commit()

def test_track_job_not_found(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}
    res = client.post("/api/v1/jobs/999999999/visit", headers=headers)
    assert res.status_code == 404
