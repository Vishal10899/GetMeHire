"""
Target 1 Final Gap Closure Verification Suite:
1. Exact Non-Overlapping Experience Boundaries (0, 1, 2, 3, 4, 5, 6, 8, 9, unquantified, unspecified).
2. Company Search & Verified Alias Resolution (Scale, Canonical, Stripe, Monzo, Duolingo, On Running).
3. Job Category & Industry Filtering (Software Engineering, Healthcare, combined filters).
4. Application URL Verifier Service (VALID, REDIRECTED, TEMPORARILY_UNAVAILABLE, CONFIRMED_BROKEN, SSRF safety).
"""

import pytest
import datetime
from unittest.mock import patch, MagicMock
from app.models import Job, Company, Source
from app.services.job_service import JobService, COMPANY_ALIASES
from app.services.url_verifier import UrlVerifierService


# ============================================================================
# 1. EXPERIENCE BOUNDARIES TESTS
# ============================================================================

def test_experience_boundary_intervals(db_session):
    """
    Verifies that experience ranges are strictly non-overlapping half-open intervals:
    - 0-1: [0, 1]
    - 1-3: (1, 3]
    - 3-5: (3, 5]
    - 5-8: (5, 8]
    - 8+:  (8, inf)
    - entry: [0, 2]
    - internship: employment_type == 'INTERNSHIP' or min_years == 0 or title contains 'intern'
    - unspecified: min_years IS NULL AND experience_level IS NULL AND employment_type != 'INTERNSHIP'
    """
    comp = db_session.query(Company).first()
    src = db_session.query(Source).first()
    now = datetime.datetime.now(datetime.timezone.utc)

    # Helper to insert test job
    created_jobs = []
    def make_job(ext_id, title, years, level=None, emp_type="FULL_TIME"):
        j = Job(
            company_id=comp.id,
            source_id=src.id,
            external_job_id=ext_id,
            title=title,
            normalized_title=title,
            description="Experience boundary test description.",
            profession="ENGINEERING",
            department="Engineering",
            location="San Francisco, CA",
            city="San Francisco",
            country="United States",
            country_code="US",
            remote_type="ONSITE",
            employment_type=emp_type,
            min_experience_years=years,
            experience_level=level,
            posting_date=now,
            first_seen_at=now,
            last_seen_at=now,
            status="ACTIVE",
            application_url=f"https://example.com/jobs/{ext_id}",
            content_fingerprint=f"fp-{ext_id}"
        )
        db_session.add(j)
        created_jobs.append(j)
        return j

    # Seed jobs with exact boundary years
    j0 = make_job("bound-0y", "Engineer 0 Year", 0.0)
    j1 = make_job("bound-1y", "Engineer 1 Year", 1.0)
    j2 = make_job("bound-2y", "Engineer 2 Year", 2.0)
    j3 = make_job("bound-3y", "Engineer 3 Year", 3.0)
    j4 = make_job("bound-4y", "Engineer 4 Year", 4.0)
    j5 = make_job("bound-5y", "Engineer 5 Year", 5.0)
    j6 = make_job("bound-6y", "Engineer 6 Year", 6.0)
    j8 = make_job("bound-8y", "Engineer 8 Year", 8.0)
    j9 = make_job("bound-9y", "Engineer 9 Year", 9.0)

    # Unquantified jobs
    j_unq_entry = make_job("bound-unq-entry", "Junior Dev", None, level="ENTRY")
    j_unq_mid = make_job("bound-unq-mid", "Mid Dev", None, level="MID")
    j_unq_sr = make_job("bound-unq-sr", "Senior Dev", None, level="SENIOR")
    j_unq_lead = make_job("bound-unq-lead", "Staff Dev", None, level="LEAD")

    # Unspecified job
    j_unspecified = make_job("bound-unspecified", "General Specialist", None, level=None, emp_type="FULL_TIME")

    # Internship job
    j_intern = make_job("bound-intern", "Summer Intern", None, level=None, emp_type="INTERNSHIP")

    db_session.commit()

    try:
        # 1. Range "0-1" -> MUST match j0, j1, j_unq_entry; MUST NOT match j2, j3, j4, j5, j8, j9, j_unspecified
        r_01 = JobService.search_jobs(db_session, experience_range="0-1", page_size=100)
        titles_01 = {job.title for job in r_01.items}
        assert "Engineer 0 Year" in titles_01
        assert "Engineer 1 Year" in titles_01
        assert "Junior Dev" in titles_01
        assert "Engineer 2 Year" not in titles_01, "2.0 years must not be in 0-1"
        assert "Engineer 3 Year" not in titles_01
        assert "General Specialist" not in titles_01, "Unspecified must never match 0-1"

        # 2. Range "1-3" -> MUST match j2, j3; MUST NOT match j1 (boundary test: 1 is in 0-1, not 1-3)
        r_13 = JobService.search_jobs(db_session, experience_range="1-3", page_size=100)
        titles_13 = {job.title for job in r_13.items}
        assert "Engineer 2 Year" in titles_13
        assert "Engineer 3 Year" in titles_13
        assert "Engineer 1 Year" not in titles_13, "1.0 year boundary must be in 0-1, not 1-3"
        assert "Engineer 4 Year" not in titles_13, "4.0 years must not be in 1-3"
        assert "General Specialist" not in titles_13

        # 3. Range "3-5" -> MUST match j4, j5, j_unq_mid; MUST NOT match j3 (boundary test: 3 is in 1-3, not 3-5)
        r_35 = JobService.search_jobs(db_session, experience_range="3-5", page_size=100)
        titles_35 = {job.title for job in r_35.items}
        assert "Engineer 4 Year" in titles_35
        assert "Engineer 5 Year" in titles_35
        assert "Mid Dev" in titles_35
        assert "Engineer 3 Year" not in titles_35, "3.0 year boundary must be in 1-3, not 3-5"
        assert "Engineer 6 Year" not in titles_35, "6.0 years must not be in 3-5"
        assert "General Specialist" not in titles_35

        # 4. Range "5-8" -> MUST match j6, j8, j_unq_sr; MUST NOT match j5 (boundary test: 5 is in 3-5, not 5-8)
        r_58 = JobService.search_jobs(db_session, experience_range="5-8", page_size=100)
        titles_58 = {job.title for job in r_58.items}
        assert "Engineer 6 Year" in titles_58
        assert "Engineer 8 Year" in titles_58
        assert "Senior Dev" in titles_58
        assert "Engineer 5 Year" not in titles_58, "5.0 year boundary must be in 3-5, not 5-8"
        assert "Engineer 9 Year" not in titles_58, "9.0 years must not be in 5-8"
        assert "General Specialist" not in titles_58

        # 5. Range "8+" -> MUST match j9, j_unq_lead; MUST NOT match j8 (boundary test: 8 is in 5-8, not 8+)
        r_8p = JobService.search_jobs(db_session, experience_range="8+", page_size=100)
        titles_8p = {job.title for job in r_8p.items}
        assert "Engineer 9 Year" in titles_8p
        assert "Staff Dev" in titles_8p
        assert "Engineer 8 Year" not in titles_8p, "8.0 year boundary must be in 5-8, not 8+"
        assert "Engineer 6 Year" not in titles_8p
        assert "General Specialist" not in titles_8p

        # 6. Range "entry" -> MUST match j0, j1, j2, j_unq_entry; MUST NOT match j3, j4
        r_ent = JobService.search_jobs(db_session, experience_range="entry", page_size=100)
        titles_ent = {job.title for job in r_ent.items}
        assert "Engineer 0 Year" in titles_ent
        assert "Engineer 1 Year" in titles_ent
        assert "Engineer 2 Year" in titles_ent
        assert "Junior Dev" in titles_ent
        assert "Engineer 3 Year" not in titles_ent
        assert "General Specialist" not in titles_ent

        # 7. Range "internship" -> MUST match j_intern and j0
        r_int = JobService.search_jobs(db_session, experience_range="internship", page_size=100)
        titles_int = {job.title for job in r_int.items}
        assert "Summer Intern" in titles_int
        assert "Engineer 0 Year" in titles_int
        assert "Engineer 1 Year" not in titles_int
        assert "General Specialist" not in titles_int

        # 8. Range "unspecified" -> MUST strictly match j_unspecified; MUST NEVER match quantified or leveled jobs
        r_unsp = JobService.search_jobs(db_session, experience_range="unspecified", page_size=100)
        titles_unsp = {job.title for job in r_unsp.items}
        assert "General Specialist" in titles_unsp
        assert "Engineer 0 Year" not in titles_unsp
        assert "Engineer 1 Year" not in titles_unsp
        assert "Junior Dev" not in titles_unsp
        assert "Senior Dev" not in titles_unsp
        assert "Summer Intern" not in titles_unsp

    finally:
        for j in created_jobs:
            db_session.delete(j)
        db_session.commit()


# ============================================================================
# 2. COMPANY SEARCH AND VERIFIED ALIAS TESTS
# ============================================================================

def test_company_search_and_alias_resolution(db_session):
    """
    Verifies that company filtering and keyword searches correctly resolve
    canonical names and verified aliases (e.g. 'Scale' -> 'Scale AI', 'Stripe Payments' -> 'Stripe').
    """
    # 1. Alias dictionary verification
    assert COMPANY_ALIASES["scale"] == "Scale AI"
    assert COMPANY_ALIASES["canonical ltd"] == "Canonical"
    assert COMPANY_ALIASES["stripe payments"] == "Stripe"
    assert COMPANY_ALIASES["monzo bank"] == "Monzo"
    assert COMPANY_ALIASES["duolingo inc"] == "Duolingo"
    assert COMPANY_ALIASES["toast tab"] == "Toast"
    assert COMPANY_ALIASES["komodo health inc"] == "Komodo Health"
    assert COMPANY_ALIASES["on running"] == "On Running"

    # 2. Search by exact canonical name
    resp_stripe = JobService.search_jobs(db_session, company="Stripe")
    assert resp_stripe.total >= 0

    # 3. Search by alias
    resp_alias = JobService.search_jobs(db_session, company="Stripe Payments")
    assert resp_alias.total == resp_stripe.total

    # 4. Search via general keyword matching company alias
    resp_kw = JobService.search_jobs(db_session, keyword="Stripe Payments")
    assert resp_kw.total >= resp_stripe.total


# ============================================================================
# 3. JOB CATEGORIES & INDUSTRY FILTER TESTS
# ============================================================================

def test_job_categories_summary_and_filter(db_session):
    """
    Verifies category taxonomy endpoint and combined search filters.
    """
    # 1. Categories summary returns all defined taxonomy families with job counts
    res = JobService.get_categories_summary(db_session)
    assert "categories" in res
    assert "total_active_jobs" in res
    categories = res["categories"]
    assert len(categories) > 0

    cat_keys = [c["key"] for c in categories]
    assert "ENGINEERING" in cat_keys
    assert "DATA_AI" in cat_keys
    assert "HEALTHCARE_MEDICAL" in cat_keys
    assert "EDUCATION_TRAINING" in cat_keys

    for c in categories:
        assert "label" in c
        assert "active_jobs_count" in c
        assert isinstance(c["active_jobs_count"], int)
        assert c["active_jobs_count"] >= 0

    # 2. Filter by category
    resp_eng = JobService.search_jobs(db_session, category="Software Engineering and IT")
    assert isinstance(resp_eng.total, int)

    # 3. Combined filter: category + country_code + remote_type
    resp_comb = JobService.search_jobs(
        db_session,
        category="Software Engineering and IT",
        country_code="US",
        remote_type="REMOTE"
    )
    assert isinstance(resp_comb.total, int)
    for j in resp_comb.items:
        assert j.country_code == "US"
        assert j.remote_type == "REMOTE"


# ============================================================================
# 4. APPLICATION URL VERIFIER TESTS
# ============================================================================

def test_url_verifier_service_safety_and_classification():
    """
    Verifies that UrlVerifierService properly handles URL schemes, SSRF attacks,
    and HTTP status codes without ever crashing or fabricating data.
    """
    # 1. Invalid URLs / SSRF prevention
    res_empty = UrlVerifierService.verify_single_url("")
    assert res_empty["status"] == "INVALID_URL"

    res_js = UrlVerifierService.verify_single_url("javascript:alert(1)")
    assert res_js["status"] == "INVALID_URL"

    res_local = UrlVerifierService.verify_single_url("http://127.0.0.1:8000/internal")
    assert res_local["status"] == "INVALID_URL"

    res_priv = UrlVerifierService.verify_single_url("http://192.168.1.1/admin")
    assert res_priv["status"] == "INVALID_URL"

    res_meta = UrlVerifierService.verify_single_url("http://169.254.169.254/latest/meta-data")
    assert res_meta["status"] == "INVALID_URL"

    # 2. Mocked HTTP 200 (VALID)
    mock_200 = MagicMock()
    mock_200.status_code = 200
    mock_200.headers = {}
    mock_200.url = "https://boards.greenhouse.io/toast/jobs/12345"

    with patch("httpx.Client.head", return_value=mock_200):
        res = UrlVerifierService.verify_single_url("https://boards.greenhouse.io/toast/jobs/12345")
        assert res["status"] == "VALID"
        assert res["http_status"] == 200

    # 3. Mocked Redirected destination (REDIRECTED)
    mock_redir = MagicMock()
    mock_redir.status_code = 200
    mock_redir.headers = {}
    mock_redir.url = "https://careers.toasttab.com/jobs/12345"  # Changed URL from original

    with patch("httpx.Client.head", return_value=mock_redir):
        res = UrlVerifierService.verify_single_url("https://boards.greenhouse.io/toast/jobs/12345")
        assert res["status"] == "REDIRECTED"
        assert res["final_url"] == "https://careers.toasttab.com/jobs/12345"
        assert res["is_redirected"] is True

    # 4. Mocked HTTP 404 (CONFIRMED_BROKEN)
    mock_404 = MagicMock()
    mock_404.status_code = 404
    mock_404.headers = {}
    mock_404.url = "https://boards.greenhouse.io/toast/jobs/closed"

    with patch("httpx.Client.head", return_value=mock_404):
        with patch("httpx.Client.get", return_value=mock_404):
            res = UrlVerifierService.verify_single_url("https://boards.greenhouse.io/toast/jobs/closed")
            assert res["status"] == "CONFIRMED_BROKEN"
            assert res["http_status"] == 404

    # 5. Mocked HTTP 429 / 503 (TEMPORARILY_UNAVAILABLE - never marked broken!)
    mock_429 = MagicMock()
    mock_429.status_code = 429
    mock_429.headers = {"retry-after": "60"}
    mock_429.url = "https://boards.greenhouse.io/toast/jobs/busy"

    with patch("httpx.Client.head", return_value=mock_429):
        with patch("httpx.Client.get", return_value=mock_429):
            res = UrlVerifierService.verify_single_url("https://boards.greenhouse.io/toast/jobs/busy")
            assert res["status"] == "TEMPORARILY_UNAVAILABLE"
            assert res["http_status"] == 429
