import pytest
from app.ingestion.anomaly import AnomalyDetector
from app.models import Source, Company, IngestionRun

def test_anomaly_detector_high_rejection(db_session):
    source = db_session.query(Source).first()
    assert source is not None

    # High rejection: 5 discovered, 4 rejected
    is_anomaly, details = AnomalyDetector.evaluate_run(
        db=db_session,
        source=source,
        discovered_count=5,
        rejected_count=4,
        inserted_count=1,
        updated_count=0,
        unchanged_count=0
    )
    assert is_anomaly is True
    assert "High parsing rejection rate" in details["reasons"][0]

def test_admin_sources_api(client, admin_token):
    headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. List sources
    list_res = client.get("/api/v1/admin/sources", headers=headers)
    assert list_res.status_code == 200
    sources = list_res.json()
    assert len(sources) >= 1

    # 2. System Health
    health_res = client.get("/api/v1/admin/health", headers=headers)
    assert health_res.status_code == 200
    health_data = health_res.json()
    assert health_data["database_connected"] is True
    assert health_data["total_sources"] >= 1
    assert health_data["total_jobs"] >= 1

    # 3. Ingestion Runs list
    runs_res = client.get("/api/v1/admin/ingestion-runs", headers=headers)
    assert runs_res.status_code == 200
    runs = runs_res.json()
    assert isinstance(runs, list)

def test_non_admin_forbidden_on_admin_endpoints(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # Candidate user must receive 403 Forbidden
    res = client.get("/api/v1/admin/sources", headers=headers)
    assert res.status_code == 403
    assert "Administrative privileges required" in res.json()["detail"]

    sync_res = client.post("/api/v1/admin/sources/1/sync", headers=headers)
    assert sync_res.status_code == 403

    health_res = client.get("/api/v1/admin/health", headers=headers)
    assert health_res.status_code == 403
