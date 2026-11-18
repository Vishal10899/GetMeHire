import pytest
from app.ingestion.crawler import CareerCrawlerService
from app.ingestion.adapters.bamboohr import BambooHRAdapter
from app.ingestion.adapters.teamtailor import TeamtailorAdapter
from app.ingestion.adapters.breezy import BreezyAdapter
from app.models import Company, Source
from app.services.job_service import JobService

def test_crawler_level2_ats_detection():
    # Test Greenhouse detection
    ats, board, feed = CareerCrawlerService.detect_ats("https://boards.greenhouse.io/stripe")
    assert ats == "GREENHOUSE"
    assert board == "stripe"
    assert "boards-api.greenhouse.io" in feed

    # Test Lever detection
    ats, board, feed = CareerCrawlerService.detect_ats("https://jobs.lever.co/spotify")
    assert ats == "LEVER"
    assert board == "spotify"
    assert "api.lever.co" in feed

    # Test Ashby detection
    ats, board, feed = CareerCrawlerService.detect_ats("https://jobs.ashbyhq.com/openai")
    assert ats == "ASHBY"
    assert board == "openai"
    assert "api.ashbyhq.com" in feed

    # Test Workable detection
    ats, board, feed = CareerCrawlerService.detect_ats("https://apply.workable.com/fortanix")
    assert ats == "WORKABLE"
    assert board == "fortanix"

    # Test SmartRecruiters detection
    ats, board, feed = CareerCrawlerService.detect_ats("https://jobs.smartrecruiters.com/cern")
    assert ats == "SMARTRECRUITERS"
    assert board == "cern"

    # Test Personio detection
    ats, board, feed = CareerCrawlerService.detect_ats("https://snocks.jobs.personio.de")
    assert ats == "PERSONIO"
    assert board == "snocks"

    # Test Recruitee detection
    ats, board, feed = CareerCrawlerService.detect_ats("https://bunq.recruitee.com")
    assert ats == "RECRUITEE"
    assert board == "bunq"

    # Test BambooHR detection
    ats, board, feed = CareerCrawlerService.detect_ats("https://postman.bamboohr.com/careers")
    assert ats == "BAMBOOHR"
    assert board == "postman"

    # Test Teamtailor detection
    ats, board, feed = CareerCrawlerService.detect_ats("https://career.teamtailor.com/jobs")
    assert ats == "TEAMTAILOR"
    assert board == "teamtailor"

    # Test Breezy HR detection
    ats, board, feed = CareerCrawlerService.detect_ats("https://anovia.breezy.hr")
    assert ats == "BREEZY"
    assert board == "anovia"

    # Test HTML fallback
    ats, board, feed = CareerCrawlerService.detect_ats("https://mycustomcorp.com/careers", html_content="<html><body><a href='https://boards.greenhouse.io/customco'>Join Us</a></body></html>")
    assert ats == "GREENHOUSE"
    assert board == "customco"

def test_bamboohr_adapter_normalization():
    adapter = BambooHRAdapter()
    raw = {
        "id": "101",
        "jobOpeningName": "Senior Backend Engineer",
        "location": {"city": "San Francisco", "state": "CA", "country": "United States"},
        "locationType": "remote",
        "employmentType": "full-time",
        "jobDescription": "<p>We are seeking a <strong>Python</strong> and <em>FastAPI</em> developer.</p>",
        "_company_slug": "acme"
    }
    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "101"
    assert norm.title == "Senior Backend Engineer"
    assert norm.remote_type == "REMOTE"
    assert norm.employment_type == "FULL_TIME"
    assert norm.application_url == "https://acme.bamboohr.com/careers/101"
    assert "Python" in norm.skills
    assert "Fastapi" in norm.skills

def test_teamtailor_adapter_normalization():
    adapter = TeamtailorAdapter()
    raw = {
        "id": "tt-202",
        "title": "Data Analyst (Remote)",
        "url": "https://career.myco.com/jobs/tt-202",
        "description": "SQL, Python, and analytics reporting experience required.",
        "location": "London, United Kingdom",
        "department": "Analytics"
    }
    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "tt-202"
    assert norm.title == "Data Analyst (Remote)"
    assert norm.remote_type == "REMOTE"
    assert norm.country == "United Kingdom"
    assert "Python" in norm.skills
    assert "Sql" in norm.skills

def test_breezy_adapter_normalization():
    adapter = BreezyAdapter()
    raw = {
        "id": "bz-303",
        "name": "DevOps Engineer",
        "url": "https://myco.breezy.hr/p/bz-303",
        "description": "Looking for AWS, Docker, Kubernetes and Terraform expert.",
        "location": {"city": "Berlin", "country": {"name": "Germany"}, "is_remote": True}
    }
    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "bz-303"
    assert norm.title == "DevOps Engineer"
    assert norm.remote_type == "REMOTE"
    assert norm.country == "Germany"
    assert "Aws" in norm.skills
    assert "Docker" in norm.skills

def test_company_registry_filtering(db_session):
    # Ensure test companies exist with industry and country
    stripe = db_session.query(Company).filter(Company.canonical_name == "Stripe").first()
    if not stripe:
        stripe = Company(canonical_name="Stripe", website="https://stripe.com", career_page_url="https://stripe.com/jobs", identity_status="VERIFIED")
        db_session.add(stripe)
    stripe.industry = "Software & IT"
    stripe.country = "United States"
    stripe.ats_provider = "GREENHOUSE"

    personio = db_session.query(Company).filter(Company.canonical_name == "Personio").first()
    if not personio:
        personio = Company(canonical_name="Personio", website="https://personio.de", career_page_url="https://personio.de/careers", identity_status="VERIFIED")
        db_session.add(personio)
    personio.industry = "Software & IT"
    personio.country = "Germany"
    personio.ats_provider = "PERSONIO"

    db_session.commit()

    # Verify company metadata filtering by industry
    res = JobService.get_companies_summary(db=db_session, industry="Software & IT")
    assert res.total >= 1
    assert any("software" in (c.industry or "").lower() for c in res.items)

    # Verify company metadata filtering by country
    res_de = JobService.get_companies_summary(db=db_session, country="Germany")
    assert res_de.total >= 1
    assert any("germany" in (c.country or "").lower() for c in res_de.items)
