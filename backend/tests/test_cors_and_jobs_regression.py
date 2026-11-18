import pytest
from fastapi.testclient import TestClient

def test_regression_options_preflight_headers(client: TestClient):
    """
    Regression test: Verifies HTTP 200 and standard CORS preflight headers
    on all major platform endpoints from allowed origins.
    """
    endpoints = [
        "/api/v1/jobs",
        "/api/v1/jobs/professions",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
        "/api/v1/profile",
        "/api/v1/saved-jobs",
        "/api/v1/recommendations"
    ]
    allowed_origins = [
        "http://localhost:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
        "http://[::1]:3000"
    ]
    for endpoint in endpoints:
        for origin in allowed_origins:
            res = client.options(endpoint, headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST" if "auth" in endpoint else "GET",
                "Access-Control-Request-Headers": "authorization,content-type",
                "Access-Control-Request-Private-Network": "true"
            })
            assert res.status_code == 200, f"OPTIONS failed on {endpoint} from {origin}: {res.status_code} {res.text}"
            assert res.headers.get("access-control-allow-origin") == origin
            assert res.headers.get("access-control-allow-credentials") == "true"
            assert "GET" in res.headers.get("access-control-allow-methods", "")
            assert res.headers.get("access-control-allow-private-network") == "true"

def test_regression_cors_disallowed_origin_rejection(client: TestClient):
    """
    Regression test: Ensures unauthorized / malicious origins are rejected
    with HTTP 400 Disallowed CORS origin and leak no allow-origin headers.
    """
    disallowed = "http://evil-attacker.example.com"
    # Preflight
    res_opts = client.options("/api/v1/jobs", headers={
        "Origin": disallowed,
        "Access-Control-Request-Method": "GET"
    })
    assert res_opts.status_code == 400
    assert "Disallowed CORS origin" in res_opts.text
    assert res_opts.headers.get("access-control-allow-origin") != disallowed
    assert res_opts.headers.get("access-control-allow-origin") != "*"

    # Actual GET
    res_get = client.get("/api/v1/jobs", headers={"Origin": disallowed})
    assert res_get.headers.get("access-control-allow-origin") is None

def test_regression_jobs_get(client: TestClient):
    """
    Regression test: Verifies jobs GET endpoint returns 200, correct schema,
    and valid job metadata.
    """
    res = client.get("/api/v1/jobs?sort_by=newest&page=1&page_size=10")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "total_pages" in data
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert len(data["items"]) <= 10
    assert data["total"] > 0

    job = data["items"][0]
    required_fields = ["id", "title", "company_name", "location", "application_url", "source_name"]
    for field in required_fields:
        assert field in job, f"Missing required field {field} in job item"
        assert job[field] is not None

def test_regression_professions_get(client: TestClient):
    """
    Regression test: Verifies professions GET endpoint taxonomy and total counts.
    """
    res = client.get("/api/v1/jobs/professions")
    assert res.status_code == 200
    data = res.json()
    assert "professions" in data
    assert "total_jobs" in data
    assert isinstance(data["professions"], list)
    assert len(data["professions"]) >= 5
    assert data["total_jobs"] > 0

    for prof in data["professions"]:
        assert "key" in prof
        assert "label" in prof
        assert "count" in prof
        assert prof["count"] >= 0

def test_regression_search_filters(client: TestClient):
    """
    Regression test: Verifies search across keyword, profession, remote filter, and company.
    """
    # 1. Keyword search
    res_kw = client.get("/api/v1/jobs?keyword=Engineer&page_size=5")
    assert res_kw.status_code == 200
    data_kw = res_kw.json()
    assert data_kw["total"] > 0
    assert len(data_kw["items"]) > 0

    # 2. Profession filter
    res_prof = client.get("/api/v1/jobs?profession=ENGINEERING&page_size=5")
    assert res_prof.status_code == 200
    data_prof = res_prof.json()
    assert data_prof["total"] > 0
    for j in data_prof["items"]:
        assert j["profession"] == "ENGINEERING"

    # 3. Remote filter
    res_rem = client.get("/api/v1/jobs?remote_type=REMOTE&page_size=5")
    assert res_rem.status_code == 200
    data_rem = res_rem.json()
    if data_rem["total"] > 0:
        for j in data_rem["items"]:
            assert j["remote_type"] == "REMOTE"

def test_regression_pagination(client: TestClient):
    """
    Regression test: Verifies pagination consistency, page boundaries,
    and distinct items between page 1 and page 2.
    """
    page_size = 5
    # Page 1
    res_p1 = client.get(f"/api/v1/jobs?sort_by=newest&page=1&page_size={page_size}")
    assert res_p1.status_code == 200
    data_p1 = res_p1.json()
    items_p1 = data_p1["items"]
    assert len(items_p1) == page_size
    p1_ids = [j["id"] for j in items_p1]

    # Page 2
    res_p2 = client.get(f"/api/v1/jobs?sort_by=newest&page=2&page_size={page_size}")
    assert res_p2.status_code == 200
    data_p2 = res_p2.json()
    items_p2 = data_p2["items"]
    assert len(items_p2) == page_size
    p2_ids = [j["id"] for j in items_p2]

    # Ensure page 1 and page 2 items are disjoint (no duplicate jobs across pages)
    assert set(p1_ids).isdisjoint(set(p2_ids)), "Page 1 and Page 2 contain overlapping jobs"

    # Page out of bounds
    huge_page = 999999
    res_huge = client.get(f"/api/v1/jobs?page={huge_page}&page_size={page_size}")
    assert res_huge.status_code == 200
    data_huge = res_huge.json()
    assert data_huge["items"] == []
    assert data_huge["page"] == huge_page
