import pytest

def test_saved_jobs_lifecycle(client, candidate_token):
    headers = {"Authorization": f"Bearer {candidate_token}"}

    # Get a job ID
    list_res = client.get("/api/v1/jobs?page_size=2")
    jobs = list_res.json()["items"]
    job_1_id = jobs[0]["id"]

    # 1. Save Job
    save_res = client.put(f"/api/v1/saved-jobs/{job_1_id}", headers=headers, json={"notes": "Priority application"})
    assert save_res.status_code == 200

    # 2. Idempotent repeated save (PRD 4.5)
    save_repeat = client.put(f"/api/v1/saved-jobs/{job_1_id}", headers=headers, json={"notes": "Updated note"})
    assert save_repeat.status_code == 200

    # 3. Retrieve saved jobs list
    saved_list_res = client.get("/api/v1/saved-jobs", headers=headers)
    assert saved_list_res.status_code == 200
    saved_items = saved_list_res.json()["items"]
    assert any(s["job_id"] == job_1_id for s in saved_items)

    # 4. Unsave Job
    unsave_res = client.delete(f"/api/v1/saved-jobs/{job_1_id}", headers=headers)
    assert unsave_res.status_code == 200

    # Verify removed
    verify_res = client.get("/api/v1/saved-jobs", headers=headers)
    assert not any(s["job_id"] == job_1_id for s in verify_res.json()["items"])
