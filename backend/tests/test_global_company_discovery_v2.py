import pytest
from app.models import Company, Source, Job
from app.discovery.normalizer import clean_company_name, extract_canonical_domain, is_duplicate_company
from app.discovery.connectors.sec_edgar import SecEdgarConnector
from app.discovery.connectors.open_directory import OpenDirectoryConnector
from app.discovery.connectors.ats_directory import PublicAtsDirectoryConnector
from app.discovery.connectors.global_enterprise import GlobalEnterpriseConnector
from app.discovery.verifier import CompanyVerifierService
from app.discovery.worker import CompanyDiscoveryService
from app.services.job_service import JobService

def test_clean_company_name_normalization():
    # Test stripping common legal suffixes
    assert clean_company_name("APPLE INC") == "Apple"
    assert clean_company_name("MICROSOFT CORP") == "Microsoft"
    assert clean_company_name("AMAZON COM INC") == "Amazon"
    assert clean_company_name("Spotify AB") == "Spotify"
    assert clean_company_name("Zalando SE") == "Zalando"
    assert clean_company_name("Siemens AG") == "Siemens"
    assert clean_company_name("Atlassian Pty Ltd") == "Atlassian"
    assert clean_company_name("Meta Platforms Inc.") == "Meta"
    assert clean_company_name("Alphabet Inc.") == "Google"

def test_extract_canonical_domain():
    # Test domain parsing including subdomains and second-level TLDs
    assert extract_canonical_domain("https://careers.stripe.com/jobs") == "stripe.com"
    assert extract_canonical_domain("http://www.google.co.uk/search") == "google.co.uk"
    assert extract_canonical_domain("https://jobs.lever.co/spotify") == "lever.co"
    assert extract_canonical_domain("https://apply.canva.com.au/openings") == "canva.com.au"
    assert extract_canonical_domain("https://sub.sub2.company.co.jp") == "company.co.jp"
    assert extract_canonical_domain("invalid-domain") == "invalid-domain"
    assert extract_canonical_domain(None) is None

def test_duplicate_company_prevention(db_session):
    # Ensure baseline company
    existing = db_session.query(Company).filter(Company.canonical_name == "Stripe").first()
    if not existing:
        existing = Company(
            canonical_name="Stripe",
            website="https://stripe.com",
            domain="stripe.com",
            identity_status="VERIFIED"
        )
        db_session.add(existing)
        db_session.commit()

    # 1. Duplicate by exact name
    dup1 = is_duplicate_company(db_session, name="Stripe")
    assert dup1 is not None
    assert dup1.id == existing.id

    # 2. Duplicate by raw legal name
    dup2 = is_duplicate_company(db_session, name="Stripe Inc.")
    assert dup2 is not None
    assert dup2.id == existing.id

    # 3. Duplicate by domain
    dup3 = is_duplicate_company(db_session, name="Stripe Payments", domain="https://careers.stripe.com")
    assert dup3 is not None
    assert dup3.id == existing.id

    # 4. Distinct company is not marked duplicate
    distinct = is_duplicate_company(db_session, name="Completely Unique Startup Ltd", domain="unique-startup-12345.io")
    assert distinct is None

def test_company_tiered_status_transitions(db_session):
    # Create test company in DISCOVERED tier
    test_comp = Company(
        canonical_name="Test Company Alpha",
        domain="alpha-test-corp-999.com",
        verification_status="DISCOVERED",
        identity_status="VERIFIED"
    )
    db_session.add(test_comp)
    db_session.commit()
    db_session.refresh(test_comp)

    assert test_comp.verification_status == "DISCOVERED"

    # Transition to DOMAIN_VERIFIED
    test_comp.verification_status = "DOMAIN_VERIFIED"
    assert test_comp.verification_status == "DOMAIN_VERIFIED"

    # Transition to CAREER_PAGE_FOUND
    test_comp.career_page_url = "https://alpha-test-corp-999.com/careers"
    test_comp.verification_status = "CAREER_PAGE_FOUND"
    assert test_comp.verification_status == "CAREER_PAGE_FOUND"

    # Transition to SOURCE_VERIFIED
    test_comp.ats_provider = "GREENHOUSE"
    test_comp.ats_board_id = "testalpha"
    test_comp.verification_status = "SOURCE_VERIFIED"
    assert test_comp.verification_status == "SOURCE_VERIFIED"

    # Evaluate vacancy: no active jobs yet -> NO_CURRENT_VACANCIES
    status = CompanyVerifierService.evaluate_active_vacancies(db_session, test_comp)
    assert status in ["SOURCE_VERIFIED", "NO_CURRENT_VACANCIES"]

    # Transition to UNSUPPORTED if site is dead or blocked
    test_comp.verification_status = "UNSUPPORTED"
    test_comp.verification_notes = "Domain expired or blocked by Cloudflare challenge"
    db_session.commit()

    reloaded = db_session.query(Company).filter(Company.id == test_comp.id).first()
    assert reloaded.verification_status == "UNSUPPORTED"
    assert "Cloudflare" in reloaded.verification_notes

    # Clean up test artifact
    db_session.delete(reloaded)
    db_session.commit()

def test_discovery_connectors_candidate_generation():
    # 1. ATS Directory Connector
    ats_conn = PublicAtsDirectoryConnector()
    ats_candidates = ats_conn.discover(limit=10)
    assert len(ats_candidates) > 0
    assert any(c.ats_provider in ["GREENHOUSE", "LEVER", "ASHBY", "SMARTRECRUITERS"] for c in ats_candidates)

    # 2. Global Enterprise Connector
    ent_conn = GlobalEnterpriseConnector()
    ent_candidates = ent_conn.discover(limit=10)
    assert len(ent_candidates) > 0
    assert any(c.operating_region in ["Europe", "North America", "Asia", "South America", "Global"] for c in ent_candidates)

def test_admin_discovery_endpoints(client, admin_token):
    admin_token_headers = {"Authorization": f"Bearer {admin_token}"}
    # Test GET /api/v1/admin/discovery/summary
    res = client.get("/api/v1/admin/discovery/summary", headers=admin_token_headers)
    assert res.status_code == 200
    data = res.json()
    assert "total_companies" in data
    assert "tiers" in data
    assert "DISCOVERED" in data["tiers"]
    assert "DOMAIN_VERIFIED" in data["tiers"]
    assert "ACTIVE_JOB_SOURCE" in data["tiers"]

    # Test GET /api/v1/admin/discovery/companies
    res_list = client.get("/api/v1/admin/discovery/companies?page=1&page_size=10", headers=admin_token_headers)
    assert res_list.status_code == 200
    list_data = res_list.json()
    assert "items" in list_data
    assert "total" in list_data

    # Test PATCH /api/v1/admin/discovery/companies/{id}/status
    test_comp = client.app.state = None # check against first company in list
    first_comp = list_data["items"][0]
    comp_id = first_comp["id"]

    res_patch = client.patch(
        f"/api/v1/admin/discovery/companies/{comp_id}/status",
        json={"verification_status": "DOMAIN_VERIFIED", "verification_notes": "Admin audit approval test"},
        headers=admin_token_headers
    )
    assert res_patch.status_code == 200
    patched_data = res_patch.json()
    assert patched_data["verification_status"] == "DOMAIN_VERIFIED"
