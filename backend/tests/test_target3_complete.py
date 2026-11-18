import datetime
import uuid
import pytest
from app.models import User, Job, Company, Source, JobActivity, VisitedJob
from app.services.job_activity_service import JobActivityService
from app.services.url_verifier import UrlVerifierService
from app.core.security import get_password_hash, create_access_token

@pytest.fixture
def test_setup(db_session):
    """Seed test company, source and baseline jobs for Target 3 verification."""
    company = db_session.query(Company).filter(Company.canonical_name == "Acme Corporation").first()
    if not company:
        company = Company(canonical_name="Acme Corporation", website="https://acme.example.com")
        db_session.add(company)
        db_session.flush()

    source = db_session.query(Source).filter(Source.source_name == "Greenhouse Direct").first()
    if not source:
        source = Source(company_id=company.id, source_name="Greenhouse Direct", source_type="ATS", canonical_source_url="https://boards.greenhouse.io")
        db_session.add(source)
        db_session.flush()

    # Active job with verified URL
    active_job = db_session.query(Job).filter(Job.title == "Target 3 Active Engineer").first()
    if not active_job:
        active_job = Job(
            external_job_id="t3-act-1",
            content_fingerprint="fp-t3-act-1",
            title="Target 3 Active Engineer",
            normalized_title="Target 3 Active Engineer",
            company_id=company.id,
            source_id=source.id,
            application_url="https://boards.greenhouse.io/acme/jobs/40112233",
            description="Engineering position for Target 3 verification.",
            location="San Francisco, CA",
            remote_type="REMOTE",
            status="ACTIVE",
            first_seen_at=datetime.datetime.now(datetime.timezone.utc),
            last_seen_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db_session.add(active_job)
        db_session.flush()

    # Closed job
    closed_job = db_session.query(Job).filter(Job.title == "Target 3 Closed Position").first()
    if not closed_job:
        closed_job = Job(
            external_job_id="t3-cls-1",
            content_fingerprint="fp-t3-cls-1",
            title="Target 3 Closed Position",
            normalized_title="Target 3 Closed Position",
            company_id=company.id,
            source_id=source.id,
            application_url="https://boards.greenhouse.io/acme/jobs/closed99",
            description="Closed vacancy.",
            location="Remote",
            remote_type="REMOTE",
            status="CLOSED",
            first_seen_at=datetime.datetime.now(datetime.timezone.utc),
            last_seen_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db_session.add(closed_job)
        db_session.flush()

    # Secondary test user for cross-user isolation tests
    user_b = db_session.query(User).filter(User.email == "user_b@example.com").first()
    if not user_b:
        user_b = User(
            email="user_b@example.com",
            hashed_password=get_password_hash("UserB@123456"),
            role="USER",
            account_status="ACTIVE",
            is_verified=True
        )
        db_session.add(user_b)
        db_session.flush()

    db_session.commit()
    user_b_token = create_access_token(user_b.id)

    return {
        "company": company,
        "source": source,
        "active_job": active_job,
        "closed_job": closed_job,
        "user_b": user_b,
        "user_b_token": user_b_token,
    }


def test_1_valid_original_application_url(client, candidate_token, test_setup):
    """Test 1: Valid original employer application URL returns successfully with truthful metadata."""
    headers = {"Authorization": f"Bearer {candidate_token}"}
    job = test_setup["active_job"]

    res = client.post(f"/api/v1/jobs/{job.id}/apply", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["job_id"] == job.id
    assert data["application_url"] == job.application_url
    assert data["redirect_result"] == "SUCCESS"
    assert data["is_safe"] is True
    assert data["company_name"] == "Acme Corporation"
    assert "submits applications" in data["disclaimer"].lower()


def test_2_missing_application_url_handling(client, candidate_token, db_session, test_setup):
    """Test 2: Job with missing/empty application URL is rejected with HTTP 400."""
    headers = {"Authorization": f"Bearer {candidate_token}"}
    uid = uuid.uuid4().hex[:8]
    empty_url_job = Job(
        external_job_id=f"t3-nourl-{uid}",
        content_fingerprint=f"fp-t3-nourl-{uid}",
        title="Job With No URL",
        company_id=test_setup["company"].id,
        source_id=test_setup["source"].id,
        application_url="",
        description="No URL job",
        location="Remote",
        status="ACTIVE",
        first_seen_at=datetime.datetime.now(datetime.timezone.utc),
        last_seen_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(empty_url_job)
    db_session.commit()

    res = client.post(f"/api/v1/jobs/{empty_url_job.id}/apply", headers=headers)
    assert res.status_code == 400
    assert "no application url configured" in res.json()["detail"].lower()


def test_3_invalid_url_scheme_handling(client, candidate_token, db_session, test_setup):
    """Test 3: Non-HTTP/HTTPS schemes (javascript:, file:, data:) rejected with HTTP 400."""
    headers = {"Authorization": f"Bearer {candidate_token}"}
    bad_schemes = [
        "javascript:alert(document.cookie)",
        "file:///etc/passwd",
        "data:text/html,<script>window.location='https://attacker.com'</script>",
    ]

    uid = uuid.uuid4().hex[:8]
    for idx, bad_url in enumerate(bad_schemes):
        bad_job = Job(
            external_job_id=f"t3-bad-{uid}-{idx}",
            content_fingerprint=f"fp-t3-bad-{uid}-{idx}",
            title="Bad Scheme Job",
            company_id=test_setup["company"].id,
            source_id=test_setup["source"].id,
            application_url=bad_url,
            description="Scheme injection test",
            location="Remote",
            status="ACTIVE",
            first_seen_at=datetime.datetime.now(datetime.timezone.utc),
            last_seen_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db_session.add(bad_job)
        db_session.commit()

        res = client.post(f"/api/v1/jobs/{bad_job.id}/apply", headers=headers)
        assert res.status_code == 400
        assert "invalid or disallowed application url destination" in res.json()["detail"].lower()


def test_4_open_redirect_and_ssrf_prevention(client, candidate_token, db_session, test_setup):
    """Test 4: SSRF targets (localhost, 127.0.0.1, AWS metadata 169.254.169.254, RFC1918) blocked with HTTP 400."""
    headers = {"Authorization": f"Bearer {candidate_token}"}
    ssrf_urls = [
        "http://localhost:8000/api/v1/admin",
        "http://127.0.0.1:5432/db",
        "http://169.254.169.254/latest/meta-data/",
        "http://10.0.0.1/internal-dashboard",
        "http://192.168.1.1/router",
        "http://172.16.0.1/private",
    ]

    uid = uuid.uuid4().hex[:8]
    for idx, ssrf_url in enumerate(ssrf_urls):
        assert UrlVerifierService.is_safe_url(ssrf_url) is False

        ssrf_job = Job(
            external_job_id=f"t3-ssrf-{uid}-{idx}",
            content_fingerprint=f"fp-t3-ssrf-{uid}-{idx}",
            title="SSRF Attempt Job",
            company_id=test_setup["company"].id,
            source_id=test_setup["source"].id,
            application_url=ssrf_url,
            description="SSRF test",
            location="Remote",
            status="ACTIVE",
            first_seen_at=datetime.datetime.now(datetime.timezone.utc),
            last_seen_at=datetime.datetime.now(datetime.timezone.utc)
        )
        db_session.add(ssrf_job)
        db_session.commit()

        res = client.post(f"/api/v1/jobs/{ssrf_job.id}/apply", headers=headers)
        assert res.status_code == 400
        assert "disallowed" in res.json()["detail"].lower() or "invalid" in res.json()["detail"].lower()


def test_5_successful_apply_click_tracking(client, candidate_token, db_session, test_setup):
    """Test 5: Outbound Apply Now click recorded in JobActivity and updates VisitedJob."""
    headers = {"Authorization": f"Bearer {candidate_token}"}
    job = test_setup["active_job"]
    user = db_session.query(User).filter(User.email == "candidate@example.com").first()

    # Pre-clean
    db_session.query(JobActivity).filter(JobActivity.user_id == user.id, JobActivity.job_id == job.id).delete()
    db_session.query(VisitedJob).filter(VisitedJob.user_id == user.id, VisitedJob.job_id == job.id).delete()
    db_session.commit()

    res = client.post(f"/api/v1/jobs/{job.id}/apply", headers=headers)
    assert res.status_code == 200

    activity = db_session.query(JobActivity).filter(
        JobActivity.user_id == user.id,
        JobActivity.job_id == job.id,
        JobActivity.activity_type == "APPLY_CLICK"
    ).first()
    assert activity is not None
    assert activity.redirect_result == "SUCCESS"
    assert activity.company_name == "Acme Corporation"

    visited = db_session.query(VisitedJob).filter(
        VisitedJob.user_id == user.id,
        VisitedJob.job_id == job.id
    ).first()
    assert visited is not None
    assert visited.visit_count == 1


def test_6_job_view_vs_apply_click_distinction(client, candidate_token, db_session, test_setup):
    """Test 6: Strict distinction between VIEW and APPLY_CLICK activities."""
    headers = {"Authorization": f"Bearer {candidate_token}"}
    job = test_setup["active_job"]
    user = db_session.query(User).filter(User.email == "candidate@example.com").first()

    # Pre-clean
    db_session.query(JobActivity).filter(JobActivity.user_id == user.id, JobActivity.job_id == job.id).delete()
    db_session.commit()

    # 1. Record View
    view_res = client.post(f"/api/v1/jobs/{job.id}/view", headers=headers)
    assert view_res.status_code == 200
    assert view_res.json()["activity_type"] == "VIEW"

    # 2. Record Apply Click
    apply_res = client.post(f"/api/v1/jobs/{job.id}/apply", headers=headers)
    assert apply_res.status_code == 200

    # Query filtered timeline for views
    views_res = client.get("/api/v1/profile/activity?activity_type=VIEW", headers=headers)
    assert views_res.status_code == 200
    views_data = views_res.json()
    assert any(item["job_id"] == job.id and item["activity_type"] == "VIEW" for item in views_data["items"])
    assert all(item["activity_type"] == "VIEW" for item in views_data["items"])

    # Query filtered timeline for apply clicks
    applies_res = client.get("/api/v1/profile/activity?activity_type=APPLY_CLICK", headers=headers)
    assert applies_res.status_code == 200
    applies_data = applies_res.json()
    assert any(item["job_id"] == job.id and item["activity_type"] == "APPLY_CLICK" for item in applies_data["items"])
    assert all(item["activity_type"] == "APPLY_CLICK" for item in applies_data["items"])


def test_7_view_debouncing_and_click_tracking(client, candidate_token, db_session, test_setup):
    """Test 7: Rapid repeated views are debounced within 2-minute window; apply clicks record each intent."""
    headers = {"Authorization": f"Bearer {candidate_token}"}
    job = test_setup["active_job"]

    # First view: recorded
    res1 = client.post(f"/api/v1/jobs/{job.id}/view", headers=headers)
    assert res1.status_code == 200

    # Second view within seconds: debounced
    res2 = client.post(f"/api/v1/jobs/{job.id}/view", headers=headers)
    assert res2.status_code == 200
    assert "already recorded within debounce window" in res2.json()["message"].lower()

    # Repeated apply clicks: both logged
    res_apply1 = client.post(f"/api/v1/jobs/{job.id}/apply", headers=headers)
    res_apply2 = client.post(f"/api/v1/jobs/{job.id}/apply", headers=headers)
    assert res_apply1.status_code == 200
    assert res_apply2.status_code == 200


def test_8_closed_job_handling(client, candidate_token, db_session, test_setup):
    """Test 8: Closed jobs return HTTP 410 Gone unless allow_closed=True is explicitly passed."""
    headers = {"Authorization": f"Bearer {candidate_token}"}
    closed_job = test_setup["closed_job"]

    # Default apply click returns 410 GONE
    res_default = client.post(f"/api/v1/jobs/{closed_job.id}/apply", headers=headers)
    assert res_default.status_code == 410
    assert "closed" in res_default.json()["detail"].lower()

    # With allow_closed=True via query param or body
    res_allowed = client.post(f"/api/v1/jobs/{closed_job.id}/apply?allow_closed=true", headers=headers)
    assert res_allowed.status_code == 200
    data = res_allowed.json()
    assert data["redirect_result"] == "SUCCESS"
    assert data["application_url"] == closed_job.application_url
    assert data["status"] == "CLOSED"


def test_9_link_status_determination(db_session, test_setup):
    """Test 9: JobActivityService.determine_link_status produces truthful statuses."""
    active_job = test_setup["active_job"]
    closed_job = test_setup["closed_job"]

    status_active, is_safe = JobActivityService.determine_link_status(active_job)
    assert is_safe is True
    assert status_active in ("VERIFIED_ACCESSIBLE", "UNVERIFIED")

    status_closed, is_safe_closed = JobActivityService.determine_link_status(closed_job)
    assert status_closed == "CLOSED"
    assert is_safe_closed is True

    # Empty URL
    empty_job = Job(external_job_id="ext-e", title="E", application_url="")
    status_empty, is_safe_empty = JobActivityService.determine_link_status(empty_job)
    assert status_empty == "UNAVAILABLE"
    assert is_safe_empty is False

    # SSRF URL
    bad_job = Job(external_job_id="ext-b", title="B", application_url="http://127.0.0.1:8000/steal")
    status_bad, is_safe_bad = JobActivityService.determine_link_status(bad_job)
    assert status_bad == "INACCESSIBLE"
    assert is_safe_bad is False


def test_10_direct_apply_redirect_http_307(client, candidate_token, test_setup):
    """Test 10: GET /jobs/{id}/apply-redirect issues HTTP 307 temporary redirect to genuine employer page."""
    headers = {"Authorization": f"Bearer {candidate_token}"}
    job = test_setup["active_job"]

    res = client.get(f"/api/v1/jobs/{job.id}/apply-redirect", headers=headers, follow_redirects=False)
    assert res.status_code == 307
    assert res.headers["location"] == job.application_url


def test_11_authenticated_candidate_activity_tracking(client, candidate_token, test_setup):
    """Test 11: Authenticated candidate activity is properly recorded and retrievable via /profile/activity."""
    headers = {"Authorization": f"Bearer {candidate_token}"}
    job = test_setup["active_job"]

    client.post(f"/api/v1/jobs/{job.id}/apply", headers=headers)

    res = client.get("/api/v1/profile/activity", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total_count" in data
    assert "disclaimer" in data
    assert len(data["items"]) >= 1

    first_item = data["items"][0]
    assert "job_title" in first_item
    assert "company_name" in first_item
    assert "activity_type" in first_item
    assert "status" in first_item


def test_12_anonymous_activity_handling(client, test_setup):
    """Test 12: Anonymous candidates can apply and view without 401 Unauthorized or crashes."""
    job = test_setup["active_job"]

    # Anonymous Apply
    res_apply = client.post(f"/api/v1/jobs/{job.id}/apply")
    assert res_apply.status_code == 200
    assert res_apply.json()["application_url"] == job.application_url

    # Anonymous View
    res_view = client.post(f"/api/v1/jobs/{job.id}/view")
    assert res_view.status_code == 200

    # Anonymous Redirect
    res_redir = client.get(f"/api/v1/jobs/{job.id}/apply-redirect", follow_redirects=False)
    assert res_redir.status_code == 307
    assert res_redir.headers["location"] == job.application_url


def test_13_cross_user_data_isolation(client, candidate_token, test_setup, db_session):
    """Test 13: Multi-tenant candidate data isolation. User B cannot see User A's activity."""
    headers_a = {"Authorization": f"Bearer {candidate_token}"}
    headers_b = {"Authorization": f"Bearer {test_setup['user_b_token']}"}

    job = test_setup["active_job"]

    # User A records an apply click
    client.post(f"/api/v1/jobs/{job.id}/apply", headers=headers_a)

    # User B queries activity
    res_b = client.get("/api/v1/profile/activity", headers=headers_b)
    assert res_b.status_code == 200
    b_items = res_b.json()["items"]

    # Verify that all returned items belong exclusively to User B
    user_b = test_setup["user_b"]
    user_a = db_session.query(User).filter(User.email == "candidate@example.com").first()

    for item in b_items:
        activity_record = db_session.query(JobActivity).filter(JobActivity.id == item["id"]).first()
        assert activity_record.user_id == user_b.id
        assert activity_record.user_id != user_a.id


def test_14_dashboard_activity_summary_totals(client, candidate_token, test_setup):
    """Test 14: GET /profile/activity/summary returns accurate aggregate counts and recent items."""
    headers = {"Authorization": f"Bearer {candidate_token}"}
    job = test_setup["active_job"]

    # Ensure at least one view and one apply
    client.post(f"/api/v1/jobs/{job.id}/view", headers=headers)
    client.post(f"/api/v1/jobs/{job.id}/apply", headers=headers)

    res = client.get("/api/v1/profile/activity/summary", headers=headers)
    assert res.status_code == 200
    summary = res.json()

    assert "total_views" in summary
    assert "total_apply_clicks" in summary
    assert "unique_companies_explored" in summary
    assert "saved_jobs_count" in summary
    assert "recent_views" in summary
    assert "recent_apply_clicks" in summary
    assert "disclaimer" in summary

    assert summary["total_views"] >= 1
    assert summary["total_apply_clicks"] >= 1
    assert summary["unique_companies_explored"] >= 1
    assert len(summary["recent_views"]) <= 5
    assert len(summary["recent_apply_clicks"]) <= 5


def test_15_historical_activity_preserved_for_closed_jobs(client, candidate_token, db_session, test_setup):
    """Test 15: Prior activity records persist accurately even after a vacancy transitions to CLOSED."""
    headers = {"Authorization": f"Bearer {candidate_token}"}
    uid = uuid.uuid4().hex[:8]
    temp_job = Job(
        external_job_id=f"t3-dyn-{uid}",
        content_fingerprint=f"fp-t3-dyn-{uid}",
        title="Dynamic Transition Vacancy",
        company_id=test_setup["company"].id,
        source_id=test_setup["source"].id,
        application_url="https://boards.greenhouse.io/acme/dynamic-vac",
        description="Transitions from active to closed",
        location="Remote",
        status="ACTIVE",
        first_seen_at=datetime.datetime.now(datetime.timezone.utc),
        last_seen_at=datetime.datetime.now(datetime.timezone.utc)
    )
    db_session.add(temp_job)
    db_session.commit()

    # Candidate views and applies while ACTIVE
    client.post(f"/api/v1/jobs/{temp_job.id}/apply", headers=headers)

    # Vacancy closes in database
    temp_job.status = "CLOSED"
    db_session.commit()

    # Timeline check
    res = client.get("/api/v1/profile/activity", headers=headers)
    assert res.status_code == 200
    items = res.json()["items"]

    matching_item = next((item for item in items if item["job_id"] == temp_job.id), None)
    assert matching_item is not None
    assert matching_item["job_title"] == "Dynamic Transition Vacancy"
    assert matching_item["status"] == "CLOSED"


def test_16_regression_target1_and_target2_intact(client, candidate_token):
    """Test 16: Ensure Target 1 discovery and Target 2 profile/recommendation endpoints remain 100% functional."""
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # Target 1: Discovery search
    res_jobs = client.get("/api/v1/jobs?limit=5")
    assert res_jobs.status_code == 200
    assert "items" in res_jobs.json()

    # Target 1: Search categories
    res_categories = client.get("/api/v1/jobs/categories")
    assert res_categories.status_code == 200

    # Target 2: Candidate Profile
    res_profile = client.get("/api/v1/profile", headers=headers)
    assert res_profile.status_code == 200
    assert "full_name" in res_profile.json()

    # Target 2: Recommendations
    res_recs = client.get("/api/v1/recommendations?limit=5", headers=headers)
    assert res_recs.status_code == 200
    assert "items" in res_recs.json()

    # Target 2: Resume Studio Entitlements
    res_entitlements = client.get("/api/v1/resume-studio/entitlements", headers=headers)
    assert res_entitlements.status_code == 200
    assert isinstance(res_entitlements.json(), list)
