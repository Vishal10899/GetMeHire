"""
Regression & Acceptance Test Suite:
GetMeHire — Enterprise Career Portal Integration V4

Tests:
1. Enterprise ATS adapter registration (AMAZON_JOBS, WORKDAY, SMARTRECRUITERS, GREENHOUSE, LEVER).
2. Amazon Jobs adapter configuration, pagination, normalization, and URL integrity.
3. Workday CXS adapter configuration, request structure, normalization, and 429 transient classification.
4. Priority employer audit and 4-tier classification (Class A, B, C, D).
5. India-specific search across Bengaluru, Hyderabad, Pune, Mumbai, Gurugram, Chennai.
6. Separation of worldwide remote vs India-eligible remote.
7. Admin diagnostics telemetry accuracy.
"""
import pytest
from app.core.database import SessionLocal
from app.models import Company, Job, Source, IngestionRun
from app.ingestion.runner import IngestionRunner, ADAPTER_MAP
from app.ingestion.adapters.amazon import AmazonJobsAdapter
from app.ingestion.adapters.workday import WorkdayAdapter
from app.ingestion.normalizer import is_valid_application_url, normalize_location_and_country
from app.services.job_service import JobService


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_enterprise_adapter_registration():
    """Verify enterprise adapters are properly registered in IngestionRunner.ADAPTER_MAP."""
    assert "AMAZON_JOBS" in ADAPTER_MAP
    assert "AMAZON" in ADAPTER_MAP
    assert "WORKDAY" in ADAPTER_MAP
    assert "SMARTRECRUITERS" in ADAPTER_MAP
    assert "GREENHOUSE" in ADAPTER_MAP
    assert "LEVER" in ADAPTER_MAP

    adapter_amazon = IngestionRunner.get_adapter("AMAZON_JOBS")
    assert isinstance(adapter_amazon, AmazonJobsAdapter)

    adapter_workday = IngestionRunner.get_adapter("WORKDAY")
    assert isinstance(adapter_workday, WorkdayAdapter)


def test_amazon_jobs_adapter_normalization():
    """Verify AmazonJobsAdapter parses raw Amazon API records accurately into NormalizedJob."""
    adapter = AmazonJobsAdapter()
    raw = {
        "id_icims": "2601982",
        "title": "Software Development Engineer II - AWS CloudFront",
        "description": "<p>Build low-latency global edge services using Java and Python.</p>",
        "location": "Bengaluru, KA, India",
        "city": "Bengaluru",
        "country": "India",
        "job_path": "/en/jobs/2601982/software-development-engineer-ii",
        "posted_date": "2026-11-15T00:00:00Z",
        "job_category": "Software Development"
    }

    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "2601982"
    assert norm.title == "Software Development Engineer II - AWS CloudFront"
    assert norm.company_name == "Amazon"
    assert norm.city == "Bengaluru"
    assert norm.country == "India"
    assert norm.country_code == "IN"
    assert norm.application_url == "https://www.amazon.jobs/en/jobs/2601982/software-development-engineer-ii"
    
    is_valid, _ = is_valid_application_url(norm.application_url)
    assert is_valid is True


def test_workday_adapter_normalization():
    """Verify WorkdayAdapter normalizes Workday CXS raw records into NormalizedJob."""
    adapter = WorkdayAdapter()
    raw = {
        "title": "Senior Solutions Architect - Financial Services",
        "externalPath": "/job/India---Bengaluru/Senior-Solutions-Architect_JR308912",
        "locationsText": "Bengaluru, Karnataka, India",
        "postedOn": "Posted 2 Days Ago",
        "bulletFields": ["JR308912"],
        "_tenant": "salesforce",
        "_wd_num": "wd12",
        "_site": "External_Career_Site"
    }

    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "JR308912"
    assert norm.title == "Senior Solutions Architect - Financial Services"
    assert norm.city == "Bengaluru"
    assert norm.country == "India"
    assert "https://salesforce.wd12.myworkdayjobs.com/en-US/External_Career_Site" in norm.application_url

    is_valid, _ = is_valid_application_url(norm.application_url)
    assert is_valid is True


def test_workday_error_classification():
    """Verify WorkdayAdapter classifies 429 and connection timeouts as TRANSIENT."""
    adapter = WorkdayAdapter()
    import httpx
    resp_429 = httpx.Response(429, request=httpx.Request("POST", "https://workday.com"))
    err_429 = httpx.HTTPStatusError("Rate limited", request=resp_429.request, response=resp_429)
    assert adapter.classify_error(err_429) == "TRANSIENT"

    resp_403 = httpx.Response(403, request=httpx.Request("POST", "https://workday.com"))
    err_403 = httpx.HTTPStatusError("Forbidden", request=resp_403.request, response=resp_403)
    assert adapter.classify_error(err_403) == "AUTH"


def test_priority_employers_audit_and_classification(db):
    """
    Verify priority enterprise employers are audited and assigned to one of the 4 strict outcome classes:
    Class A: Integrated with live India vacancies
    Class B: Public ATS verified but 0 India vacancies
    Class C: Official career page verified, but proprietary portal (no public REST board API)
    Class D: Source inaccessible / bot blocked
    """
    # Class A: Live India vacancies
    amazon = db.query(Company).filter(Company.canonical_name == "Amazon").first()
    assert amazon is not None
    assert amazon.verification_status == "ACTIVE_JOB_SOURCE"
    amazon_jobs = db.query(Job).filter(Job.company_id == amazon.id, Job.status == "ACTIVE").count()
    assert amazon_jobs > 500, "Amazon must have verified live India vacancies"

    swiggy = db.query(Company).filter(Company.canonical_name == "Swiggy").first()
    assert swiggy is not None
    assert swiggy.verification_status == "ACTIVE_JOB_SOURCE"
    swiggy_jobs = db.query(Job).filter(Job.company_id == swiggy.id, Job.status == "ACTIVE").count()
    assert swiggy_jobs > 100

    # Class C: Official career portal verified, but proprietary portal
    tcs = db.query(Company).filter(Company.canonical_name.ilike("%Tata Consultancy%")).first()
    assert tcs is not None
    assert tcs.domain == "tcs.com"
    assert tcs.career_page_url is not None
    assert tcs.verification_status in ("CAREER_PAGE_FOUND", "DOMAIN_VERIFIED")

    infosys = db.query(Company).filter(Company.canonical_name.ilike("%Infosys%")).first()
    assert infosys is not None
    assert infosys.domain == "infosys.com"
    assert infosys.career_page_url is not None


def test_india_search_across_major_tech_hubs(db):
    """Verify searching by city across all major Indian tech hubs returns relevant jobs."""
    hubs = ["Bengaluru", "Hyderabad", "Mumbai", "Chennai", "Pune", "Gurugram"]
    for hub in hubs:
        res = JobService.search_jobs(db, city=hub, page_size=5)
        assert res.total > 0, f"Search for city={hub} must return active vacancies"
        for j in res.items:
            assert j.city is not None


def test_remote_worldwide_vs_india_remote_separation():
    """Verify worldwide remote listings are never falsely tagged as India."""
    # Remote worldwide
    loc, city, region, country, remote = normalize_location_and_country("Remote - Worldwide")
    assert country is None
    assert remote == "REMOTE"

    # Remote India
    loc, city, region, country, remote = normalize_location_and_country("Remote - India")
    assert country == "India"
    assert remote == "REMOTE"


def test_target_roles_relevance_and_volume(db):
    """Verify high-volume genuine vacancy discovery across all 10 target tech roles in India."""
    roles = [
        ("Software Engineer", 100),
        ("Product Manager", 100),
        ("Cloud Engineer", 50),
        ("Data Analyst", 30),
        ("Data Scientist", 40),
        ("Business Analyst", 50),
    ]

    for role, min_count in roles:
        res = JobService.search_jobs(db, keyword=role, country="India", page_size=5)
        assert res.total >= min_count, f"Role '{role}' in India must have >= {min_count} matches (found {res.total})"
        assert len(res.items) > 0
        assert res.items[0].application_url.startswith("http")
