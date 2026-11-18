import pytest

def test_search_jobs_basic(client):
    res = client.get("/api/v1/jobs")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 1
    assert data["page"] == 1
    assert data["page_size"] == 20

def test_search_jobs_by_keyword(client):
    res = client.get("/api/v1/jobs?keyword=Infrastructure")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for j in data["items"]:
        in_title_dept_skills = any("infrastructure" in str(j.get(k) or "").lower() for k in ["title", "department", "skills"])
        if not in_title_dept_skills:
            detail = client.get(f"/api/v1/jobs/{j['id']}").json()
            assert "infrastructure" in detail["description"].lower()

def test_search_jobs_by_company(client):
    res = client.get("/api/v1/jobs?company=Stripe")
    assert res.status_code == 200
    data = res.json()
    assert all(j["company_name"] == "Stripe" for j in data["items"])

def test_search_jobs_remote_filter(client):
    res = client.get("/api/v1/jobs?remote_type=REMOTE")
    assert res.status_code == 200
    data = res.json()
    assert all(j["remote_type"] == "REMOTE" for j in data["items"])

def test_search_jobs_salary_filter(client):
    res = client.get("/api/v1/jobs?min_salary=150000")
    assert res.status_code == 200
    data = res.json()
    assert all(float(j["salary_max"]) >= 150000 for j in data["items"] if j["salary_max"] is not None)

def test_job_detail_and_similar(client):
    # Fetch list first to get an ID
    list_res = client.get("/api/v1/jobs?page_size=1")
    assert list_res.status_code == 200
    job_id = list_res.json()["items"][0]["id"]

    # Detail
    det_res = client.get(f"/api/v1/jobs/{job_id}")
    assert det_res.status_code == 200
    detail = det_res.json()
    assert detail["id"] == job_id
    assert "description" in detail
    assert "company" in detail
    assert detail["application_url"].startswith("http")

    # Similar
    sim_res = client.get(f"/api/v1/jobs/{job_id}/similar")
    assert sim_res.status_code == 200
    sim_jobs = sim_res.json()["jobs"]
    assert isinstance(sim_jobs, list)

def test_get_professions_taxonomy_endpoint(client):
    res = client.get("/api/v1/jobs/professions")
    assert res.status_code == 200
    data = res.json()
    assert "professions" in data
    assert len(data["professions"]) >= 7
    assert data["total_jobs"] >= 1
    keys = {p["key"] for p in data["professions"]}
    assert "ENGINEERING" in keys
    assert "SALES_BIZDEV" in keys
    assert "PRODUCT_DESIGN" in keys

def test_search_jobs_by_profession(client):
    res = client.get("/api/v1/jobs?profession=SALES_BIZDEV")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 100
    assert all(j["profession"] == "SALES_BIZDEV" for j in data["items"])
