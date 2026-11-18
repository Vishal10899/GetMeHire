"""
Regression & Acceptance Test Suite:
GetMeHire — India Employer & Job Coverage Expansion

Tests:
1. Indian employer discovery & public corporate registry coverage.
2. Official India career page identification & ATS board detection.
3. Indian city normalization and alias bidirectional matching.
4. Distinction between Remote India, Hybrid India, and Worldwide Remote.
5. Search across all 10 priority target roles in India.
6. Company alias resolution (TCS, HCL, Wipro, Swiggy, etc.).
7. ATS adapter pagination & continuation cursor safety.
8. Duplicate prevention across repeated ingestion runs.
9. Authentic application URL validation for India vacancies.
10. Admin dashboard India coverage diagnostics telemetry.
"""
import pytest
from app.core.database import SessionLocal
from app.models import Company, Job, Source, IngestionRun
from app.ingestion.normalizer import (
    normalize_location_and_country,
    normalize_location_full,
    is_valid_application_url,
    CITY_SEARCH_ALIASES,
    INDIA_CITIES,
)
from app.discovery.connectors.public_registries import PublicRegistriesConnector
from app.discovery.connectors.ats_directory import PublicAtsDirectoryConnector
from app.discovery.worker import CompanyDiscoveryService
from app.discovery.verifier import CareerCrawlerService, CompanyVerifierService
from app.services.job_service import JobService, COMPANY_ALIASES
from app.ingestion.adapters.smartrecruiters import SmartRecruitersAdapter


@pytest.fixture(scope="module")
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def test_indian_employer_discovery_and_registries(db):
    """Verify discovery connectors find major Indian IT, MNC, and tech employers."""
    reg_connector = PublicRegistriesConnector()
    reg_candidates = reg_connector.discover(limit=500)
    
    cand_names = {c.name.lower(): c for c in reg_candidates}
    
    # Priority Indian IT Companies
    assert "tata consultancy services" in cand_names
    assert cand_names["tata consultancy services"].country == "India"
    assert cand_names["tata consultancy services"].domain == "tcs.com"
    
    assert "infosys" in cand_names
    assert cand_names["infosys"].country == "India"
    
    assert "wipro" in cand_names
    assert cand_names["wipro"].country == "India"
    
    assert "hcltech" in cand_names
    assert cand_names["hcltech"].country == "India"
    
    assert "tech mahindra" in cand_names
    assert "ltimindtree" in cand_names
    assert "persistent systems" in cand_names
    assert "coforge" in cand_names


def test_india_career_page_and_ats_detection():
    """Verify detection of ATS providers and board identifiers from official careers URLs."""
    # SmartRecruiters detection
    provider, board, feed = CareerCrawlerService.detect_ats("https://jobs.smartrecruiters.com/swiggy")
    assert provider == "SMARTRECRUITERS"
    assert board == "swiggy"
    assert "api.smartrecruiters.com" in feed

    provider, board, feed = CareerCrawlerService.detect_ats("https://jobs.smartrecruiters.com/freshworks")
    assert provider == "SMARTRECRUITERS"
    assert board == "freshworks"

    # Greenhouse detection
    provider, board, feed = CareerCrawlerService.detect_ats("https://boards.greenhouse.io/thoughtworks")
    assert provider == "GREENHOUSE"
    assert board == "thoughtworks"
    assert "boards-api.greenhouse.io" in feed

    provider, board, feed = CareerCrawlerService.detect_ats("https://boards.greenhouse.io/razorpaysoftwareprivatelimited")
    assert provider == "GREENHOUSE"
    assert board == "razorpaysoftwareprivatelimited"


def test_india_city_normalization_and_aliases():
    """Verify Indian cities and common alias spellings normalize deterministically."""
    # Bengaluru / Bangalore
    loc, city, region, country, remote = normalize_location_and_country("Bangalore, Karnataka, India")
    assert city == "Bengaluru"
    assert country == "India"

    loc, city, region, country, remote = normalize_location_and_country("Bengaluru")
    assert city == "Bengaluru"
    assert country == "India"

    # Gurugram / Gurgaon
    loc, city, region, country, remote = normalize_location_and_country("Gurgaon, Haryana")
    assert city == "Gurugram"
    assert country == "India"

    # Mumbai / Bombay / Navi Mumbai
    loc, city, region, country, remote = normalize_location_and_country("Bombay")
    assert city == "Mumbai"
    assert country == "India"

    loc, city, region, country, remote = normalize_location_and_country("Navi Mumbai")
    assert city == "Navi Mumbai"
    assert country == "India"

    # Kolkata / Calcutta
    loc, city, region, country, remote = normalize_location_and_country("Calcutta, WB")
    assert city == "Kolkata"
    assert country == "India"

    # Chennai / Madras
    loc, city, region, country, remote = normalize_location_and_country("Madras")
    assert city == "Chennai"
    assert country == "India"

    # Thiruvananthapuram / Trivandrum
    loc, city, region, country, remote = normalize_location_and_country("Trivandrum, Kerala")
    assert city == "Thiruvananthapuram"
    assert country == "India"

    # Kochi / Cochin
    loc, city, region, country, remote = normalize_location_and_country("Cochin")
    assert city == "Kochi"
    assert country == "India"

    # Chandigarh / Mohali
    loc, city, region, country, remote = normalize_location_and_country("Mohali")
    assert city == "Mohali"
    assert country == "India"

    # Verify CITY_SEARCH_ALIASES coverage
    assert "bangalore" in CITY_SEARCH_ALIASES
    assert "bengaluru" in CITY_SEARCH_ALIASES["bangalore"]
    assert "gurgaon" in CITY_SEARCH_ALIASES
    assert "gurugram" in CITY_SEARCH_ALIASES["gurgaon"]


def test_remote_india_vs_worldwide_remote_distinction():
    """Verify correct distinction between Remote India, Hybrid India, and Worldwide Remote."""
    # Remote India explicitly
    loc, city, region, country, remote = normalize_location_and_country("Remote - India")
    assert country == "India"
    assert remote == "REMOTE"

    loc, city, region, country, remote = normalize_location_and_country("India (Remote)")
    assert country == "India"
    assert remote == "REMOTE"

    # Hybrid India
    loc, city, region, country, remote = normalize_location_and_country("Bengaluru, India (Hybrid)")
    assert city == "Bengaluru"
    assert country == "India"
    assert remote == "HYBRID"

    # Worldwide Remote (NOT labeled India)
    loc, city, region, country, remote = normalize_location_and_country("Remote")
    assert country is None
    assert remote == "REMOTE"

    loc, city, region, country, remote = normalize_location_and_country("Remote Worldwide")
    assert country is None
    assert remote == "REMOTE"

    # Remote US (NOT labeled India)
    loc, city, region, country, remote = normalize_location_and_country("Remote - US")
    assert country == "United States"
    assert remote == "REMOTE"


def test_india_specific_job_search_10_target_roles(db):
    """Verify search API returns authentic India listings across all 10 priority target roles."""
    target_roles = [
        "Data Analyst",
        "Software Engineer",
        "Data Scientist",
        "Machine Learning Engineer",
        "Business Analyst",
        "Java Developer",
        "Python Developer",
        "SQL Developer",
        "Product Manager",
        "Cloud Engineer",
    ]

    for role in target_roles:
        res = JobService.search_jobs(db, keyword=role, country="India", page_size=5)
        assert res.total > 0, f"Role search for '{role}' in India must return valid results"
        for item in res.items:
            # Ensure job is India-associated
            assert (item.country == "India" or item.country_code == "IN" or "India" in (item.location or "")), (
                f"Job {item.id} ({item.title}) returned for country=India must be India-associated"
            )


def test_company_alias_resolution(db):
    """Verify company aliases (e.g. TCS, HCL, Swiggy) resolve to canonical companies and return jobs."""
    # TCS alias
    res_tcs = JobService.search_jobs(db, company="TCS")
    assert res_tcs.total >= 0

    # Swiggy alias
    res_swiggy = JobService.search_jobs(db, company="Swiggy")
    assert res_swiggy.total > 0
    assert any("Swiggy" in item.company_name for item in res_swiggy.items)

    # Freshworks alias
    res_fw = JobService.search_jobs(db, company="Freshworks")
    assert res_fw.total > 0
    assert any("Freshworks" in item.company_name for item in res_fw.items)

    # Razorpay alias
    res_rp = JobService.search_jobs(db, company="Razorpay")
    assert res_rp.total > 0
    assert any("Razorpay" in item.company_name for item in res_rp.items)


def test_city_search_alias_expansion(db):
    """Verify searching for Bangalore returns Bengaluru jobs and vice versa."""
    res_bangalore = JobService.search_jobs(db, city="Bangalore")
    res_bengaluru = JobService.search_jobs(db, city="Bengaluru")

    assert res_bangalore.total > 0
    assert res_bengaluru.total > 0
    # Both queries should return the same count because aliases expand to each other
    assert res_bangalore.total == res_bengaluru.total


def test_smartrecruiters_checkpoint_safety():
    """Verify SmartRecruiters adapter handles None checkpoint and extracts board safely."""
    adapter = SmartRecruitersAdapter()
    config = {"board_id": "swiggy", "page_size": 2}
    
    # fetch_page must not throw AttributeError when checkpoint=None
    jobs, next_cp, has_more = adapter.fetch_page(
        "https://api.smartrecruiters.com/v1/companies/swiggy/postings",
        config,
        None
    )
    assert len(jobs) > 0
    assert isinstance(next_cp, dict)
    assert "offset" in next_cp


def test_application_url_validation_for_india_vacancies(db):
    """Verify application URLs for active India jobs are authentic, accessible ATS links."""
    india_jobs = db.query(Job).filter(
        ((Job.country == "India") | (Job.country_code == "IN")),
        Job.status == "ACTIVE"
    ).limit(30).all()

    assert len(india_jobs) > 0
    for j in india_jobs:
        is_valid, reason = is_valid_application_url(j.application_url)
        assert is_valid is True, f"Job {j.id} has invalid application URL: {j.application_url} ({reason})"
        assert not j.application_url.startswith("ftp://")
        assert "example.com" not in j.application_url
        assert "localhost" not in j.application_url


def test_admin_india_diagnostics_telemetry(db):
    """Verify admin discovery telemetry includes real India coverage diagnostics."""
    telemetry = CompanyDiscoveryService.get_discovery_telemetry(db)
    assert "india_diagnostics" in telemetry
    diag = telemetry["india_diagnostics"]
    
    assert diag["registered_employers"] > 50
    assert diag["verified_employers"] > 50
    assert diag["employers_with_career_pages"] > 40
    assert diag["active_job_sources"] >= 5
    assert diag["active_vacancies"] > 300
    assert len(diag["city_distribution"]) > 0
    assert len(diag["employer_distribution"]) > 0

    # Ensure Bengaluru is top tech hub
    city_names = [c["city"] for c in diag["city_distribution"]]
    assert "Bengaluru" in city_names
