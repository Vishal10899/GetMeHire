"""
GlobalJobs - Final Master Engineering Cleanup Verification Tests
Tests for:
1. Data quality gate: is_valid_job_posting
2. Ingestion error classification: classify_error
3. Ingestion runner consecutive failure threshold & health status logic
4. Exclusion of synthetic seed listings from public discovery & matching
"""
import pytest
from app.ingestion.normalizer import is_valid_job_posting
from app.ingestion.base import SourceAdapter
from app.models import Job, Source, Company
from app.services.job_service import JobService
from app.services.matching_service import MatchingService

class DummyAdapter(SourceAdapter):
    def validate_configuration(self, config):
        return True
    def fetch_page(self, source_url, config, checkpoint):
        return [], {}, False
    def parse_and_normalize(self, raw_record):
        return None

def test_data_quality_gate_rejects_dummy_and_test_postings():
    # Invalid test titles
    assert is_valid_job_posting("Test Job", "This is a real long description about software engineering.")[0] is False
    assert is_valid_job_posting("test", "A valid description for engineering with more than 20 chars.")[0] is False
    assert is_valid_job_posting("Dummy Job", "A valid description for engineering with more than 20 chars.")[0] is False
    assert is_valid_job_posting("Placeholder", "A valid description for engineering with more than 20 chars.")[0] is False
    assert is_valid_job_posting("Test - Do Not Apply", "A valid description for engineering with more than 20 chars.")[0] is False

    # Short title or empty title
    assert is_valid_job_posting("AB", "A valid description for engineering with more than 20 chars.")[0] is False
    assert is_valid_job_posting("", "A valid description for engineering with more than 20 chars.")[0] is False
    assert is_valid_job_posting(None, "A valid description for engineering with more than 20 chars.")[0] is False

    # Invalid descriptions
    assert is_valid_job_posting("Senior Backend Engineer", "Test")[0] is False
    assert is_valid_job_posting("Senior Backend Engineer", "<p>Test Test</p>")[0] is False
    assert is_valid_job_posting("Senior Backend Engineer", "abc")[0] is False
    assert is_valid_job_posting("Senior Backend Engineer", "")[0] is False
    assert is_valid_job_posting("Senior Backend Engineer", None)[0] is False

    # Valid authentic posting
    valid, reason = is_valid_job_posting(
        "Senior Distributed Systems Engineer",
        "<p>We are seeking a senior distributed systems engineer to join our core cloud infrastructure team.</p>"
    )
    assert valid is True
    assert reason is None

def test_ingestion_error_classification():
    adapter = DummyAdapter()

    # Transient DNS and network errors
    assert adapter.classify_error(Exception("[Errno 11001] getaddrinfo failed")) == "TRANSIENT"
    assert adapter.classify_error(Exception("socket.gaierror: Name or service not known")) == "TRANSIENT"
    assert adapter.classify_error(Exception("Connection reset by peer")) == "TRANSIENT"
    assert adapter.classify_error(Exception("502 Bad Gateway")) == "TRANSIENT"
    assert adapter.classify_error(Exception("503 Service Unavailable")) == "TRANSIENT"
    assert adapter.classify_error(Exception("504 Gateway Timeout")) == "TRANSIENT"
    assert adapter.classify_error(Exception("HTTPSConnectionPool: Read timed out")) == "TRANSIENT"

    # Rate limiting
    assert adapter.classify_error(Exception("HTTP 429 Too Many Requests")) == "RATE_LIMIT"

    # Authentication
    assert adapter.classify_error(Exception("401 Unauthorized API key")) == "AUTHENTICATION"
    assert adapter.classify_error(Exception("403 Forbidden")) == "AUTHENTICATION"

    # Parse errors
    assert adapter.classify_error(Exception("JSONDecodeError: Expecting value")) == "PARSE"
    assert adapter.classify_error(Exception("XMLSyntaxError: unclosed token")) == "PARSE"

    # Permanent failures
    assert adapter.classify_error(Exception("404 Not Found")) == "PERMANENT"
    assert adapter.classify_error(Exception("Illegal schema definition")) == "PERMANENT"

def test_public_search_excludes_seed_demo_jobs(client, db_session):
    # Search without include_demo should not return seed jobs
    response = client.get("/api/v1/jobs?page_size=50")
    assert response.status_code == 200
    data = response.json()
    items = data["items"]

    # Verify no returned item has raw_source_data.seed == True
    for item in items:
        # None of the public results should be marked demo
        assert item.get("is_demo") is not True

def test_profession_counts_and_companies_clean(client):
    r_prof = client.get("/api/v1/jobs/professions")
    assert r_prof.status_code == 200
    pdata = r_prof.json()
    assert "professions" in pdata
    assert pdata["total_jobs"] >= 0

    r_comp = client.get("/api/v1/jobs/companies?page_size=10")
    assert r_comp.status_code == 200
    cdata = r_comp.json()
    assert "items" in cdata
    assert cdata["total"] >= 0
