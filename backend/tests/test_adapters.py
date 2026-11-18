import pytest
from app.ingestion.adapters.greenhouse import GreenhouseAdapter
from app.ingestion.adapters.lever import LeverAdapter
from app.ingestion.adapters.ashby import AshbyAdapter
from app.ingestion.adapters.generic_json import GenericJsonAdapter
from app.ingestion.adapters.web_scraper import WebScraperAdapter

def test_greenhouse_adapter_normalization():
    adapter = GreenhouseAdapter()
    raw = {
        "id": 123456,
        "title": "Senior Backend Engineer",
        "content": "<p>We build in Python and Docker with Postgres database.</p>",
        "location": {"name": "Remote, US"},
        "departments": [{"name": "Platform"}],
        "absolute_url": "https://boards.greenhouse.io/test/jobs/123456"
    }

    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "123456"
    assert norm.title == "Senior Backend Engineer"
    assert norm.remote_type == "REMOTE"
    assert "Python" in norm.skills
    assert "Docker" in norm.skills
    assert norm.application_url == "https://boards.greenhouse.io/test/jobs/123456"

def test_lever_adapter_normalization():
    adapter = LeverAdapter()
    raw = {
        "id": "lever-99",
        "text": "Frontend Software Engineer",
        "descriptionPlain": "Working with React, TypeScript and modern CSS.",
        "categories": {
            "location": "San Francisco, CA",
            "team": "Product Engineering",
            "commitment": "Full-time"
        },
        "workplaceType": "hybrid",
        "hostedUrl": "https://jobs.lever.co/test/lever-99"
    }

    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "lever-99"
    assert norm.remote_type == "HYBRID"
    assert norm.employment_type == "FULL_TIME"
    assert "React" in norm.skills
    assert "Typescript" in norm.skills

def test_ashby_adapter_normalization():
    adapter = AshbyAdapter()
    raw = {
        "id": "ashby-77",
        "title": "Lead Machine Learning Engineer",
        "descriptionHtml": "<p>Scaling AI inference models with Python and Cloud.</p>",
        "location": "London, UK",
        "isRemote": True,
        "compensation": {
            "minValue": 130000,
            "maxValue": 180000,
            "currency": "GBP"
        },
        "jobUrl": "https://jobs.ashbyhq.com/test/ashby-77"
    }

    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "ashby-77"
    assert norm.remote_type == "REMOTE"
    assert norm.experience_level == "LEAD"
    assert norm.salary_min == 130000
    assert norm.salary_currency == "GBP"

def test_generic_json_adapter():
    adapter = GenericJsonAdapter()
    raw = {
        "id": "json-1",
        "title": "DevOps Engineer",
        "description": "Kubernetes and Terraform expert.",
        "location": "Berlin",
        "remote": True,
        "url": "https://example.com/careers/json-1"
    }

    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.external_job_id == "json-1"
    assert norm.remote_type == "REMOTE"
    assert norm.application_url == "https://example.com/careers/json-1"

def test_web_scraper_adapter():
    adapter = WebScraperAdapter()
    raw = {
        "title": "Site Reliability Engineer",
        "url": "https://company.com/careers/sre-position",
        "parent_text": "Site Reliability Engineer - Remote position. We use Python and AWS."
    }

    norm = adapter.parse_and_normalize(raw)
    assert norm is not None
    assert norm.title == "Site Reliability Engineer"
    assert norm.remote_type == "REMOTE"
    assert "Python" in norm.skills
