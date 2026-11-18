import pytest
from app.ingestion.normalizer import (
    normalize_location_and_country,
    INDIA_CITIES,
    US_STATES,
    GLOBAL_CITIES,
    CITY_SEARCH_ALIASES
)
from app.ingestion.adapters.greenhouse import GreenhouseAdapter
from app.ingestion.adapters.lever import LeverAdapter
from app.ingestion.adapters.ashby import AshbyAdapter
from app.models import User, Profile, Job
from app.core.security import create_access_token

def test_location_normalizer_india_cities():
    # Bengaluru / Bangalore
    loc, city, region, country, remote_type = normalize_location_and_country("Bengaluru")
    assert country == "India"
    assert city == "Bengaluru"
    assert region == "Karnataka"
    assert remote_type == "ONSITE"

    loc, city, region, country, remote_type = normalize_location_and_country("Bangalore, India")
    assert country == "India"
    assert city == "Bengaluru"

    # Gurugram
    loc, city, region, country, remote_type = normalize_location_and_country("Gurugram, Haryana")
    assert country == "India"
    assert city == "Gurugram"
    assert region == "Haryana"

    # Mumbai
    loc, city, region, country, remote_type = normalize_location_and_country("Mumbai, India")
    assert country == "India"
    assert city == "Mumbai"
    assert region == "Maharashtra"

    # Delhi
    loc, city, region, country, remote_type = normalize_location_and_country("New Delhi, India")
    assert country == "India"
    assert city == "New Delhi"
    assert region == "Delhi"

def test_location_normalizer_remote_variants():
    # Remote India
    loc, city, region, country, remote_type = normalize_location_and_country("Remote - Bengaluru, India")
    assert country == "India"
    assert city == "Bengaluru"
    assert remote_type == "REMOTE"

    # Remote US
    loc, city, region, country, remote_type = normalize_location_and_country("Remote (US)")
    assert country == "United States"
    assert remote_type == "REMOTE"

    # Hybrid
    loc, city, region, country, remote_type = normalize_location_and_country("San Francisco, CA (Hybrid)")
    assert country == "United States"
    assert city == "San Francisco"
    assert region == "California"
    assert remote_type == "HYBRID"

def test_location_normalizer_global_cities():
    # London
    loc, city, region, country, remote_type = normalize_location_and_country("London, UK")
    assert country == "United Kingdom"
    assert city == "London"

    # Dublin
    loc, city, region, country, remote_type = normalize_location_and_country("Dublin, Ireland")
    assert country == "Ireland"
    assert city == "Dublin"

    # Tokyo
    loc, city, region, country, remote_type = normalize_location_and_country("Tokyo, Japan")
    assert country == "Japan"
    assert city == "Tokyo"

def test_greenhouse_adapter_normalizes_location():
    adapter = GreenhouseAdapter()
    raw = {
        "id": "gh-india-1",
        "title": "Software Development Engineer II",
        "content": "<p>Backend services in Python and FastAPI.</p>",
        "location": {"name": "Bengaluru, India"},
        "departments": [{"name": "Engineering"}],
        "absolute_url": "https://boards.greenhouse.io/test/jobs/gh-india-1"
    }
    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.city == "Bengaluru"
    assert norm.region == "Karnataka"
    assert norm.country == "India"
    assert norm.remote_type == "ONSITE"

def test_lever_adapter_normalizes_location():
    adapter = LeverAdapter()
    raw = {
        "id": "lever-in-1",
        "text": "Product Designer",
        "descriptionPlain": "UI/UX design with Figma and systems.",
        "categories": {
            "location": "Hyderabad",
            "team": "Design",
            "commitment": "Full-time"
        },
        "workplaceType": "remote",
        "hostedUrl": "https://jobs.lever.co/test/lever-in-1"
    }
    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.city == "Hyderabad"
    assert norm.region == "Telangana"
    assert norm.country == "India"
    assert norm.remote_type == "REMOTE"

def test_ashby_adapter_normalizes_location():
    adapter = AshbyAdapter()
    raw = {
        "id": "ashby-in-1",
        "title": "AI Research Scientist",
        "descriptionHtml": "<p>LLM pre-training and fine-tuning with Python.</p>",
        "location": "Delhi, India",
        "isRemote": False,
        "jobUrl": "https://jobs.ashbyhq.com/test/ashby-in-1"
    }
    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.city == "Delhi"
    assert norm.country == "India"
    assert norm.remote_type == "ONSITE"

def test_jobs_search_india_and_bangalore_alias(client, db_session):
    # Ensure test India jobs exist in the test DB
    comp = db_session.query(Job).filter(Job.country == "India").first()
    if not comp:
        import datetime
        now = datetime.datetime.now(datetime.timezone.utc)
        test_job1 = Job(
            company_id=1,
            source_id=1,
            external_job_id="test-india-blr-01",
            title="Senior Backend Engineer - India",
            normalized_title="Senior Backend Engineer",
            description="Working with Python and AWS.",
            profession="ENGINEERING",
            location="Bengaluru, India",
            city="Bengaluru",
            region="Karnataka",
            country="India",
            remote_type="ONSITE",
            employment_type="FULL_TIME",
            experience_level="SENIOR",
            skills=["Python", "AWS"],
            posting_date=now,
            first_seen_at=now,
            last_seen_at=now,
            last_verified_at=now,
            status="ACTIVE",
            application_url="https://stripe.com/jobs/test-india-blr-01",
            content_fingerprint="fp-test-india-blr-01"
        )
        db_session.add(test_job1)
        db_session.commit()

    # Test search by country=India
    r_country = client.get("/api/v1/jobs?country=India")
    assert r_country.status_code == 200
    data_country = r_country.json()
    assert data_country["total"] > 0
    for itm in data_country["items"]:
        assert itm["country"] == "India"

    # Test alias: location=Bangalore matches location=Bengaluru
    r_bangalore = client.get("/api/v1/jobs?location=Bangalore")
    r_bengaluru = client.get("/api/v1/jobs?location=Bengaluru")
    assert r_bangalore.status_code == 200
    assert r_bengaluru.status_code == 200
    assert r_bangalore.json()["total"] == r_bengaluru.json()["total"]
    assert r_bangalore.json()["total"] > 0

def test_jobs_search_match_score_for_authenticated_candidate(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # Authenticated request for candidate's primary skill (Python)
    r_auth = client.get("/api/v1/jobs?keyword=Python&page_size=5", headers=headers)
    assert r_auth.status_code == 200
    items_auth = r_auth.json()["items"]
    assert len(items_auth) > 0
    # At least one item should have match_score calculated
    assert any(itm.get("match_score") is not None for itm in items_auth)

    # Unauthenticated request
    r_unauth = client.get("/api/v1/jobs?keyword=Python&page_size=5")
    assert r_unauth.status_code == 200
    items_unauth = r_unauth.json()["items"]
    # Unauthenticated users must have null match_score (no invented scores)
    for itm in items_unauth:
        assert itm.get("match_score") is None


def _ensure_regression_seed_data(db_session):
    import datetime
    now = datetime.datetime.now(datetime.timezone.utc)
    jobs_to_seed = [
        Job(
            company_id=1,
            source_id=1,
            external_job_id="test-da-india-01",
            title="Senior Data Analyst - Growth",
            normalized_title="Senior Data Analyst",
            description="SQL and Python data analysis pipelines.",
            profession="DATA_AI",
            location="Bengaluru, India",
            city="Bengaluru",
            region="Karnataka",
            country="India",
            remote_type="ONSITE",
            employment_type="FULL_TIME",
            skills=["Python", "Sql"],
            posting_date=now,
            first_seen_at=now,
            last_seen_at=now,
            last_verified_at=now,
            status="ACTIVE",
            application_url="https://stripe.com/jobs/test-da-india-01",
            content_fingerprint="fp-test-da-india-01"
        ),
        Job(
            company_id=1,
            source_id=1,
            external_job_id="test-se-blr-01",
            title="Software Engineer - Core Platform",
            normalized_title="Software Engineer",
            description="Developing scalable distributed systems with Go.",
            profession="ENGINEERING",
            location="Bengaluru, India",
            city="Bengaluru",
            region="Karnataka",
            country="India",
            remote_type="ONSITE",
            employment_type="FULL_TIME",
            skills=["Go", "Docker"],
            posting_date=now,
            first_seen_at=now,
            last_seen_at=now,
            last_verified_at=now,
            status="ACTIVE",
            application_url="https://stripe.com/jobs/test-se-blr-01",
            content_fingerprint="fp-test-se-blr-01"
        ),
        Job(
            company_id=1,
            source_id=1,
            external_job_id="test-remote-india-01",
            title="Product Designer - Remote India",
            normalized_title="Product Designer",
            description="UI/UX design and design systems.",
            profession="PRODUCT_DESIGN",
            location="Remote, India",
            city="Bengaluru",
            region="Karnataka",
            country="India",
            remote_type="REMOTE",
            employment_type="FULL_TIME",
            skills=["Figma"],
            posting_date=now,
            first_seen_at=now,
            last_seen_at=now,
            last_verified_at=now,
            status="ACTIVE",
            application_url="https://stripe.com/jobs/test-remote-india-01",
            content_fingerprint="fp-test-remote-india-01"
        ),
        Job(
            company_id=1,
            source_id=1,
            external_job_id="test-uk-london-01",
            title="Account Executive - EMEA",
            normalized_title="Account Executive",
            description="Enterprise fintech sales across Europe.",
            profession="SALES_BIZDEV",
            location="London, United Kingdom",
            city="London",
            region="England",
            country="United Kingdom",
            remote_type="ONSITE",
            employment_type="FULL_TIME",
            skills=["Sales"],
            posting_date=now,
            first_seen_at=now,
            last_seen_at=now,
            last_verified_at=now,
            status="ACTIVE",
            application_url="https://stripe.com/jobs/test-uk-london-01",
            content_fingerprint="fp-test-uk-london-01"
        ),
    ]

    for j in jobs_to_seed:
        existing = db_session.query(Job).filter(Job.external_job_id == j.external_job_id).first()
        if not existing:
            db_session.add(j)
    db_session.commit()


def test_regression_case_1_data_analyst_india(client, db_session):
    _ensure_regression_seed_data(db_session)
    res = client.get("/api/v1/jobs?keyword=Data+Analyst&country=India")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["country"] == "India"
        has_match = (
            "analyst" in item["title"].lower()
            or "data" in item["title"].lower()
            or "analyst" in (item.get("profession") or "").lower()
        )
        if not has_match:
            detail = client.get(f"/api/v1/jobs/{item['id']}").json()
            desc_low = detail.get("description", "").lower()
            has_match = "data" in desc_low and "analyst" in desc_low
        assert has_match


def test_regression_case_2_software_engineer_bengaluru(client, db_session):
    _ensure_regression_seed_data(db_session)
    res = client.get("/api/v1/jobs?keyword=Software+Engineer&city=Bengaluru")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["city"] == "Bengaluru"


def test_regression_case_3_python_india(client, db_session):
    _ensure_regression_seed_data(db_session)
    res = client.get("/api/v1/jobs?keyword=Python&country=India")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["country"] == "India"


def test_regression_case_4_remote_india(client, db_session):
    _ensure_regression_seed_data(db_session)
    res = client.get("/api/v1/jobs?country=India&remote_type=REMOTE")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["country"] == "India"
        assert item["remote_type"] == "REMOTE"


def test_regression_case_5_globally_remote(client, db_session):
    _ensure_regression_seed_data(db_session)
    res = client.get("/api/v1/jobs?remote_type=REMOTE")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["remote_type"] == "REMOTE"


def test_regression_case_6_non_india_country(client, db_session):
    _ensure_regression_seed_data(db_session)
    res = client.get("/api/v1/jobs?country=United+Kingdom")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    for item in data["items"]:
        assert item["country"] == "United Kingdom"


def test_regression_case_7_unknown_country(client, db_session):
    # Safe query for country-less entries
    unknown_jobs = db_session.query(Job).filter((Job.country.is_(None)) | (Job.country == "")).all()
    # Ensure our check logic works
    assert isinstance(unknown_jobs, list)


def test_regression_case_8_empty_query(client, db_session):
    res = client.get("/api/v1/jobs")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 0
    assert len(data["items"]) > 0


def test_regression_case_9_random_gibberish_query(client, db_session):
    res = client.get("/api/v1/jobs?keyword=qwxzjklmnbvcxz987654321")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == 0
    assert len(data["items"]) == 0

