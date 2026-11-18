import io
import uuid
import pytest
from app.core.rate_limiter import auth_rate_limiter
from app.services.alert_service import AlertService

def test_database_health_probe(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["database"] == "CONNECTED"

def test_rate_limiting_on_auth_endpoint(client):
    # Fire requests to test rate limit
    got_429 = False
    for i in range(25):
        res = client.post("/api/v1/auth/login", json={
            "email": "test_ratelimit@example.com",
            "password": "wrong"
        })
        if res.status_code == 429:
            got_429 = True
            assert "Retry-After" in res.headers
            break
    assert got_429, "Rate limiter should have triggered HTTP 429 after rapid authentication attempts"
    # Reset limiter so subsequent test requests from testclient are not throttled
    auth_rate_limiter.requests.clear()

def test_resume_magic_byte_validation(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}
    
    # Fake PDF file with malicious/invalid content
    fake_pdf = io.BytesIO(b"NOT A REAL PDF FILE HEADER JUST TEXT")
    files = {"file": ("malicious.pdf", fake_pdf, "application/pdf")}
    
    res = client.post("/api/v1/profile/resume", headers=headers, files=files)
    assert res.status_code == 400
    assert "Invalid PDF" in res.json()["detail"]

def test_valid_pdf_magic_byte_accepted(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}
    
    valid_pdf = io.BytesIO(b"%PDF-1.5 %Sample Valid PDF Content")
    files = {"file": ("valid_resume.pdf", valid_pdf, "application/pdf")}
    
    res = client.post("/api/v1/profile/resume", headers=headers, files=files)
    assert res.status_code == 200
    assert res.json()["filename"] == "valid_resume.pdf"

# ---------------------------------------------------------------------------
# F-01: Admin Authorization Verification
# ---------------------------------------------------------------------------

def test_admin_endpoints_reject_unauthenticated_requests(client):
    endpoints = [
        ("GET", "/api/v1/admin/sources"),
        ("POST", "/api/v1/admin/sources"),
        ("PATCH", "/api/v1/admin/sources/1"),
        ("POST", "/api/v1/admin/sources/1/sync"),
        ("GET", "/api/v1/admin/ingestion-runs"),
        ("GET", "/api/v1/admin/health"),
    ]
    for method, path in endpoints:
        res = client.request(method, path)
        assert res.status_code == 401, f"{method} {path} should reject unauthenticated requests with 401"
        assert "Authentication credentials were not provided" in res.json()["detail"]

def test_admin_endpoints_reject_non_admin_users(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}
    endpoints = [
        ("GET", "/api/v1/admin/sources"),
        ("POST", "/api/v1/admin/sources"),
        ("PATCH", "/api/v1/admin/sources/1"),
        ("POST", "/api/v1/admin/sources/1/sync"),
        ("GET", "/api/v1/admin/ingestion-runs"),
        ("GET", "/api/v1/admin/health"),
    ]
    for method, path in endpoints:
        res = client.request(method, path, headers=headers)
        assert res.status_code == 403, f"{method} {path} should reject candidate users with 403"
        assert "Administrative privileges required" in res.json()["detail"]

def test_admin_endpoints_permit_authorized_admin(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}
    res_sources = client.get("/api/v1/admin/sources", headers=headers)
    assert res_sources.status_code == 200
    assert isinstance(res_sources.json(), list)

    res_health = client.get("/api/v1/admin/health", headers=headers)
    assert res_health.status_code == 200
    assert res_health.json()["database_connected"] is True

    res_runs = client.get("/api/v1/admin/ingestion-runs", headers=headers)
    assert res_runs.status_code == 200
    assert isinstance(res_runs.json(), list)

# ---------------------------------------------------------------------------
# F-02: Alert Ownership & Multi-Tenant Isolation Verification
# ---------------------------------------------------------------------------

def test_alert_multi_tenant_isolation_and_ownership(client, candidate_token, db_session):
    headers_a = {"Authorization": f"Bearer {candidate_token}"}

    # 1. Candidate A creates an alert
    alert_payload = {
        "title": f"DevOps Alert {uuid.uuid4().hex[:6]}",
        "criteria": {"keywords": "DevOps", "remote_only": True},
        "frequency": "DAILY"
    }
    create_res = client.post("/api/v1/alerts", headers=headers_a, json=alert_payload)
    assert create_res.status_code == 201
    alert_a = create_res.json()
    alert_a_id = alert_a["id"]

    # 2. Register Candidate B
    email_b = f"candidate_b_{uuid.uuid4().hex[:8]}@example.com"
    reg_b = client.post("/api/v1/auth/register", json={
        "email": email_b,
        "password": "Password@123456"
    })
    assert reg_b.status_code == 201

    login_b = client.post("/api/v1/auth/login", json={
        "email": email_b,
        "password": "Password@123456"
    })
    assert login_b.status_code == 200
    token_b = login_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Candidate B cannot see Candidate A's alert in their list
    list_b = client.get("/api/v1/alerts", headers=headers_b)
    assert list_b.status_code == 200
    b_alert_ids = [a["id"] for a in list_b.json()]
    assert alert_a_id not in b_alert_ids, "Candidate B must not see Candidate A's private alert"

    # 4. Candidate B cannot modify Candidate A's alert (IDOR check)
    patch_b = client.patch(f"/api/v1/alerts/{alert_a_id}", headers=headers_b, json={"title": "Unauthorized Title"})
    assert patch_b.status_code == 404

    # 5. Candidate B cannot delete Candidate A's alert (IDOR check)
    del_b = client.delete(f"/api/v1/alerts/{alert_a_id}", headers=headers_b)
    assert del_b.status_code == 404

    # 6. Candidate B cannot trigger evaluation of Candidate A's alert
    eval_b = client.post(f"/api/v1/alerts/{alert_a_id}/evaluate", headers=headers_b)
    assert eval_b.status_code == 404

    # 7. Candidate A can evaluate their own alert
    eval_a = client.post(f"/api/v1/alerts/{alert_a_id}/evaluate", headers=headers_a)
    assert eval_a.status_code == 200
    assert "delivered" in eval_a.json()

    # 8. Legitimate background worker evaluation succeeds without user session
    worker_delivered = AlertService.evaluate_alert_for_new_jobs(db_session, alert_id=alert_a_id, user=None)
    assert isinstance(worker_delivered, int)

# ---------------------------------------------------------------------------
# F-03: CORS Configuration & Origin Validation Verification
# ---------------------------------------------------------------------------

def test_cors_preflight_allowed_origins(client):
    allowed_origins = ["http://localhost:3000", "http://127.0.0.1:3000"]
    for origin in allowed_origins:
        res = client.options("/api/v1/jobs", headers={
            "Origin": origin,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "Authorization,Content-Type"
        })
        assert res.status_code == 200
        assert res.headers.get("access-control-allow-origin") == origin
        assert res.headers.get("access-control-allow-credentials") == "true"

def test_cors_preflight_jobs_endpoints_with_pna_and_ports(client):
    """
    Regression test verifying preflight OPTIONS requests for:
    - /api/v1/jobs?sort_by=newest&page=1&page_size=15
    - /api/v1/jobs/professions
    - /api/v1/jobs?keyword=data&sort_by=newest&page=1&page_size=15
    Ensure that W3C Private Network Access (PNA) headers and loopback origins (localhost:3000,
    127.0.0.1:3000, localhost:3001, [::1]:3000) are accepted with HTTP 200 and proper CORS headers.
    """
    endpoints = [
        "/api/v1/jobs?sort_by=newest&page=1&page_size=15",
        "/api/v1/jobs/professions",
        "/api/v1/jobs?keyword=data&sort_by=newest&page=1&page_size=15"
    ]
    origins = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://[::1]:3000"
    ]
    for endpoint in endpoints:
        for origin in origins:
            res = client.options(endpoint, headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "Content-Type,Authorization",
                "Access-Control-Request-Private-Network": "true"
            })
            assert res.status_code == 200, f"Failed preflight for {endpoint} from {origin}: {res.text}"
            assert res.headers.get("access-control-allow-origin") == origin
            assert res.headers.get("access-control-allow-credentials") == "true"
            assert res.headers.get("access-control-allow-private-network") == "true"

def test_cors_disallowed_origin_rejected(client):
    disallowed_origin = "http://unauthorized-malicious-site.com"
    # Preflight request
    res = client.options("/api/v1/jobs", headers={
        "Origin": disallowed_origin,
        "Access-Control-Request-Method": "GET"
    })
    # Untrusted origin must never be returned in access-control-allow-origin and returns 400
    assert res.status_code == 400
    assert "Disallowed CORS origin" in res.text
    assert res.headers.get("access-control-allow-origin") != disallowed_origin
    assert res.headers.get("access-control-allow-origin") != "*"

    # Actual GET request
    get_res = client.get("/api/v1/jobs", headers={"Origin": disallowed_origin})
    assert get_res.headers.get("access-control-allow-origin") is None

def test_jobs_and_professions_get_endpoints_independent(client):
    """
    Verifies that GET requests to jobs, professions, and keyword search work independently.
    """
    res_jobs = client.get("/api/v1/jobs?sort_by=newest&page=1&page_size=15")
    assert res_jobs.status_code == 200
    data_jobs = res_jobs.json()
    assert "items" in data_jobs
    assert "total" in data_jobs
    assert len(data_jobs["items"]) <= 15

    res_prof = client.get("/api/v1/jobs/professions")
    assert res_prof.status_code == 200
    data_prof = res_prof.json()
    assert "professions" in data_prof
    assert "total_jobs" in data_prof

    res_search = client.get("/api/v1/jobs?keyword=data&sort_by=newest&page=1&page_size=15")
    assert res_search.status_code == 200
    data_search = res_search.json()
    assert "items" in data_search
    assert data_search["total"] >= 1

# ---------------------------------------------------------------------------
# F-04: Production Security Headers & Injection / SSRF Mitigations
# ---------------------------------------------------------------------------

def test_production_security_headers_present(client):
    res = client.get("/health")
    assert res.status_code == 200
    headers = res.headers
    assert headers.get("x-content-type-options") == "nosniff"
    assert headers.get("x-frame-options") == "DENY"
    assert headers.get("x-xss-protection") == "1; mode=block"
    assert "max-age=" in headers.get("strict-transport-security", "")
    assert headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "geolocation=()" in headers.get("permissions-policy", "")

def test_ssrf_and_loopback_redirect_protection():
    from app.services.visited_job_service import VisitedJobService
    from fastapi import HTTPException
    
    # Valid external URLs should pass
    valid_url = "https://boards.greenhouse.io/stripe/jobs/12345"
    assert VisitedJobService.validate_redirect_url(valid_url) == valid_url

    # Malicious loopback and cloud metadata SSRF targets must raise 400
    disallowed_urls = [
        "http://localhost/admin",
        "http://127.0.0.1:8000/internal",
        "http://169.254.169.254/latest/meta-data/",
        "http://0.0.0.0/secrets",
        "http://10.0.0.1/private",
        "http://192.168.1.1/router",
        "ftp://malicious.com/file",
        "javascript:alert(1)"
    ]
    for bad_url in disallowed_urls:
        with pytest.raises(HTTPException) as exc:
            VisitedJobService.validate_redirect_url(bad_url)
        assert exc.value.status_code == 400

def test_company_discovery_token_sanitization():
    from app.services.company_discovery import CompanyDiscoveryService
    
    # Path traversal attack input
    dirty_input = "../../../etc/passwd"
    clean_token = CompanyDiscoveryService.extract_token_from_input(dirty_input)
    assert "/" not in clean_token
    assert "." not in clean_token
    assert clean_token == "passwd"

def test_jwt_tampered_signature_rejected(client, candidate_token):
    # Tamper with the token signature
    parts = candidate_token.split(".")
    assert len(parts) == 3
    tampered_token = f"{parts[0]}.{parts[1]}.badsignature12345"
    
    headers = {"Authorization": f"Bearer {tampered_token}"}
    res = client.get("/api/v1/profile", headers=headers)
    assert res.status_code == 401
    assert "Invalid or expired access token" in res.json()["detail"]
