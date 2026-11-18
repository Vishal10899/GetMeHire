import pytest
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime
import httpx

from app.ingestion.adapters.workable import WorkableAdapter
from app.ingestion.adapters.smartrecruiters import SmartRecruitersAdapter
from app.ingestion.adapters.personio import PersonioAdapter, safe_parse_xml
from app.ingestion.adapters.remotive import RemotiveAdapter, parse_salary_string
from app.ingestion.adapters.usajobs import USAJobsAdapter
from app.ingestion.runner import IngestionRunner, ADAPTER_MAP
from app.models import Source, Company, Job

# ==============================================================================
# 1. WorkableAdapter Tests
# ==============================================================================

def test_workable_adapter_validation():
    adapter = WorkableAdapter()
    assert adapter.validate_configuration({"company_slug": "arondite"}) is True
    assert adapter.validate_configuration({"account_slug": "aha"}) is True
    assert adapter.validate_configuration({"board_url": "https://apply.workable.com/test"}) is True
    assert adapter.validate_configuration({}) is False

def test_workable_adapter_normalization():
    adapter = WorkableAdapter()
    raw = {
        "shortcode": "WORK-101",
        "title": "Senior AI Systems Engineer",
        "department": "Engineering",
        "city": "London",
        "country": "United Kingdom",
        "state": "England",
        "telecommuting": True,
        "workplace": "hybrid",
        "employment_type": "full_time",
        "url": "https://apply.workable.com/j/WORK-101",
        "application_url": "https://apply.workable.com/j/WORK-101/apply",
        "published_on": "2026-11-10T12:00:00Z",
        "detail": {
            "description": "<p>We build production AI systems using Python, FastAPI, React and Kubernetes.</p>",
            "requirements": "<ul><li>5+ years Python</li><li>Docker & K8s</li></ul>",
            "benefits": "<p>Competitive equity, healthcare.</p>"
        }
    }

    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "WORK-101"
    assert norm.title == "Senior AI Systems Engineer"
    assert norm.country == "United Kingdom"
    assert norm.city == "London"
    assert norm.remote_type in ("REMOTE", "HYBRID")
    assert norm.employment_type == "FULL_TIME"
    assert norm.experience_level == "SENIOR"
    assert "Python" in norm.skills
    assert "Fastapi" in norm.skills
    assert "Kubernetes" in norm.skills
    assert norm.application_url == "https://apply.workable.com/j/WORK-101/apply"

def test_workable_adapter_missing_required_fields():
    adapter = WorkableAdapter()
    assert adapter.parse_and_normalize({}) is None
    assert adapter.parse_and_normalize({"shortcode": "123"}) is None  # Missing title
    assert adapter.parse_and_normalize({"title": "Developer"}) is None  # Missing shortcode

def test_workable_adapter_http_error_handling():
    adapter = WorkableAdapter()
    with patch("httpx.Client.get") as mock_get:
        # HTTP 404 test
        mock_resp_404 = MagicMock()
        mock_resp_404.status_code = 404
        mock_get.return_value = mock_resp_404

        with pytest.raises(Exception) as exc_info:
            adapter.fetch_page("https://apply.workable.com/nonexistent", {"company_slug": "nonexistent"}, {})
        assert "not found (HTTP 404)" in str(exc_info.value)

        # HTTP 429 test
        mock_resp_429 = MagicMock()
        mock_resp_429.status_code = 429
        mock_get.return_value = mock_resp_429

        with pytest.raises(Exception) as exc_info:
            adapter.fetch_page("https://apply.workable.com/test", {"company_slug": "test"}, {})
        assert "Rate limit exceeded" in str(exc_info.value)


# ==============================================================================
# 2. SmartRecruitersAdapter Tests
# ==============================================================================

def test_smartrecruiters_adapter_validation():
    adapter = SmartRecruitersAdapter()
    assert adapter.validate_configuration({"company_slug": "cern"}) is True
    assert adapter.validate_configuration({"company_identifier": "redbull"}) is True
    assert adapter.validate_configuration({}) is False

def test_smartrecruiters_adapter_normalization():
    adapter = SmartRecruitersAdapter()
    raw = {
        "id": "744000123456",
        "name": "Staff Data Infrastructure Engineer",
        "department": {"id": "eng", "label": "Infrastructure"},
        "location": {
            "city": "Geneva",
            "region": "Geneva",
            "country": "ch",
            "remote": False,
            "hybrid": True,
            "fullLocation": "Geneva, Switzerland"
        },
        "releasedDate": "2026-11-12T10:00:00.000Z",
        "_company_slug": "cern",
        "detail": {
            "jobAd": {
                "sections": {
                    "jobDescription": {"text": "<p>Scale high-performance distributed systems with Python, Golang, and Docker.</p>"},
                    "qualifications": {"text": "<p>Deep experience in PostgreSQL, Kubernetes, and Cloud.</p>"}
                }
            }
        }
    }

    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "744000123456"
    assert norm.title == "Staff Data Infrastructure Engineer"
    assert norm.department == "Infrastructure"
    assert norm.country == "Switzerland"
    assert norm.city == "Geneva"
    assert norm.remote_type == "HYBRID"
    assert "Python" in norm.skills
    assert "Golang" in norm.skills
    assert "Kubernetes" in norm.skills
    assert norm.application_url == "https://jobs.smartrecruiters.com/cern/744000123456"

def test_smartrecruiters_pagination():
    adapter = SmartRecruitersAdapter()
    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "totalFound": 250,
            "content": [{"id": f"job-{i}", "name": f"Job {i}"} for i in range(100)]
        }
        mock_get.return_value = mock_resp

        records, next_cp, has_more = adapter.fetch_page(
            "https://api.smartrecruiters.com/v1/companies/test/postings",
            {"company_slug": "test", "page_size": 100, "fetch_details": False},
            {"offset": 0}
        )

        assert len(records) == 100
        assert has_more is True
        assert next_cp["offset"] == 100
        assert next_cp["total_found"] == 250


# ==============================================================================
# 3. PersonioAdapter Tests
# ==============================================================================

def test_personio_adapter_validation():
    adapter = PersonioAdapter()
    assert adapter.validate_configuration({"company_slug": "personio"}) is True
    assert adapter.validate_configuration({"board_url": "https://personio.jobs.personio.de/xml"}) is True
    assert adapter.validate_configuration({}) is False

def test_personio_safe_xml_parsing_security():
    # Test valid XML parses cleanly
    valid_xml = "<workzag-jobs><position><id>1</id><name>Engineer</name></position></workzag-jobs>"
    root = safe_parse_xml(valid_xml)
    assert root.tag == "workzag-jobs"

    # Test XXE attack payload is blocked
    malicious_doctype = '<!DOCTYPE foo [<!ENTITY xxe SYSTEM "file:///etc/passwd">]><workzag-jobs></workzag-jobs>'
    with pytest.raises(ValueError) as exc:
        safe_parse_xml(malicious_doctype)
    assert "Security violation" in str(exc.value)

    malicious_entity = '<!ENTITY test "attack"><workzag-jobs></workzag-jobs>'
    with pytest.raises(ValueError) as exc:
        safe_parse_xml(malicious_entity)
    assert "Security violation" in str(exc.value)

def test_personio_adapter_normalization():
    adapter = PersonioAdapter()
    raw = {
        "id": "998877",
        "name": "Senior DevOps Specialist (d/f/m)",
        "office": "Berlin, Germany",
        "department": "Cloud Infrastructure",
        "employmentType": "permanent",
        "seniority": "senior",
        "schedule": "full-time",
        "createdAt": "2026-11-10T14:30:00+00:00",
        "_company_slug": "personio",
        "_feed_domain": "de",
        "descriptions": [
            {"name": "About the Role", "value": "<p>Manage our AWS, Terraform, Kubernetes, and Docker environments.</p>"},
            {"name": "Your Profile", "value": "<p>Deep experience with Linux, Python, and CI/CD pipelines.</p>"}
        ]
    }

    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "998877"
    assert norm.title == "Senior DevOps Specialist (d/f/m)"
    assert norm.department == "Cloud Infrastructure"
    assert norm.country == "Germany"
    assert norm.city == "Berlin"
    assert norm.experience_level == "SENIOR"
    assert norm.employment_type == "FULL_TIME"
    assert "Aws" in norm.skills
    assert "Kubernetes" in norm.skills
    assert "Python" in norm.skills
    assert norm.application_url == "https://personio.jobs.personio.de/job/998877"


# ==============================================================================
# 4. RemotiveAdapter Tests
# ==============================================================================

def test_remotive_salary_parsing():
    s_min, s_max, curr = parse_salary_string("$85k - $155k")
    assert s_min == Decimal("85000")
    assert s_max == Decimal("155000")
    assert curr == "USD"

    s_min, s_max, curr = parse_salary_string("90000 - 120000 EUR")
    assert s_min == Decimal("90000")
    assert s_max == Decimal("120000")
    assert curr == "EUR"

    s_min, s_max, curr = parse_salary_string("$120k")
    assert s_min == Decimal("120000")
    assert s_max == Decimal("120000")

    assert parse_salary_string(None) == (None, None, "USD")

def test_remotive_adapter_normalization():
    adapter = RemotiveAdapter()
    raw = {
        "id": 2091173,
        "title": "Lead Backend Python Architect",
        "company_name": "Automattic",
        "category": "Software Development",
        "candidate_required_location": "USA, Canada, UK, Worldwide",
        "job_type": "full_time",
        "publication_date": "2026-11-13T17:29:57",
        "url": "https://remotive.com/remote-jobs/software-dev/lead-backend-python-architect-2091173",
        "salary": "$140k - $180k",
        "description": "<p>Design high-scale APIs with Python, FastAPI, PostgreSQL and Redis.</p>",
        "tags": ["python", "redis", "fastapi", "remote"]
    }

    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "remotive-2091173"
    assert norm.title == "Lead Backend Python Architect"
    assert norm.company_name == "Automattic"
    assert norm.remote_type == "REMOTE"
    assert norm.salary_min == Decimal("140000")
    assert norm.salary_max == Decimal("180000")
    assert "Python" in norm.skills
    assert "Fastapi" in norm.skills
    assert "Postgres" in norm.skills
    # Preserves exact Remotive URL
    assert norm.application_url == "https://remotive.com/remote-jobs/software-dev/lead-backend-python-architect-2091173"


# ==============================================================================
# 5. USAJobsAdapter Tests
# ==============================================================================

def test_usajobs_adapter_validation():
    adapter = USAJobsAdapter()
    assert adapter.validate_configuration({"api_key": "secret-key", "user_agent_email": "dev@test.gov"}) is True
    assert adapter.validate_configuration({}) is False

def test_usajobs_adapter_normalization():
    adapter = USAJobsAdapter()
    raw = {
        "MatchedObjectId": "USA-9988",
        "MatchedObjectDescriptor": {
            "PositionID": "DE-12345-2210",
            "PositionTitle": "IT Specialist (INFOSEC/Cybersecurity)",
            "PositionURI": "https://www.usajobs.gov/GetJob/ViewDetails/USA-9988",
            "ApplyURI": ["https://www.usajobs.gov/GetJob/ViewDetails/USA-9988?apply=true"],
            "OrganizationName": "Defense Information Systems Agency",
            "DepartmentName": "Department of Defense",
            "PositionLocation": [
                {
                    "LocationName": "Fort Meade, Maryland",
                    "CityName": "Fort Meade",
                    "CountrySubdivisionCode": "Maryland",
                    "CountryCode": "United States"
                }
            ],
            "PositionRemuneration": [
                {
                    "MinimumRange": "112000.00",
                    "MaximumRange": "145000.00",
                    "RateIntervalCode": "Per Year"
                }
            ],
            "PublicationStartDate": "2026-11-08T00:00:00Z",
            "UserArea": {
                "Details": {
                    "JobSummary": "Serve as a senior cybersecurity specialist managing network defense and Linux security.",
                    "KeyRequirements": ["Must be a US Citizen", "Top Secret Clearance"],
                    "TeleworkEligible": True
                }
            }
        }
    }

    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "usajobs-DE-12345-2210"
    assert norm.title == "IT Specialist (INFOSEC/Cybersecurity)"
    assert norm.company_name == "Department of Defense"
    assert norm.department == "Defense Information Systems Agency"
    assert norm.country == "United States"
    assert norm.remote_type == "REMOTE"
    assert norm.salary_min == Decimal("112000.00")
    assert norm.salary_max == Decimal("145000.00")
    assert norm.salary_period == "YEAR"
    assert "Cybersecurity" in norm.skills
    assert "Linux" in norm.skills
    assert norm.application_url == "https://www.usajobs.gov/GetJob/ViewDetails/USA-9988?apply=true"

def test_usajobs_auth_error_handling():
    adapter = USAJobsAdapter()
    with patch("httpx.Client.get") as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_get.return_value = mock_resp

        with pytest.raises(PermissionError) as exc_info:
            adapter.fetch_page("https://data.usajobs.gov/api/Search", {"api_key": "bad-key", "user_agent_email": "a@b.com"}, {})
        assert "authentication failed" in str(exc_info.value)


# ==============================================================================
# 6. IngestionRunner & Multi-Employer Integration Tests
# ==============================================================================

def test_runner_adapter_map_completeness():
    expected_adapters = [
        "GREENHOUSE", "LEVER", "ASHBY", "GENERIC_JSON", "WEB_SCRAPER",
        "WORKABLE", "SMARTRECRUITERS", "PERSONIO", "REMOTIVE", "USAJOBS"
    ]
    for key in expected_adapters:
        assert key in ADAPTER_MAP
        adapter_instance = IngestionRunner.get_adapter(key)
        assert adapter_instance is not None

def test_runner_multi_employer_feed_resolution(db_session):
    # Register test company and source
    test_comp = Company(canonical_name="Remotive Platform Host", website="https://remotive.com")
    db_session.add(test_comp)
    db_session.flush()

    source = Source(
        company_id=test_comp.id,
        source_name="Remotive Engineering Test Feed",
        source_type="REMOTIVE",
        canonical_source_url="https://remotive.com/api/remote-jobs",
        access_classification="PUBLIC_FEED",
        is_active=True,
        health_status="HEALTHY",
        configuration={"limit": 2}
    )
    db_session.add(source)
    db_session.flush()

    mock_feed_data = [
        {
            "id": 99901,
            "title": "Senior React Developer",
            "company_name": "Acme Widgets Inc",
            "candidate_required_location": "USA, Remote",
            "url": "https://remotive.com/remote-jobs/99901",
            "description": "Building modern React UIs."
        },
        {
            "id": 99902,
            "title": "Cloud Architect",
            "company_name": "Globex Corporation",
            "candidate_required_location": "Worldwide",
            "url": "https://remotive.com/remote-jobs/99902",
            "description": "AWS and Terraform cloud architecture."
        }
    ]

    with patch.object(RemotiveAdapter, "fetch_page", return_value=(mock_feed_data, {"completed": True}, False)):
        run = IngestionRunner.execute_sync(db_session, source.id)
        assert run.status == "SUCCESS"
        assert run.records_inserted == 2

        # Verify dynamic company creation
        acme_comp = db_session.query(Company).filter(Company.canonical_name == "Acme Widgets Inc").first()
        globex_comp = db_session.query(Company).filter(Company.canonical_name == "Globex Corporation").first()

        assert acme_comp is not None
        assert globex_comp is not None

        # Verify jobs were created and linked to the resolved companies
        j1 = db_session.query(Job).filter(Job.external_job_id == "remotive-99901").first()
        j2 = db_session.query(Job).filter(Job.external_job_id == "remotive-99902").first()

        assert j1 is not None
        assert j1.company_id == acme_comp.id
        assert j1.source_id == source.id
        assert j1.remote_type == "REMOTE"

        assert j2 is not None
        assert j2.company_id == globex_comp.id
        assert j2.source_id == source.id

        # Clean up test records
        db_session.delete(j1)
        db_session.delete(j2)
        db_session.delete(source)
        db_session.delete(test_comp)
        db_session.delete(acme_comp)
        db_session.delete(globex_comp)
        db_session.commit()

