import datetime
import pytest
from app.models import Source, Company, Job, IngestionRun
from app.ingestion.scheduler import IngestionScheduler
from app.ingestion.runner import IngestionRunner
from app.services.company_discovery import CompanyDiscoveryService
from app.services.job_service import JobService

def test_cron_interval_parsing():
    assert IngestionScheduler.parse_cron_interval_seconds("0 */4 * * *") == 14400
    assert IngestionScheduler.parse_cron_interval_seconds("0 */6 * * *") == 21600
    assert IngestionScheduler.parse_cron_interval_seconds("*/30 * * * *") == 1800
    assert IngestionScheduler.parse_cron_interval_seconds("0 2 * * *") == 86400
    assert IngestionScheduler.parse_cron_interval_seconds("") == 14400

def test_is_source_due_evaluation(db_session):
    # 1. Source never attempted is immediately due
    source = db_session.query(Source).first()
    assert source is not None

    source.last_attempted_at = None
    assert IngestionScheduler.is_source_due(source) is True

    # 2. Source attempted 1 minute ago with 4-hour schedule is NOT due
    now = datetime.datetime.now(datetime.timezone.utc)
    source.last_attempted_at = now - datetime.timedelta(minutes=1)
    source.sync_schedule_cron = "0 */4 * * *"
    assert IngestionScheduler.is_source_due(source, now=now) is False

    # 3. Source attempted 5 hours ago is due
    source.last_attempted_at = now - datetime.timedelta(hours=5)
    assert IngestionScheduler.is_source_due(source, now=now) is True

def test_stale_to_closed_transition_and_search_exclusion(db_session, client):
    # Setup test job that has been unseen for 20 days
    company = db_session.query(Company).first()
    source = db_session.query(Source).first()

    old_dt = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=20)
    stale_job = Job(
        company_id=company.id,
        source_id=source.id,
        external_job_id="test-stale-lifecycle-99",
        title="Legacy Obsolete Platform Architect",
        description="Old role that no longer exists.",
        location="Remote",
        remote_type="REMOTE",
        employment_type="FULL_TIME",
        first_seen_at=old_dt,
        last_seen_at=old_dt,
        last_verified_at=old_dt,
        status="POSSIBLY_STALE",
        application_url="https://example.com/apply/legacy",
        content_fingerprint="abc-legacy-fingerprint"
    )
    db_session.add(stale_job)
    db_session.commit()
    db_session.refresh(stale_job)

    # 1. Before expiration, searching includes POSSIBLY_STALE
    res_before = client.get("/api/v1/jobs?keyword=Legacy%20Obsolete")
    assert res_before.status_code == 200
    assert any(j["id"] == stale_job.id for j in res_before.json()["items"])

    # 2. Run expiration maintenance (cutoff 14 days)
    expired_count = IngestionRunner.expire_stale_jobs(db_session, grace_days=14)
    assert expired_count >= 1

    db_session.refresh(stale_job)
    assert stale_job.status == "CLOSED", "Job older than 14 days must transition to CLOSED"

    # 3. After expiration, default search excludes CLOSED job
    res_after = client.get("/api/v1/jobs?keyword=Legacy%20Obsolete")
    assert res_after.status_code == 200
    assert not any(j["id"] == stale_job.id for j in res_after.json()["items"])

    # 4. Clean up test record
    db_session.delete(stale_job)
    db_session.commit()

def test_company_discovery_probing():
    # Test valid Greenhouse probe
    probe_gh = CompanyDiscoveryService.probe_ats_board("airbnb")
    assert probe_gh["found"] is True
    assert probe_gh["source_type"] == "GREENHOUSE"
    assert probe_gh["sample_jobs_count"] > 0
    assert "https://boards.greenhouse.io/airbnb" in probe_gh["canonical_source_url"]

    # Test valid Ashby probe
    probe_ash = CompanyDiscoveryService.probe_ats_board("ramp")
    assert probe_ash["found"] is True
    assert probe_ash["source_type"] == "ASHBY"
    assert probe_ash["sample_jobs_count"] > 0

    # Test non-existent board
    probe_non = CompanyDiscoveryService.probe_ats_board("non_existent_company_handle_xyz_998811")
    assert probe_non["found"] is False
    assert probe_non["sample_jobs_count"] == 0

def test_admin_discovery_and_scheduler_endpoints(client, admin_token, db_session):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Probe endpoint
    res_probe = client.post("/api/v1/admin/sources/probe", headers=headers, json={"query": "airbnb"})
    assert res_probe.status_code == 200
    data_probe = res_probe.json()
    assert data_probe["found"] is True
    assert data_probe["source_type"] == "GREENHOUSE"

    # 2. Scheduler run endpoint
    res_sched = client.post("/api/v1/admin/scheduler/run?limit=2", headers=headers)
    assert res_sched.status_code == 200
    sched_data = res_sched.json()
    assert "sources_evaluated" in sched_data
    assert "stale_jobs_expired" in sched_data

    # 3. Stale expiration endpoint
    res_expire = client.post("/api/v1/admin/jobs/expire-stale?grace_days=14", headers=headers)
    assert res_expire.status_code == 200
    assert "expired_count" in res_expire.json()

    # Clean up test artifacts safely without deleting genuine or seeded jobs
    db_session.query(Job).filter(Job.external_job_id.like("test-%")).delete(synchronize_session=False)
    db_session.commit()

def test_checkpoint_persistence_on_runner(db_session):
    source = db_session.query(Source).first()
    assert source is not None

    # Simulate checkpoint storage
    run = IngestionRun(
        source_id=source.id,
        status="RUNNING",
        start_time=datetime.datetime.now(datetime.timezone.utc),
        pagination_checkpoint={"page": 3, "offset": 60}
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)

    assert run.pagination_checkpoint["page"] == 3
    assert run.pagination_checkpoint["offset"] == 60

    db_session.delete(run)
    db_session.commit()

def test_concurrent_sync_prevention(db_session):
    source = db_session.query(Source).first()
    assert source is not None

    # Simulate an active in-progress run
    active_run = IngestionRun(
        source_id=source.id,
        status="RUNNING",
        start_time=datetime.datetime.now(datetime.timezone.utc),
        pagination_checkpoint={}
    )
    db_session.add(active_run)
    db_session.commit()

    # Attempt to trigger a second sync concurrently
    with pytest.raises(RuntimeError) as exc_info:
        IngestionRunner.execute_sync(db_session, source.id)

    assert "already in progress" in str(exc_info.value)

    # Clean up
    db_session.delete(active_run)
    db_session.commit()

def test_failed_runs_do_not_expire_or_close_jobs(db_session):
    company = db_session.query(Company).first()
    assert company is not None

    now = datetime.datetime.now(datetime.timezone.utc)
    # Use a dedicated isolated test source to guarantee existing sources are never modified
    test_source = Source(
        company_id=company.id,
        source_name="Failure Resilience Test Source",
        source_type="GREENHOUSE",
        canonical_source_url="https://invalid-non-existent-domain-12345.xyz/api/fail",
        configuration={"board_token": "invalid_board_12345_nonexistent"},
        is_active=True
    )
    db_session.add(test_source)
    db_session.commit()
    db_session.refresh(test_source)

    test_job = Job(
        company_id=company.id,
        source_id=test_source.id,
        external_job_id="test-fail-resilience-job-99",
        title="Failure Isolation Verification Engineer",
        description="Testing that failed runs never expire or close jobs.",
        location="Remote",
        status="ACTIVE",
        application_url="https://example.com/apply/fail-resilience",
        first_seen_at=now,
        last_seen_at=now,
        last_verified_at=now,
        content_fingerprint="fp-test-fail-resilience-99"
    )
    db_session.add(test_job)
    db_session.commit()
    db_session.refresh(test_job)

    try:
        run = IngestionRunner.execute_sync(db_session, test_source.id)
        assert run.status == "FAILED"
        assert run.error_category in ["TRANSIENT", "PERMANENT", "RATE_LIMIT", "AUTHENTICATION", "PARSE"]

        # Verify active job was preserved and NOT expired or closed
        db_session.refresh(test_job)
        assert test_job.status == "ACTIVE", "Failed runs must never expire or close active jobs"
        assert test_job.last_seen_at == now
    finally:
        db_session.query(Job).filter(Job.source_id == test_source.id).delete()
        db_session.query(IngestionRun).filter(IngestionRun.source_id == test_source.id).delete()
        db_session.delete(test_source)
        db_session.commit()

def test_search_vector_database_trigger_synchronization(db_session):
    company = db_session.query(Company).first()
    source = db_session.query(Source).first()

    # 1. Insert a new job without setting search_vector manually
    new_job = Job(
        company_id=company.id,
        source_id=source.id,
        external_job_id="test-vector-sync-101",
        title="Principal Quantum Cryptography Engineer",
        description="Developing post-quantum lattice encryption systems.",
        department="Security",
        location="Zurich",
        remote_type="HYBRID",
        employment_type="FULL_TIME",
        status="ACTIVE",
        application_url="https://example.com/apply/quantum",
        content_fingerprint="fp-quantum-crypto"
    )
    db_session.add(new_job)
    db_session.commit()
    db_session.refresh(new_job)

    # PostgreSQL trigger should have populated search_vector
    assert new_job.search_vector is not None

    # 2. Update job title
    new_job.title = "Lead Quantum Lattice Security Architect"
    db_session.commit()
    db_session.refresh(new_job)

    # 3. Verify hybrid full-text search matches updated term
    search_res = JobService.search_jobs(db_session, keyword="Quantum Lattice")
    assert search_res.total >= 1
    assert any(j.id == new_job.id for j in search_res.items)

    # Clean up
    db_session.delete(new_job)
    db_session.commit()

def test_ingestion_idempotency_and_content_update(db_session, monkeypatch):
    """Verify stable external job IDs uniquely identify jobs, repeated syncs are idempotent,
    and changed content updates existing records correctly."""
    company = db_session.query(Company).first()
    test_source = Source(
        company_id=company.id,
        source_name="Test Idempotency Source",
        source_type="GENERIC_JSON",
        canonical_source_url="https://test-idempotency.example.com",
        configuration={"test": True},
        is_active=True
    )
    db_session.add(test_source)
    db_session.commit()
    db_session.refresh(test_source)

    class MockAdapter:
        def __init__(self, items):
            self.items = items
        def fetch_page(self, source_url, config, checkpoint):
            return self.items, {}, False
        def parse_and_normalize(self, raw):
            from app.ingestion.base import NormalizedJob
            return NormalizedJob(
                external_job_id=raw["id"],
                title=raw["title"],
                description=raw.get("desc", "Description"),
                application_url=raw.get("url", f"https://careers.acme-corp.com/jobs/{raw['id']}")
            )
        def classify_error(self, exc):
            return "TRANSIENT"

    try:
        # Run 1: Insert 2 jobs
        mock_data_1 = [
            {"id": "idemp-001", "title": "Staff Platform Architect", "desc": "Original text"},
            {"id": "idemp-002", "title": "Frontend Lead", "desc": "Original text 2"}
        ]
        monkeypatch.setattr(IngestionRunner, "get_adapter", lambda st: MockAdapter(mock_data_1))
        run_1 = IngestionRunner.execute_sync(db_session, test_source.id)
        assert run_1.status == "SUCCESS"
        assert run_1.records_inserted == 2
        assert run_1.records_updated == 0
        assert run_1.records_unchanged == 0

        # Run 2: Exact same data -> 100% idempotent
        run_2 = IngestionRunner.execute_sync(db_session, test_source.id)
        assert run_2.status == "SUCCESS"
        assert run_2.records_inserted == 0
        assert run_2.records_updated == 0
        assert run_2.records_unchanged == 2

        # Run 3: Modify idemp-001's title -> updates 1 record, unchanged 1
        mock_data_2 = [
            {"id": "idemp-001", "title": "Staff Platform Architect (Updated)", "desc": "Updated text"},
            {"id": "idemp-002", "title": "Frontend Lead", "desc": "Original text 2"}
        ]
        monkeypatch.setattr(IngestionRunner, "get_adapter", lambda st: MockAdapter(mock_data_2))
        run_3 = IngestionRunner.execute_sync(db_session, test_source.id)
        assert run_3.status == "SUCCESS"
        assert run_3.records_inserted == 0
        assert run_3.records_updated == 1
        assert run_3.records_unchanged == 1

        updated_job = db_session.query(Job).filter(Job.source_id == test_source.id, Job.external_job_id == "idemp-001").first()
        assert updated_job.title == "Staff Platform Architect (Updated)"
    finally:
        db_session.query(Job).filter(Job.source_id == test_source.id).delete()
        db_session.query(IngestionRun).filter(IngestionRun.source_id == test_source.id).delete()
        db_session.delete(test_source)
        db_session.commit()

def test_sudden_drop_triggers_anomaly_protection(db_session, monkeypatch):
    """Verify that sudden large drops in discovered jobs trigger anomaly protection
    rather than marking unseen jobs stale or closed."""
    company = db_session.query(Company).first()
    test_source = Source(
        company_id=company.id,
        source_name="Test Anomaly Source",
        source_type="GENERIC_JSON",
        canonical_source_url="https://test-anomaly.example.com",
        configuration={"test": True},
        is_active=True
    )
    db_session.add(test_source)
    db_session.commit()
    db_session.refresh(test_source)

    # Establish baseline run with 100 discovered jobs
    baseline_run = IngestionRun(
        source_id=test_source.id,
        status="SUCCESS",
        start_time=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2),
        end_time=datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=2),
        records_discovered=100,
        records_inserted=100
    )
    db_session.add(baseline_run)

    # Create 5 active jobs
    jobs = []
    for i in range(5):
        j = Job(
            company_id=company.id,
            source_id=test_source.id,
            external_job_id=f"test-anomaly-job-{i}",
            title=f"Test Anomaly Job {i}",
            description="Active job testing anomaly protection.",
            application_url=f"https://example.com/apply/{i}",
            content_fingerprint=f"fp-anomaly-{i}",
            status="ACTIVE"
        )
        db_session.add(j)
        jobs.append(j)
    db_session.commit()

    class DropAdapter:
        def fetch_page(self, source_url, config, checkpoint):
            # Only returns 1 job out of the previous 100 (99% drop)
            return [{"id": "test-anomaly-job-0", "title": "Test Anomaly Job 0"}], {}, False
        def parse_and_normalize(self, raw):
            from app.ingestion.base import NormalizedJob
            return NormalizedJob(
                external_job_id=raw["id"],
                title=raw["title"],
                description="Active job testing anomaly protection.",
                application_url=f"https://careers.acme-corp.com/apply/0"
            )
        def classify_error(self, exc):
            return "TRANSIENT"

    try:
        monkeypatch.setattr(IngestionRunner, "get_adapter", lambda st: DropAdapter())
        drop_run = IngestionRunner.execute_sync(db_session, test_source.id)

        assert drop_run.status == "ANOMALY_QUARANTINE"
        assert drop_run.anomaly_detected is True
        assert "Sudden sharp drop" in str(drop_run.anomaly_details)

        # Confirm all 5 jobs are STILL ACTIVE and NONE were marked POSSIBLY_STALE
        for j in jobs:
            db_session.refresh(j)
            assert j.status == "ACTIVE", f"Job {j.external_job_id} should remain ACTIVE during anomaly quarantine"
    finally:
        db_session.query(Job).filter(Job.source_id == test_source.id).delete()
        db_session.query(IngestionRun).filter(IngestionRun.source_id == test_source.id).delete()
        db_session.delete(test_source)
        db_session.commit()
