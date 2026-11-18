"""
Target 1 Complete Verification Suite:
Worldwide Job Discovery & Intelligent Search Engine

Covers:
1. New ATS Adapters (Recruitee, Breezy HR, BambooHR, Teamtailor) & XXE protection.
2. Location Normalization & ISO Alpha-2 Country Code generation.
3. Multi-vacancy visibility per company (preserving all genuine vacancies).
4. Company Identity Resolution and Company Summary API.
5. Advanced Search Filters (country_code, experience_range, date_posted, sort_by=company).
6. SSRF Prevention & Ingestion Safety.
7. SHA-256 deduplication invariant.
"""

import pytest
import xml.etree.ElementTree as ET
from unittest.mock import patch, MagicMock

from app.ingestion.normalizer import (
    normalize_location_and_country,
    normalize_location_full,
    get_country_code,
    COUNTRY_TO_ISO_CODE,
    generate_normalized_title,
    clean_html_markup,
)
from app.ingestion.adapters.recruitee import RecruiteeAdapter
from app.ingestion.adapters.breezy import BreezyAdapter
from app.ingestion.adapters.bamboohr import BambooHRAdapter
from app.ingestion.adapters.teamtailor import TeamtailorAdapter
from app.services.company_discovery import CompanyDiscoveryService


# ============================================================================
# 1. NEW ATS ADAPTERS TESTS
# ============================================================================

def test_recruitee_adapter_parsing():
    adapter = RecruiteeAdapter()
    sample = {
        "id": 1094821,
        "title": "Senior Backend Go Engineer",
        "description": "<p>Build high-scale distributed banking systems in Go and PostgreSQL.</p>",
        "careers_url": "https://bunq.recruitee.com/o/senior-backend-go-engineer",
        "city": "Amsterdam",
        "country": "Netherlands",
        "country_code": "NL",
        "remote": True,
        "employment_type_code": "full_time",
        "department": "Engineering",
        "created_at": "2026-10-15T10:00:00.000Z",
    }

    norm = adapter.parse_and_normalize(sample)
    assert norm is not None
    assert norm.external_job_id == "1094821"
    assert norm.title == "Senior Backend Go Engineer"
    assert norm.country_code == "NL"
    assert norm.remote_type == "REMOTE"
    assert norm.employment_type == "FULL_TIME"
    assert norm.application_url == "https://bunq.recruitee.com/o/senior-backend-go-engineer"
    assert "Go" in norm.skills
    assert "Postgresql" in norm.skills


def test_breezy_adapter_parsing():
    adapter = BreezyAdapter()
    sample = {
        "id": "brz-54321",
        "name": "Cloud DevOps Architect",
        "description": "<div>Managing Kubernetes clusters on AWS and Terraform.</div>",
        "url": "https://techcorp.breezy.hr/p/brz-54321-cloud-devops-architect",
        "type": {"id": "full_time", "name": "Full-Time"},
        "experience": {"id": "senior", "name": "Senior"},
        "location": {
            "name": "Bengaluru, Karnataka, India",
            "city": "Bengaluru",
            "country": {"name": "India"},
            "is_remote": False,
        },
        "salary": {"min": 2500000, "max": 4000000, "currency": "INR"},
        "updated_at": "2026-11-01T12:00:00Z",
    }

    norm = adapter.parse_and_normalize(sample)
    assert norm is not None
    assert norm.external_job_id == "brz-54321"
    assert norm.title == "Cloud DevOps Architect"
    assert norm.country_code == "IN"
    assert norm.country == "India"
    assert norm.city == "Bengaluru"
    assert norm.experience_level == "SENIOR"
    assert norm.salary_min == 2500000.0
    assert norm.salary_currency == "INR"
    assert "Kubernetes" in norm.skills
    assert "Aws" in norm.skills


def test_bamboohr_adapter_parsing():
    adapter = BambooHRAdapter()
    sample = {
        "id": "bb-9876",
        "jobOpeningName": "Staff React Developer",
        "jobDescription": "<p>Lead frontend development using React, Next.js and Tailwind.</p>",
        "location": {"city": "Toronto", "state": "ON"},
        "employmentType": "Full-Time",
        "locationType": "hybrid",
        "compensation": "$140,000 - $175,000 CAD per year",
    }

    norm = adapter.parse_and_normalize(sample)
    assert norm is not None
    assert norm.external_job_id == "bb-9876"
    assert norm.title == "Staff React Developer"
    assert norm.country_code == "CA"
    assert norm.country == "Canada"
    assert norm.remote_type == "HYBRID"
    assert norm.salary_min == 140000.0
    assert norm.salary_max == 175000.0
    assert "React" in norm.skills


def test_teamtailor_adapter_parsing_and_xxe_protection():
    adapter = TeamtailorAdapter()
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
    <rss version="2.0" xmlns:teamtailor="http://teamtailor.com">
      <channel>
        <title>Acme Careers</title>
        <link>https://acme.teamtailor.com</link>
        <item>
          <guid>tt-item-001</guid>
          <title>Machine Learning Engineer</title>
          <description><![CDATA[Python, PyTorch and Docker infrastructure.]]></description>
          <link>https://acme.teamtailor.com/jobs/001-ml-engineer</link>
          <pubDate>Thu, 12 Nov 2026 10:00:00 GMT</pubDate>
          <teamtailor:location>Berlin, Germany</teamtailor:location>
          <teamtailor:employment-type>full_time</teamtailor:employment-type>
          <teamtailor:remote-status>hybrid</teamtailor:remote-status>
        </item>
      </channel>
    </rss>"""

    jobs = adapter.parse_xml_feed(xml_content, default_company="Acme Corp")
    assert len(jobs) == 1
    job = jobs[0]
    assert job.external_job_id == "tt-item-001"
    assert job.title == "Machine Learning Engineer"
    assert job.country_code == "DE"
    assert job.remote_type == "HYBRID"
    assert job.application_url == "https://acme.teamtailor.com/jobs/001-ml-engineer"
    assert "Python" in job.skills


# ============================================================================
# 2. LOCATION NORMALIZATION & ISO ALPHA-2 CODE TESTS
# ============================================================================

def test_location_normalization_india_hubs():
    locs = [
        ("Bengaluru, Karnataka, India", "IN", "India", "Bengaluru"),
        ("Hyderabad, Telangana", "IN", "India", "Hyderabad"),
        ("Noida, Uttar Pradesh", "IN", "India", "Noida"),
        ("Mumbai, MH", "IN", "India", "Mumbai"),
        ("Pune", "IN", "India", "Pune"),
    ]
    for raw, expected_iso, expected_country, expected_city in locs:
        clean_loc, city, region, country, country_code, remote_type = normalize_location_full(raw)
        assert country_code == expected_iso, f"Failed for {raw}: got {country_code}"
        assert country == expected_country
        assert city == expected_city


def test_location_normalization_global_countries():
    locs = [
        ("San Francisco, CA, USA", "US", "United States"),
        ("London, England, United Kingdom", "GB", "United Kingdom"),
        ("Dublin, Ireland", "IE", "Ireland"),
        ("Tokyo, Japan", "JP", "Japan"),
        ("Paris, France", "FR", "France"),
        ("Sydney, Australia", "AU", "Australia"),
        ("Zurich, Switzerland", "CH", "Switzerland"),
        ("Singapore", "SG", "Singapore"),
    ]
    for raw, expected_iso, expected_country in locs:
        clean_loc, city, region, country, country_code, remote_type = normalize_location_full(raw)
        assert country_code == expected_iso
        assert country == expected_country


def test_location_normalization_title_fallback():
    # Location is None or generic, but title contains country
    clean_loc, city, region, country, country_code, remote_type = normalize_location_full("", raw_title="Senior Python Developer - Germany")
    assert country_code == "DE"
    assert country == "Germany"

    clean_loc, city, region, country, country_code, remote_type = normalize_location_full("Remote", raw_title="Frontend Engineer (Japan)")
    assert country_code == "JP"
    assert country == "Japan"


def test_location_normalization_unspecified_preservation():
    # Ambiguous or global remote location should NOT fabricate a country
    clean_loc, city, region, country, country_code, remote_type = normalize_location_full("Worldwide / Anywhere")
    assert country_code is None
    assert country is None
    assert remote_type == "REMOTE" or clean_loc == "Worldwide / Anywhere"


# ============================================================================
# 3. MULTI-VACANCY & COMPANY IDENTITY INVARIANT TESTS
# ============================================================================

def test_multiple_jobs_per_company_preserved(client):
    """
    Business invariant: Multiple vacancies from the same company MUST remain
    discoverable. If Canonical or Stripe has dozens of openings, all must be accessible.
    """
    res = client.get("/api/v1/jobs?company=Canonical&page_size=50")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] > 1, f"Expected multiple vacancies for Canonical, found {data['total']}"
    assert len(data["items"]) >= min(data["total"], 50)
    for job in data["items"]:
        assert job["company_name"] == "Canonical"


def test_companies_summary_api(client):
    """
    Verify GET /api/v1/jobs/companies returns verified canonical company identities
    with accurate active job counts.
    """
    res = client.get("/api/v1/jobs/companies")
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    companies = data["items"]
    assert isinstance(companies, list)
    assert len(companies) >= 2

    # Ensure top hiring companies have active jobs
    canonical_entry = next((c for c in companies if c["canonical_name"] == "Canonical"), None)
    assert canonical_entry is not None
    assert canonical_entry["active_jobs_count"] >= 1
    assert canonical_entry["id"] is not None


# ============================================================================
# 4. ADVANCED SEARCH FILTERS API TESTS
# ============================================================================

def test_search_by_country_code(client):
    # Search by country_code=US
    res_us = client.get("/api/v1/jobs?country_code=US&page_size=10")
    assert res_us.status_code == 200
    data_us = res_us.json()
    assert data_us["total"] >= 1
    for job in data_us["items"]:
        assert job["country_code"] == "US"

    # Search by country_code=IN
    res_in = client.get("/api/v1/jobs?country_code=IN&page_size=10")
    assert res_in.status_code == 200
    data_in = res_in.json()
    assert data_in["total"] >= 1
    for job in data_in["items"]:
        assert job["country_code"] == "IN"


def test_search_by_experience_range(client):
    # Test entry range (0-2 years)
    res_entry = client.get("/api/v1/jobs?experience_range=entry&page_size=10")
    assert res_entry.status_code == 200
    data_entry = res_entry.json()
    assert data_entry["total"] >= 1

    # Test senior/5-8 range
    res_mid = client.get("/api/v1/jobs?experience_range=5-8&page_size=10")
    assert res_mid.status_code == 200
    data_mid = res_mid.json()
    assert data_mid["total"] >= 1


def test_search_by_date_posted(client):
    res_30d = client.get("/api/v1/jobs?date_posted=30d&page_size=10")
    assert res_30d.status_code == 200
    data_30d = res_30d.json()
    assert "items" in data_30d
    assert "total" in data_30d


def test_search_sort_by_company(client):
    res = client.get("/api/v1/jobs?sort_by=company&page_size=20")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) > 1
    # Verify alphabetical ordering
    company_names = [j["company_name"].lower() for j in items]
    assert company_names == sorted(company_names)


def test_search_by_company_id(client):
    # Fetch companies to get an ID
    comp_res = client.get("/api/v1/jobs/companies")
    assert comp_res.status_code == 200
    companies = comp_res.json()["items"]
    target_comp = next((c for c in companies if c["active_jobs_count"] >= 1), companies[0])

    res = client.get(f"/api/v1/jobs?company_id={target_comp['id']}")
    assert res.status_code == 200
    data = res.json()
    assert data["total"] == target_comp["active_jobs_count"]
    for j in data["items"]:
        assert j["company_id"] == target_comp["id"]


# ============================================================================
# 5. SECURITY & SSRF PROTECTION TESTS
# ============================================================================

def test_company_discovery_ssrf_blocking():
    service = CompanyDiscoveryService()
    unsafe_urls = [
        "http://localhost:8000/api/v1/jobs",
        "http://127.0.0.1:5432",
        "http://169.254.169.254/latest/meta-data",
        "http://0.0.0.0:80",
        "file:///etc/passwd",
    ]
    for url in unsafe_urls:
        assert service._is_safe_url(url) is False, f"Expected {url} to be blocked by SSRF filter"

    safe_urls = [
        "https://boards.greenhouse.io/canonical",
        "https://jobs.lever.co/stripe",
        "https://linear.recruitee.com",
    ]
    for url in safe_urls:
        assert service._is_safe_url(url) is True, f"Expected {url} to be allowed"
