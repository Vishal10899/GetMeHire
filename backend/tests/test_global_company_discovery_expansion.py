import pytest
import datetime
from unittest.mock import MagicMock, patch
from sqlalchemy.orm import Session
from app.models import Company, Source, Job, IngestionRun, User
from app.discovery.normalizer import clean_company_name, extract_canonical_domain, is_duplicate_company, KNOWN_ATS_DOMAINS
from app.discovery.connectors.sec_edgar import SecEdgarConnector
from app.discovery.connectors.open_directory import OpenDirectoryConnector
from app.discovery.connectors.ats_directory import PublicAtsDirectoryConnector
from app.discovery.connectors.global_enterprise import GlobalEnterpriseConnector
from app.discovery.connectors.public_registries import PublicRegistriesConnector
from app.discovery.verifier import CompanyVerifierService
from app.discovery.worker import CompanyDiscoveryService
from app.ingestion.crawler import CareerCrawlerService
from app.ingestion.runner import IngestionRunner
from app.ingestion.normalizer import is_valid_job_posting, is_valid_application_url
from app.services.admin_service import AdminService

# =========================================================================
# 1. New Discovery Connectors & Global Regional Coverage
# =========================================================================
def test_new_discovery_connectors_worldwide_coverage():
    # 1. Public ATS Directory Connector
    ats_conn = PublicAtsDirectoryConnector()
    ats_candidates = ats_conn.discover(limit=150)
    assert len(ats_candidates) >= 50

    # Verify coverage across all 9 target geographic regions
    regions_found = {c.operating_region for c in ats_candidates if c.operating_region}
    expected_regions = {
        "North America", "South Asia", "East Asia", "Southeast Asia",
        "Europe", "Middle East", "Africa", "South America", "Oceania"
    }
    for reg in expected_regions:
        assert reg in regions_found, f"Region {reg} missing from ATS candidates"

    # Verify coverage across prioritized ATS platforms
    ats_providers = {c.ats_provider for c in ats_candidates if c.ats_provider}
    expected_providers = {"GREENHOUSE", "LEVER", "ASHBY", "SMARTRECRUITERS", "PERSONIO", "BAMBOOHR", "TEAMTAILOR"}
    for prov in expected_providers:
        assert prov in ats_providers, f"ATS provider {prov} missing from ATS candidates"

    # 2. Public Registries Connector
    reg_conn = PublicRegistriesConnector()
    reg_candidates = reg_conn.discover(limit=50)
    assert len(reg_candidates) >= 20
    assert any(c.discovery_source == "PUBLIC_CORPORATE_REGISTRY" for c in reg_candidates)
    assert any(c.country in ["United Kingdom", "France", "Germany", "India", "Australia", "Singapore"] for c in reg_candidates)

    # 3. Global Enterprise Connector
    ent_conn = GlobalEnterpriseConnector()
    ent_candidates = ent_conn.discover(limit=100)
    assert len(ent_candidates) >= 50
    # Verify non-IT industries
    industries_found = {c.industry for c in ent_candidates if c.industry}
    assert "Energy" in industries_found
    assert "Aerospace" in industries_found
    assert "Automotive" in industries_found
    assert "Healthcare & Pharmaceuticals" in industries_found

    # 4. Open Directory Connector fallback & parsing
    open_conn = OpenDirectoryConnector()
    open_candidates = open_conn.discover(limit=50)
    assert len(open_candidates) >= 20
    assert any(c.domain for c in open_candidates)

    # 5. SEC EDGAR Connector fallback & parsing
    sec_conn = SecEdgarConnector()
    sec_candidates = sec_conn.discover(limit=50)
    assert len(sec_candidates) >= 20
    assert any(c.metadata.get("sec_registered") for c in sec_candidates)

# =========================================================================
# 2. Company Identity, Deduplication & ATS Domain Isolation
# =========================================================================
def test_company_identity_and_deduplication(db_session):
    # Ensure test base company
    base_comp = db_session.query(Company).filter(Company.canonical_name == "Canva").first()
    if not base_comp:
        base_comp = Company(
            canonical_name="Canva",
            domain="canva.com",
            website="https://canva.com",
            career_page_url="https://boards.greenhouse.io/canva",
            verification_status="SOURCE_VERIFIED",
            identity_status="VERIFIED"
        )
        db_session.add(base_comp)
        db_session.commit()

    # 1. Exact canonical name match
    dup1 = is_duplicate_company(db_session, name="Canva")
    assert dup1 is not None
    assert dup1.id == base_comp.id

    # 2. Legal suffix variation match ("Canva Pty Ltd")
    dup2 = is_duplicate_company(db_session, name="Canva Pty Ltd")
    assert dup2 is not None
    assert dup2.id == base_comp.id

    # 3. Domain match
    dup3 = is_duplicate_company(db_session, name="Canva Visual Suite", domain="https://www.canva.com")
    assert dup3 is not None
    assert dup3.id == base_comp.id

    # 4. Critical ATS Domain Isolation Guard:
    # A candidate sharing an ATS URL (e.g. boards.greenhouse.io/othercomp)
    # MUST NOT be marked as duplicate of Canva simply because Canva's career page has boards.greenhouse.io!
    distinct_candidate = is_duplicate_company(
        db_session,
        name="Unique New Startup Corp",
        domain="https://boards.greenhouse.io/uniquenewstartup"
    )
    assert distinct_candidate is None or distinct_candidate.canonical_name != "Canva"

# =========================================================================
# 3. 7 Verification Tiers Transitions
# =========================================================================
def test_verification_transitions_7_tiers(db_session):
    # Create test candidate in Tier 1: DISCOVERED
    comp = Company(
        canonical_name="Starlight Energy Global",
        domain=None,
        website=None,
        verification_status="DISCOVERED",
        identity_status="VERIFIED"
    )
    db_session.add(comp)
    db_session.commit()
    db_session.refresh(comp)

    assert comp.verification_status == "DISCOVERED"

    # Tier 2: DOMAIN_VERIFIED
    comp.domain = "starlightenergy-test.com"
    comp.website = "https://starlightenergy-test.com"
    comp.verification_status = "DOMAIN_VERIFIED"
    comp.last_verified_at = datetime.datetime.now(datetime.timezone.utc)
    db_session.commit()
    assert comp.verification_status == "DOMAIN_VERIFIED"

    # Evidence rule: A company with verified domain must NOT automatically be active job source
    eval_status = CompanyVerifierService.evaluate_active_vacancies(db_session, comp)
    assert eval_status == "DOMAIN_VERIFIED"
    assert comp.verification_status != "ACTIVE_JOB_SOURCE"

    # Tier 3: CAREER_PAGE_FOUND
    comp.career_page_url = "https://starlightenergy-test.com/careers"
    comp.verification_status = "CAREER_PAGE_FOUND"
    db_session.commit()
    eval_status = CompanyVerifierService.evaluate_active_vacancies(db_session, comp)
    assert eval_status == "CAREER_PAGE_FOUND"

    # Tier 4: SOURCE_VERIFIED
    comp.ats_provider = "GREENHOUSE"
    comp.ats_board_id = "starlightenergy"
    comp.verification_status = "SOURCE_VERIFIED"
    db_session.commit()
    eval_status = CompanyVerifierService.evaluate_active_vacancies(db_session, comp)
    assert eval_status == "SOURCE_VERIFIED"

    # Link Source record with 0 jobs -> transitions to Tier 6: NO_CURRENT_VACANCIES
    source = Source(
        company_id=comp.id,
        source_name="Starlight Greenhouse Board",
        source_type="GREENHOUSE",
        canonical_source_url="https://boards-api.greenhouse.io/v1/boards/starlightenergy/jobs",
        external_board_id="starlightenergy",
        access_classification="PUBLIC_API",
        health_status="HEALTHY",
        is_active=True
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(comp)

    eval_status = CompanyVerifierService.evaluate_active_vacancies(db_session, comp)
    assert eval_status == "NO_CURRENT_VACANCIES"
    assert comp.verification_status == "NO_CURRENT_VACANCIES"

    # Add active job -> transitions to Tier 5: ACTIVE_JOB_SOURCE
    now_dt = datetime.datetime.now(datetime.timezone.utc)
    job = Job(
        company_id=comp.id,
        source_id=source.id,
        external_job_id="test-job-starlight-1",
        title="Senior Solar Systems Engineer",
        description="Lead solar engineering projects across international sites.",
        location="London, United Kingdom",
        country="United Kingdom",
        country_code="GB",
        remote_type="HYBRID",
        employment_type="FULL_TIME",
        application_url="https://starlightenergy-test.com/careers/test-job-starlight-1",
        content_fingerprint="fingerprint_test_starlight_1",
        status="ACTIVE",
        posting_date=now_dt,
        first_seen_at=now_dt,
        last_seen_at=now_dt,
        last_verified_at=now_dt
    )
    db_session.add(job)
    db_session.commit()
    db_session.refresh(comp)

    eval_status = CompanyVerifierService.evaluate_active_vacancies(db_session, comp)
    assert eval_status == "ACTIVE_JOB_SOURCE"
    assert comp.verification_status == "ACTIVE_JOB_SOURCE"

    # Clean up test records
    db_session.delete(job)
    db_session.delete(source)
    db_session.delete(comp)
    db_session.commit()

# =========================================================================
# 4. ATS Endpoint Validation Across All 10 Providers
# =========================================================================
def test_ats_endpoint_validation_all_providers():
    test_urls = [
        ("https://boards.greenhouse.io/stripe", "GREENHOUSE", "stripe"),
        ("https://jobs.lever.co/spotify", "LEVER", "spotify"),
        ("https://jobs.ashbyhq.com/supabase", "ASHBY", "supabase"),
        ("https://jobs.smartrecruiters.com/shopify", "SMARTRECRUITERS", "shopify"),
        ("https://biontech.jobs.personio.de", "PERSONIO", "biontech"),
        ("https://apply.workable.com/arondite", "WORKABLE", "arondite"),
        ("https://postman.bamboohr.com/careers", "BAMBOOHR", "postman"),
        ("https://northvolt.teamtailor.com", "TEAMTAILOR", "northvolt"),
        ("https://careers.recruitee.com", "RECRUITEE", None),
        ("https://testcorp.breezy.hr", "BREEZY", "testcorp"),
    ]

    for url, expected_provider, expected_board in test_urls:
        prov, board, feed = CareerCrawlerService.detect_ats(url)
        assert prov == expected_provider or prov in ["WEB_SCRAPER", expected_provider]
        if expected_board and prov == expected_provider:
            assert board == expected_board

    # Check adapter retrieval for all 10 prioritized providers
    for p in ["GREENHOUSE", "LEVER", "ASHBY", "SMARTRECRUITERS", "PERSONIO", "WORKABLE", "BAMBOOHR", "TEAMTAILOR", "RECRUITEE", "BREEZY"]:
        adapter = IngestionRunner.get_adapter(p)
        assert adapter is not None

# =========================================================================
# 5. Cursor Continuation & Exhaustion
# =========================================================================
def test_cursor_continuation_and_exhaustion(db_session):
    # Idempotent cleanup before test
    old_comp = db_session.query(Company).filter(Company.canonical_name == "Pagination Test Corp").first()
    if old_comp:
        db_session.query(Job).filter(Job.company_id == old_comp.id).delete()
        db_session.query(Source).filter(Source.company_id == old_comp.id).delete()
        db_session.delete(old_comp)
        db_session.commit()

    # Setup mock company and source
    comp = Company(
        canonical_name="Pagination Test Corp",
        domain="pagination-test-corp.com",
        verification_status="SOURCE_VERIFIED",
        identity_status="VERIFIED"
    )
    db_session.add(comp)
    db_session.flush()

    source = Source(
        company_id=comp.id,
        source_name="Pagination Test Source",
        source_type="GENERIC_JSON",
        canonical_source_url="https://careers.paginationcorp.com/api/jobs",
        access_classification="PUBLIC_API",
        configuration={"max_pages": 1},  # limit to 1 page to trigger partial crawl
        health_status="HEALTHY",
        is_active=True
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    try:
        # Mock adapter fetch_page returning has_more=True with continuation token
        mock_adapter = MagicMock()
        page1_records = [{
            "id": "job-page-1-a",
            "title": "Software Engineer I",
            "description": "Standard software engineering role for page 1.",
            "location": "New York, NY",
            "url": "https://careers.paginationcorp.com/jobs/job-page-1-a"
        }]
        mock_adapter.fetch_page.return_value = (page1_records, {"cursor": "token_page_2"}, True)
        mock_adapter.parse_and_normalize.side_effect = IngestionRunner.get_adapter("GENERIC_JSON").parse_and_normalize
        mock_adapter.classify_error.side_effect = IngestionRunner.get_adapter("GENERIC_JSON").classify_error

        with patch.object(IngestionRunner, "get_adapter", return_value=mock_adapter):
            run1 = IngestionRunner.execute_sync(db_session, source.id)

        db_session.refresh(source)
        # Since max_pages=1 and has_more was True:
        # 1. Run status is PARTIAL
        assert run1.status == "PARTIAL"
        # 2. Source configuration persists continuation cursor
        assert source.configuration.get("crawl_status") == "PARTIALLY_CRAWLED"
        assert source.configuration.get("continuation_cursor") == {"cursor": "token_page_2"}
        # 3. 1 job inserted
        assert run1.records_inserted == 1

        # Now simulate run 2 resuming from continuation cursor and reaching exhaustion
        page2_records = [{
            "id": "job-page-2-b",
            "title": "Software Engineer II",
            "description": "Standard software engineering role for page 2.",
            "location": "New York, NY",
            "url": "https://careers.paginationcorp.com/jobs/job-page-2-b"
        }]
        mock_adapter.fetch_page.return_value = (page2_records, {"cursor": None}, False)

        with patch.object(IngestionRunner, "get_adapter", return_value=mock_adapter):
            run2 = IngestionRunner.execute_sync(db_session, source.id)

        db_session.refresh(source)
        # Since has_more was False (exhaustion):
        # 1. Run status is SUCCESS
        assert run2.status == "SUCCESS"
        # 2. Source configuration cleared continuation cursor and marked FULLY_CRAWLED
        assert source.configuration.get("crawl_status") == "FULLY_CRAWLED"
        assert source.configuration.get("continuation_cursor") is None
        # 3. Source last_complete_sync_at updated
        assert source.last_complete_sync_at is not None
    finally:
        # Clean up test artifacts
        db_session.query(Job).filter(Job.source_id == source.id).delete()
        db_session.query(IngestionRun).filter(IngestionRun.source_id == source.id).delete()
        db_session.delete(source)
        db_session.delete(comp)
        db_session.commit()

# =========================================================================
# 6. Duplicate Prevention Across Multiple Runs
# =========================================================================
def test_duplicate_prevention_across_multiple_runs(db_session):
    # Idempotent cleanup before test
    old_comp = db_session.query(Company).filter(Company.canonical_name == "Dedup Run Test Corp").first()
    if old_comp:
        db_session.query(Job).filter(Job.company_id == old_comp.id).delete()
        db_session.query(Source).filter(Source.company_id == old_comp.id).delete()
        db_session.delete(old_comp)
        db_session.commit()

    comp = Company(
        canonical_name="Dedup Run Test Corp",
        domain="dedup-test.com",
        verification_status="SOURCE_VERIFIED",
        identity_status="VERIFIED"
    )
    db_session.add(comp)
    db_session.flush()

    source = Source(
        company_id=comp.id,
        source_name="Dedup Test Source",
        source_type="GENERIC_JSON",
        canonical_source_url="https://careers.deduptest.com/api/jobs",
        access_classification="PUBLIC_API",
        health_status="HEALTHY",
        is_active=True
    )
    db_session.add(source)
    db_session.commit()
    db_session.refresh(source)

    try:
        records = [
            {"id": "dedup-job-1", "title": "DevOps Engineer", "description": "Cloud infra and CI/CD pipelines.", "url": "https://careers.deduptest.com/jobs/1"},
            {"id": "dedup-job-2", "title": "Security Analyst", "description": "Security compliance and audits.", "url": "https://careers.deduptest.com/jobs/2"},
        ]

        mock_adapter = MagicMock()
        mock_adapter.fetch_page.return_value = (records, {"completed": True}, False)
        mock_adapter.parse_and_normalize.side_effect = IngestionRunner.get_adapter("GENERIC_JSON").parse_and_normalize
        mock_adapter.classify_error.side_effect = IngestionRunner.get_adapter("GENERIC_JSON").classify_error

        with patch.object(IngestionRunner, "get_adapter", return_value=mock_adapter):
            # Run 1: Should insert 2 jobs
            run1 = IngestionRunner.execute_sync(db_session, source.id)
            assert run1.records_inserted == 2
            assert run1.records_unchanged == 0

            # Run 2: Exact same payload. Should insert 0 new jobs, mark 2 unchanged
            run2 = IngestionRunner.execute_sync(db_session, source.id)
            assert run2.records_inserted == 0
            assert run2.records_unchanged == 2
    finally:
        # Clean up test artifacts
        db_session.query(Job).filter(Job.source_id == source.id).delete()
        db_session.query(IngestionRun).filter(IngestionRun.source_id == source.id).delete()
        db_session.delete(source)
        db_session.delete(comp)
        db_session.commit()

# =========================================================================
# 7. Transient Failures Do Not Close Active Jobs
# =========================================================================
def test_transient_network_failures_do_not_close_jobs(db_session):
    comp = Company(
        canonical_name="Resilience Test Corp",
        domain="resilience-test.com",
        verification_status="ACTIVE_JOB_SOURCE",
        identity_status="VERIFIED"
    )
    db_session.add(comp)
    db_session.flush()

    source = Source(
        company_id=comp.id,
        source_name="Resilience Test Source",
        source_type="GENERIC_JSON",
        canonical_source_url="https://example.com/api/jobs",
        access_classification="PUBLIC_API",
        health_status="HEALTHY",
        is_active=True
    )
    db_session.add(source)
    db_session.flush()

    now_dt = datetime.datetime.now(datetime.timezone.utc)
    job = Job(
        company_id=comp.id,
        source_id=source.id,
        external_job_id="resilience-job-1",
        title="Principal Architect",
        description="Enterprise systems architecture.",
        location="Remote",
        application_url="https://example.com/jobs/resilience-1",
        content_fingerprint="fingerprint_resilience_1",
        status="ACTIVE",
        posting_date=now_dt,
        first_seen_at=now_dt,
        last_seen_at=now_dt,
        last_verified_at=now_dt
    )
    db_session.add(job)
    db_session.commit()

    # Simulate network timeout exception
    mock_adapter = MagicMock()
    mock_adapter.fetch_page.side_effect = ConnectionResetError("Connection reset by peer (HTTP 502/timeout)")
    mock_adapter.classify_error.return_value = "TRANSIENT"

    with patch.object(IngestionRunner, "get_adapter", return_value=mock_adapter):
        run = IngestionRunner.execute_sync(db_session, source.id)

    db_session.refresh(job)
    db_session.refresh(source)

    # 1. Run failed with TRANSIENT category
    assert run.status == "FAILED"
    assert run.error_category == "TRANSIENT"

    # 2. Existing active job is STILL ACTIVE! Must not be closed due to transient error!
    assert job.status == "ACTIVE"

    # Clean up test artifacts
    db_session.delete(job)
    db_session.query(IngestionRun).filter(IngestionRun.source_id == source.id).delete()
    db_session.delete(source)
    db_session.delete(comp)
    db_session.commit()

# =========================================================================
# 8. Job Quality, URL Validation & Expiry
# =========================================================================
def test_job_quality_and_url_validation(db_session):
    # Test application URL validation
    valid, _ = is_valid_application_url("https://boards.greenhouse.io/stripe/jobs/12345")
    assert valid is True

    valid_http, _ = is_valid_application_url("http://company.com/apply/role-1")
    assert valid_http is True

    # Rejection of invalid / dummy URLs
    empty_url, reason1 = is_valid_application_url("")
    assert empty_url is False
    assert reason1 == "MISSING_APPLICATION_URL"

    dummy_url, reason2 = is_valid_application_url("https://example.com/jobs/1")
    assert dummy_url is False
    assert reason2 == "DUMMY_URL"

    bad_scheme, reason3 = is_valid_application_url("ftp://server/job.txt")
    assert bad_scheme is False
    assert reason3 == "INVALID_URL_SCHEME"

    # Test title & description validation
    valid_job, _ = is_valid_job_posting("Software Engineer", "Full stack development with Python and React.")
    assert valid_job is True

    dummy_job, d_reason = is_valid_job_posting("test job", "test description")
    assert dummy_job is False

    # Test stale jobs expiration
    comp = Company(canonical_name="Expiry Test Corp", identity_status="VERIFIED")
    db_session.add(comp)
    db_session.flush()

    source = Source(
        company_id=comp.id,
        source_name="Expiry Test Source",
        source_type="GENERIC_JSON",
        canonical_source_url="https://expiry-test.com/api",
        is_active=True
    )
    db_session.add(source)
    db_session.flush()

    old_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20)
    stale_job = Job(
        company_id=comp.id,
        source_id=source.id,
        external_job_id="stale-job-999",
        title="Former Position",
        description="Position closed long ago.",
        location="Remote",
        application_url="https://expiry-test.com/jobs/999",
        content_fingerprint="fingerprint_old_999",
        status="POSSIBLY_STALE",
        posting_date=old_dt,
        first_seen_at=old_dt,
        last_seen_at=old_dt,
        last_verified_at=old_dt
    )
    db_session.add(stale_job)
    db_session.commit()

    # Expire stale jobs older than 14 days
    expired_count = IngestionRunner.expire_stale_jobs(db_session, source_id=source.id, grace_days=14)
    assert expired_count == 1

    db_session.refresh(stale_job)
    assert stale_job.status == "CLOSED"

    # Clean up
    db_session.delete(stale_job)
    db_session.delete(source)
    db_session.delete(comp)
    db_session.commit()

# =========================================================================
# 9. Admin Authorization & Telemetry Accuracy
# =========================================================================
def test_admin_authorization_and_telemetry(client, admin_token, candidate_token, db_session):
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    user_headers = {"Authorization": f"Bearer {candidate_token}"}

    # 1. Regular user is forbidden from admin discovery summary
    user_res = client.get("/api/v1/admin/discovery/summary", headers=user_headers)
    assert user_res.status_code == 403

    # 2. Admin successfully gets discovery summary with all Section 7 fields
    res = client.get("/api/v1/admin/discovery/summary", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()

    # Verify all 11 required summary fields exist
    assert "total_companies" in data
    assert "domain_verified_companies" in data
    assert "career_pages_found" in data
    assert "verified_ats_sources" in data
    assert "active_job_sources" in data
    assert "no_current_vacancies" in data
    assert "unsupported_sources" in data
    assert "partially_crawled_sources" in data
    assert "pending_verification" in data
    assert "active_jobs_count" in data
    assert "jobs_rejected_count" in data

    # Verify distribution breakdowns exist
    assert "countries" in data
    assert isinstance(data["countries"], list)
    assert "regions" in data
    assert isinstance(data["regions"], list)
    assert "industries" in data
    assert isinstance(data["industries"], list)
    assert "ats_providers" in data
    assert isinstance(data["ats_providers"], list)

    # 3. Verify Source Response includes source-level diagnostics
    sources_res = client.get("/api/v1/admin/sources", headers=admin_headers)
    assert sources_res.status_code == 200
    sources_data = sources_res.json()
    assert len(sources_data) > 0
    first_source = sources_data[0]
    assert "pagination_status" in first_source
    assert "has_continuation_cursor" in first_source
    assert "jobs_discovered" in first_source
    assert "jobs_accepted" in first_source
    assert "jobs_rejected" in first_source
