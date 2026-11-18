import pytest
import datetime
import hashlib
from sqlalchemy.orm import Session
from app.models import Company, Source, Job, User
from app.ingestion.normalizer import (
    normalize_location_and_country,
    get_country_code,
    normalize_employment_type,
    normalize_work_arrangement_and_eligibility,
)
from app.ingestion.classifier import classify_profession_with_confidence
from app.services.job_service import JobService
from app.services.admin_service import AdminService

@pytest.fixture(scope="function")
def seeded_prd_jobs(db_session: Session):
    """
    Deterministic test fixtures specifically covering the PRD required scenarios.
    These fixtures are deterministic test fixtures and never represented as unverified vacancies.
    """
    # 1. Company
    co_global = db_session.query(Company).filter_by(canonical_name="GlobalCorp Test").first()
    if not co_global:
        co_global = Company(
            canonical_name="GlobalCorp Test",
            website="https://globalcorp.test",
            identity_status="VERIFIED"
        )
        db_session.add(co_global)
        db_session.flush()

    # 2. Source
    source_test = db_session.query(Source).filter_by(source_name="PRD_TEST_FEED").first()
    if not source_test:
        source_test = Source(
            company_id=co_global.id,
            source_name="PRD_TEST_FEED",
            source_type="GREENHOUSE",
            canonical_source_url="https://boards.greenhouse.io/globalcorp",
            access_classification="PUBLIC_API",
            is_active=True,
            health_status="HEALTHY"
        )
        db_session.add(source_test)
        db_session.flush()

    # 3. Deterministic Jobs
    now = datetime.datetime.now(datetime.timezone.utc)
    
    test_jobs = [
        # S1: AI Engineer in India (Bengaluru, Gurgaon, Hyderabad)
        {
            "external_job_id": "PRD_AI_IN_BLR",
            "title": "Senior AI Engineer",
            "country": "India",
            "country_code": "IN",
            "city": "Bengaluru",
            "location": "Bengaluru, Karnataka, India",
            "employment_type": "FULL_TIME",
            "work_arrangement": "HYBRID",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "DATA_AI",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/ai_blr"
        },
        {
            "external_job_id": "PRD_AI_IN_GGN",
            "title": "Lead Generative AI Engineer",
            "country": "India",
            "country_code": "IN",
            "city": "Gurgaon",
            "location": "Gurgaon, Haryana, India",
            "employment_type": "FULL_TIME",
            "work_arrangement": "ONSITE",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "DATA_AI",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/ai_ggn"
        },
        # S2: AI Engineer in US & Germany (Worldwide)
        {
            "external_job_id": "PRD_AI_US_SF",
            "title": "Machine Learning / AI Engineer",
            "country": "United States",
            "country_code": "US",
            "city": "San Francisco",
            "location": "San Francisco, CA, USA",
            "employment_type": "FULL_TIME",
            "work_arrangement": "ONSITE",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "DATA_AI",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/ai_sf"
        },
        {
            "external_job_id": "PRD_AI_DE_BER",
            "title": "Principal AI Research Engineer",
            "country": "Germany",
            "country_code": "DE",
            "city": "Berlin",
            "location": "Berlin, Germany",
            "employment_type": "FULL_TIME",
            "work_arrangement": "HYBRID",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "DATA_AI",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/ai_berlin"
        },
        # S3: Web Developer in London (Engineering, not sales)
        {
            "external_job_id": "PRD_WEB_DEV_LDN",
            "title": "Senior Web Developer",
            "country": "United Kingdom",
            "country_code": "GB",
            "city": "London",
            "location": "London, England, United Kingdom",
            "employment_type": "FULL_TIME",
            "work_arrangement": "ONSITE",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "ENGINEERING",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/web_dev_ldn"
        },
        # S4: Senior Surgeon (Worldwide Medical)
        {
            "external_job_id": "PRD_SR_SURGEON_US",
            "title": "Senior Orthopedic Surgeon",
            "country": "United States",
            "country_code": "US",
            "city": "Boston",
            "location": "Boston, MA, USA",
            "employment_type": "FULL_TIME",
            "work_arrangement": "ONSITE",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "HEALTHCARE_MEDICAL",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/surgeon_bos"
        },
        {
            "external_job_id": "PRD_SR_SURGEON_UK",
            "title": "Consultant General Surgeon",
            "country": "United Kingdom",
            "country_code": "GB",
            "city": "London",
            "location": "London, UK",
            "employment_type": "FULL_TIME",
            "work_arrangement": "ONSITE",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "HEALTHCARE_MEDICAL",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/surgeon_ldn"
        },
        # S5: Data Analyst + Canada + Contract
        {
            "external_job_id": "PRD_DATA_ANALYST_CA_CONTRACT",
            "title": "Senior Data Analyst",
            "country": "Canada",
            "country_code": "CA",
            "city": "Toronto",
            "location": "Toronto, Ontario, Canada",
            "employment_type": "CONTRACT",
            "work_arrangement": "HYBRID",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "DATA_AI",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/data_analyst_ca_contract"
        },
        # S6: Software Engineer + Germany + Hybrid
        {
            "external_job_id": "PRD_SWE_DE_HYBRID",
            "title": "Lead Software Engineer",
            "country": "Germany",
            "country_code": "DE",
            "city": "Munich",
            "location": "Munich, Bavaria, Germany",
            "employment_type": "FULL_TIME",
            "work_arrangement": "HYBRID",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "ENGINEERING",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/swe_de_hybrid"
        },
        # S7: Remote Python Developer + Worldwide eligibility
        {
            "external_job_id": "PRD_PYTHON_REMOTE_WORLDWIDE",
            "title": "Senior Remote Python Developer",
            "country": "United States",
            "country_code": "US",
            "city": "Remote",
            "location": "Remote (Worldwide)",
            "employment_type": "FULL_TIME",
            "work_arrangement": "REMOTE",
            "remote_eligibility": "WORLDWIDE",
            "profession": "ENGINEERING",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/python_remote_worldwide"
        },
        # S8: Part-time Customer Support + Australia
        {
            "external_job_id": "PRD_CS_AU_PART_TIME",
            "title": "Customer Support Specialist",
            "country": "Australia",
            "country_code": "AU",
            "city": "Sydney",
            "location": "Sydney, NSW, Australia",
            "employment_type": "PART_TIME",
            "work_arrangement": "ONSITE",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "CUSTOMER_SUPPORT",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/cs_au_pt"
        },
        # S9: Genuine Internship in United States
        {
            "external_job_id": "PRD_INTERN_US",
            "title": "Software Engineering Intern",
            "country": "United States",
            "country_code": "US",
            "city": "Seattle",
            "location": "Seattle, WA, USA",
            "employment_type": "INTERNSHIP",
            "work_arrangement": "ONSITE",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "ENGINEERING",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/intern_swe_us"
        },
        # S9 check: Internal Auditor in US (must NOT be returned as Internship)
        {
            "external_job_id": "PRD_INTERNAL_AUDITOR_US",
            "title": "Senior Internal Auditor",
            "country": "United States",
            "country_code": "US",
            "city": "Chicago",
            "location": "Chicago, IL, USA",
            "employment_type": "FULL_TIME",
            "work_arrangement": "ONSITE",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "FINANCE_ACCOUNTING",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/internal_auditor"
        },
        # S10: Non-IT profession + No Location (Store Manager / Aircraft Pilot)
        {
            "external_job_id": "PRD_STORE_MGR_AU",
            "title": "Retail Store Manager",
            "country": "Australia",
            "country_code": "AU",
            "city": "Melbourne",
            "location": "Melbourne, Victoria, Australia",
            "employment_type": "FULL_TIME",
            "work_arrangement": "ONSITE",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "HOSPITALITY_RETAIL",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/store_mgr_mel"
        },
        {
            "external_job_id": "PRD_STORE_MGR_CA",
            "title": "Flagship Store Manager",
            "country": "Canada",
            "country_code": "CA",
            "city": "Vancouver",
            "location": "Vancouver, BC, Canada",
            "employment_type": "FULL_TIME",
            "work_arrangement": "ONSITE",
            "remote_eligibility": "NOT_REMOTE",
            "profession": "HOSPITALITY_RETAIL",
            "application_url": "https://boards.greenhouse.io/globalcorp/jobs/store_mgr_yvr"
        }
    ]

    for item in test_jobs:
        existing = db_session.query(Job).filter_by(external_job_id=item["external_job_id"]).first()
        if not existing:
            job = Job(
                company_id=co_global.id,
                source_id=source_test.id,
                external_job_id=item["external_job_id"],
                title=item["title"],
                country=item["country"],
                country_code=item["country_code"],
                city=item["city"],
                location=item["location"],
                employment_type=item["employment_type"],
                work_arrangement=item["work_arrangement"],
                remote_eligibility=item["remote_eligibility"],
                profession=item["profession"],
                application_url=item["application_url"],
                description=f"Job description for {item['title']} located in {item['location']}.",
                status="ACTIVE",
                posting_date=now,
                first_seen_at=now,
                last_seen_at=now,
                last_verified_at=now,
                content_fingerprint=hashlib.sha256(item["external_job_id"].encode()).hexdigest(),
                raw_source_data={}
            )
            db_session.add(job)
        else:
            for k, v in item.items():
                setattr(existing, k, v)
            existing.status = "ACTIVE"
    
    db_session.commit()
    return True


# =========================================================================
# REQUIRED SCENARIOS 1-10 TEST SUITE
# =========================================================================

def test_scenario_1_ai_engineer_india(client, seeded_prd_jobs):
    """
    Scenario 1: AI Engineer + India
    Expected: Return AI Engineer vacancies across ALL available Indian cities (Bengaluru, Gurgaon, etc.).
    Do not restrict results to one city.
    """
    res = client.get("/api/v1/jobs?keyword=AI+Engineer&location=India")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) >= 2
    cities = {j["city"] for j in items if j.get("city")}
    assert "Bengaluru" in cities
    assert "Gurgaon" in cities
    for j in items:
        assert j["country"] == "India" or j.get("country_code") == "IN"


def test_scenario_2_ai_engineer_worldwide_no_location(client, seeded_prd_jobs):
    """
    Scenario 2: AI Engineer + empty location
    Expected: Return relevant vacancies worldwide (India, US, Germany, etc.).
    Never silently default an empty location to India or any single country.
    """
    res = client.get("/api/v1/jobs?keyword=AI+Engineer")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) >= 4
    countries = {j["country"] for j in items if j.get("country")}
    assert "India" in countries
    assert "United States" in countries
    assert "Germany" in countries


def test_scenario_3_web_developer_london(client, seeded_prd_jobs):
    """
    Scenario 3: Web Developer + London
    Expected: Return vacancies in London, strictly matching web engineering.
    Unrelated non-engineering (e.g. Sales Director) must not match.
    """
    res = client.get("/api/v1/jobs?keyword=Web+Developer&location=London")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) >= 1
    for j in items:
        assert j["city"] == "London"
        assert j["profession"] == "ENGINEERING"


def test_scenario_4_senior_surgeon_empty_location(client, seeded_prd_jobs):
    """
    Scenario 4: Senior Surgeon + empty location
    Expected: Return relevant healthcare / surgical vacancies worldwide.
    """
    res = client.get("/api/v1/jobs?keyword=Senior+Surgeon")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) >= 1
    for j in items:
        assert j["profession"] == "HEALTHCARE_MEDICAL"
        assert "Surgeon" in j["title"]


def test_scenario_5_data_analyst_canada_contract(client, seeded_prd_jobs):
    """
    Scenario 5: Data Analyst + Canada + Contract
    Expected: Return contract Data Analyst jobs in Canada.
    """
    res = client.get("/api/v1/jobs?keyword=Data+Analyst&location=Canada&employment_type=CONTRACT")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) >= 1
    for j in items:
        assert j["country"] == "Canada"
        assert j["employment_type"] == "CONTRACT"
        assert "Data Analyst" in j["title"]


def test_scenario_6_software_engineer_germany_hybrid(client, seeded_prd_jobs):
    """
    Scenario 6: Software Engineer + Germany + Hybrid
    Expected: Return hybrid Software Engineer jobs in Germany.
    """
    res = client.get("/api/v1/jobs?keyword=Software+Engineer&location=Germany&work_arrangement=HYBRID")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) >= 1
    for j in items:
        assert j["country"] == "Germany"
        assert j["work_arrangement"] == "HYBRID"


def test_scenario_7_remote_python_developer_worldwide(client, seeded_prd_jobs):
    """
    Scenario 7: Remote Python Developer + Worldwide eligibility
    Expected: Return remote Python Developer vacancies with WORLDWIDE eligibility.
    """
    res = client.get("/api/v1/jobs?keyword=Python+Developer&work_arrangement=REMOTE&remote_eligibility=WORLDWIDE")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) >= 1
    for j in items:
        assert j["work_arrangement"] == "REMOTE"
        assert j["remote_eligibility"] == "WORLDWIDE"


def test_scenario_8_part_time_customer_support_australia(client, seeded_prd_jobs):
    """
    Scenario 8: Part-time Customer Support + Australia
    Expected: Return part-time Customer Support jobs in Australia.
    """
    res = client.get("/api/v1/jobs?keyword=Customer+Support&location=Australia&employment_type=PART_TIME")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) >= 1
    for j in items:
        assert j["country"] == "Australia"
        assert j["employment_type"] == "PART_TIME"


def test_scenario_9_internship_united_states(client, seeded_prd_jobs):
    """
    Scenario 9: Internship + United States
    Expected: Return genuine internships in the US, bounded matching avoids 'Internal Auditor'.
    """
    res = client.get("/api/v1/jobs?location=United+States&employment_type=INTERNSHIP")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) >= 1
    for j in items:
        assert j["country"] == "United States" or j.get("country_code") == "US"
        assert j["employment_type"] == "INTERNSHIP" or "intern" in j["title"].lower()
        # Ensure Internal Auditor is NOT returned
        assert "internal auditor" not in j["title"].lower()


def test_scenario_10_non_it_profession_no_location(client, seeded_prd_jobs):
    """
    Scenario 10: Non-IT profession with no location filter (Store Manager).
    Expected: Return relevant retail / store manager opportunities worldwide.
    """
    res = client.get("/api/v1/jobs?keyword=Store+Manager")
    assert res.status_code == 200
    data = res.json()
    items = data["items"]
    assert len(items) >= 2
    # Top ranked results must be relevant Store Manager roles
    store_mgr_titles = [j["title"] for j in items if "Store Manager" in j["title"]]
    assert len(store_mgr_titles) >= 2
    assert any(j["country"] == "Australia" for j in items)
    assert any(j["country"] == "Canada" for j in items)


# =========================================================================
# ADDITIONAL VERIFICATION SCENARIOS
# =========================================================================

def test_no_hidden_india_default(client, seeded_prd_jobs):
    """
    Test: Empty location query never defaults to India.
    Must return multinational distribution.
    """
    res = client.get("/api/v1/jobs?page_size=30")
    assert res.status_code == 200
    data = res.json()
    countries = {j["country"] for j in data["items"] if j.get("country")}
    assert len(countries) >= 3
    assert "United States" in countries or "Germany" in countries or "Canada" in countries


def test_worldwide_location_normalization():
    """
    Test: Country and city normalization across US, Canada, Australia, Germany, UK, India.
    """
    # Canadian province
    _, _, _, c_ca, _ = normalize_location_and_country("Toronto, ON, Canada")
    assert c_ca == "Canada"
    assert get_country_code(c_ca) == "CA"

    # Australian state
    _, _, _, c_au, _ = normalize_location_and_country("Sydney, NSW, Australia")
    assert c_au == "Australia"
    assert get_country_code(c_au) == "AU"

    # German city
    _, _, _, c_de, _ = normalize_location_and_country("Berlin, Germany")
    assert c_de == "Germany"
    assert get_country_code(c_de) == "DE"

    # India city does not misclassify IN as Indiana
    _, _, _, c_in, _ = normalize_location_and_country("Bengaluru, Karnataka, India")
    assert c_in == "India"
    assert get_country_code(c_in) == "IN"


def test_employment_type_normalization():
    """
    Test: All PRD Section 4 employment types normalize accurately.
    """
    assert normalize_employment_type("Full Time") == "FULL_TIME"
    assert normalize_employment_type("Part-time (20 hrs)") == "PART_TIME"
    assert normalize_employment_type("Contractor / 6 months") == "CONTRACT"
    assert normalize_employment_type("Summer Intern 2026") == "INTERNSHIP"
    assert normalize_employment_type("Freelance Specialist") == "FREELANCE"
    assert normalize_employment_type("Fixed-term contract") == "FIXED_TERM"
    assert normalize_employment_type("Seasonal Associate") == "SEASONAL"
    assert normalize_employment_type("Apprentice") == "APPRENTICESHIP"


def test_work_arrangement_and_remote_eligibility():
    """
    Test: Work arrangement and remote eligibility normalization.
    """
    arr1, rel1 = normalize_work_arrangement_and_eligibility("Remote (Worldwide)")
    assert arr1 == "REMOTE"
    assert rel1 == "WORLDWIDE"

    arr2, rel2 = normalize_work_arrangement_and_eligibility("Remote (US Only)")
    assert arr2 == "REMOTE"
    assert rel2 == "COUNTRY_RESTRICTED"

    arr3, rel3 = normalize_work_arrangement_and_eligibility("Hybrid - Berlin Office")
    assert arr3 == "HYBRID"

    arr4, rel4 = normalize_work_arrangement_and_eligibility("On-site / In-Person")
    assert arr4 == "ONSITE"
    assert rel4 == "NOT_REMOTE"


def test_application_url_preservation(client, seeded_prd_jobs):
    """
    Test: Original ATS application URLs are strictly preserved without rewrite.
    """
    res = client.get("/api/v1/jobs?keyword=Senior+AI+Engineer&location=India")
    assert res.status_code == 200
    data = res.json()
    item = data["items"][0]
    assert item["application_url"] in [
        "https://boards.greenhouse.io/globalcorp/jobs/ai_blr",
        "https://boards.greenhouse.io/globalcorp/jobs/ai_ggn"
    ]


def test_search_quality_dashboard_endpoint(client, admin_token, seeded_prd_jobs):
    """
    Test: Admin Global Search Quality Dashboard endpoint returns authentic database metrics.
    """
    res = client.get(
        "/api/v1/admin/quality-dashboard",
        headers={"Authorization": f"Bearer {admin_token}"}
    )
    assert res.status_code == 200
    data = res.json()
    assert "global_active_jobs" in data
    assert data["global_active_jobs"] >= 10
    assert "active_employers" in data
    assert "active_job_sources" in data
    assert "country_distribution" in data
    assert "city_distribution" in data
    assert "profession_distribution" in data
    assert "employment_type_distribution" in data
    assert "work_arrangement_distribution" in data
    assert "remote_eligibility_distribution" in data
    assert "zero_job_sources" in data
    assert "failed_sources" in data
    assert "stale_jobs_count" in data
    assert "closed_jobs_count" in data
