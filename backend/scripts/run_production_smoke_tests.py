"""
GetMeHire — End-to-End Production Smoke Test Suite (Phase 9 Verification)
Tests live Frontend (port 3000) and live Backend (port 8000).
"""
import io
import os
import sys
import time
import json
import uuid
import httpx

# Ensure backend root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

FRONTEND_URL = os.getenv("SMOKE_FRONTEND_URL", "http://127.0.0.1:3000")
BACKEND_URL = os.getenv("SMOKE_BACKEND_URL", "http://127.0.0.1:8000")

results = []

def record(test_name: str, passed: bool, details: str):
    status = "PASS" if passed else "FAILED"
    results.append({"test": test_name, "status": status, "details": details})
    print(f"[{status}] {test_name}: {details}")

def main():
    print("=" * 80)
    print("GETMEHIRE — PHASE 9 POST-DEPLOYMENT SMOKE TESTS")
    print(f"Frontend Target: {FRONTEND_URL}")
    print(f"Backend Target:  {BACKEND_URL}")
    print("=" * 80)

    client = httpx.Client(timeout=15.0)

    # 1. Database & Backend Health
    try:
        r = client.get(f"{BACKEND_URL}/health")
        passed = r.status_code == 200 and r.json().get("status") == "HEALTHY"
        record("1. Database & Backend Health", passed, f"Status: {r.status_code}, Body: {r.text}")
    except Exception as e:
        record("1. Database & Backend Health", False, str(e))

    # 2. Homepage (Frontend)
    try:
        r = client.get(f"{FRONTEND_URL}/")
        passed = r.status_code == 200 and ("GetMeHire" in r.text or "Career" in r.text or "Jobs" in r.text)
        record("2. Homepage HTTP 200", passed, f"Status: {r.status_code}, Length: {len(r.text)} bytes")
    except Exception as e:
        record("2. Homepage HTTP 200", False, str(e))

    # 3. Find Jobs Page (Frontend)
    try:
        r = client.get(f"{FRONTEND_URL}/jobs")
        passed = r.status_code == 200
        record("3. Find Jobs UI Page", passed, f"Status: {r.status_code}, Content-Type: {r.headers.get('content-type')}")
    except Exception as e:
        record("3. Find Jobs UI Page", False, str(e))

    # 4. Global Job Search API
    job_sample_id = None
    try:
        r = client.get(f"{BACKEND_URL}/api/v1/jobs?keyword=Engineer&page=1&page_size=5")
        data = r.json()
        passed = r.status_code == 200 and data.get("total", 0) > 0
        if passed and data.get("items"):
            job_sample_id = data["items"][0]["id"]
            title = data["items"][0]["title"]
            company = data["items"][0].get("company", {}).get("canonical_name", "Unknown")
            details = f"Total matching: {data['total']}, Sample: #{job_sample_id} '{title}' at {company}"
        else:
            details = f"Status: {r.status_code}, Total: {data.get('total')}"
        record("4. Global Job Search API", passed, details)
    except Exception as e:
        record("4. Global Job Search API", False, str(e))

    # 5. Fresher & Entry-Level Search API
    try:
        r = client.get(f"{BACKEND_URL}/api/v1/jobs?early_career_category=TRUE_FRESHER&page=1&page_size=5")
        data = r.json()
        passed = r.status_code == 200 and data.get("total", 0) > 0
        details = f"Total TRUE_FRESHER jobs: {data.get('total')}, returned: {len(data.get('items', []))}"
        record("5. Fresher Search API", passed, details)
    except Exception as e:
        record("5. Fresher Search API", False, str(e))

    # 6. Entry-Level Filters API
    try:
        r = client.get(f"{BACKEND_URL}/api/v1/jobs?experience_level=ENTRY&page=1&page_size=5")
        data = r.json()
        passed = r.status_code == 200 and data.get("total", 0) > 0
        details = f"Total ENTRY level jobs: {data.get('total')}, returned: {len(data.get('items', []))}"
        record("6. Entry-Level Filters API", passed, details)
    except Exception as e:
        record("6. Entry-Level Filters API", False, str(e))

    # 7. Job Detail Pages (Backend API + Frontend route)
    if job_sample_id:
        try:
            r_api = client.get(f"{BACKEND_URL}/api/v1/jobs/{job_sample_id}")
            r_ui = client.get(f"{FRONTEND_URL}/jobs/{job_sample_id}")
            passed = r_api.status_code == 200 and r_ui.status_code == 200
            record("7. Job Detail Pages (API & UI)", passed, f"API Status: {r_api.status_code}, UI Status: {r_ui.status_code}")
        except Exception as e:
            record("7. Job Detail Pages (API & UI)", False, str(e))
    else:
        record("7. Job Detail Pages (API & UI)", False, "Skipped due to missing sample job")

    # 8. Employer Application Links & Activity Tracking
    if job_sample_id:
        try:
            r = client.post(f"{BACKEND_URL}/api/v1/jobs/{job_sample_id}/apply")
            data = r.json()
            passed = r.status_code in [200, 307] and ("application_url" in data or "redirect_url" in data or r.status_code == 307)
            app_url = data.get("application_url") or data.get("redirect_url") or r.headers.get("location")
            record("8. Employer Application Links & Provenance", passed, f"Status: {r.status_code}, URL: {app_url[:60] if app_url else 'N/A'}...")
        except Exception as e:
            record("8. Employer Application Links & Provenance", False, str(e))

    # 9. Authentication: Register and Login
    candidate_token = None
    admin_token = None
    test_email = f"smoketest_{uuid.uuid4().hex[:8]}@example.com"
    test_password = "SmokeTestPassword@123"
    try:
        # Register
        r_reg = client.post(f"{BACKEND_URL}/api/v1/auth/register", json={"email": test_email, "password": test_password})
        passed_reg = r_reg.status_code == 201

        # Login candidate
        r_login = client.post(f"{BACKEND_URL}/api/v1/auth/login", json={"email": test_email, "password": test_password})
        passed_login = r_login.status_code == 200 and "access_token" in r_login.json()
        if passed_login:
            candidate_token = r_login.json()["access_token"]

        # Login admin
        r_admin = client.post(f"{BACKEND_URL}/api/v1/auth/login", json={"email": "admin@jobplatform.com", "password": "Admin@123456"})
        if r_admin.status_code == 200 and "access_token" in r_admin.json():
            admin_token = r_admin.json()["access_token"]

        passed = passed_reg and passed_login and (admin_token is not None)
        record("9. Authentication & Authorization (Register, Candidate & Admin Login)", passed, f"Reg: {r_reg.status_code}, Login: {r_login.status_code}, Admin: {r_admin.status_code}")
    except Exception as e:
        record("9. Authentication & Authorization (Register, Candidate & Admin Login)", False, str(e))

    # 10. Resume Upload (Authenticated Candidate)
    if candidate_token:
        try:
            auth_headers = {"Authorization": f"Bearer {candidate_token}"}
            sample_pdf_bytes = b"%PDF-1.5 %Sample Production Smoke Test PDF Resume Content for Alex Chen"
            files = {"file": ("smoke_alex_chen.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")}
            r = client.post(f"{BACKEND_URL}/api/v1/profile/resume", headers=auth_headers, files=files)
            passed = r.status_code == 200 and r.json().get("filename") == "smoke_alex_chen.pdf"
            record("10. Resume Upload & Validation", passed, f"Status: {r.status_code}, Filename: {r.json().get('filename')}")
        except Exception as e:
            record("10. Resume Upload & Validation", False, str(e))
    else:
        record("10. Resume Upload & Validation", False, "Skipped (no token)")

    # 11. Resume Analysis
    if candidate_token:
        try:
            auth_headers = {"Authorization": f"Bearer {candidate_token}"}
            sample_content = {
                "full_name": "Smoke Test Candidate",
                "email": test_email,
                "skills": ["Python", "FastAPI", "React", "PostgreSQL"],
                "work_experience": [
                    {
                        "role_title": "Software Engineer",
                        "company_name": "Tech Corp",
                        "duration": "2023 - Present",
                        "bullets": ["Architected high-throughput REST APIs handling 10k RPS.", "Optimized PostgreSQL indexes."]
                    }
                ]
            }
            r = client.post(f"{BACKEND_URL}/api/v1/resume-studio/analyze", headers=auth_headers, json=sample_content)
            data = r.json()
            passed = r.status_code == 200 and "overall_score" in data
            record("11. Resume Studio Analysis", passed, f"Status: {r.status_code}, Overall Score: {data.get('overall_score')}%")
        except Exception as e:
            record("11. Resume Studio Analysis", False, str(e))
    else:
        record("11. Resume Studio Analysis", False, "Skipped (no token)")

    # 12. JD Matching
    if candidate_token:
        try:
            auth_headers = {"Authorization": f"Bearer {candidate_token}"}
            jd_payload = {
                "resume_data": {
                    "skills": ["Python", "PostgreSQL", "Docker", "FastAPI"],
                    "experience_years": 4.0
                },
                "job_description": "Looking for a Python Developer with strong FastAPI, PostgreSQL, and Docker experience. Minimum 3 years experience required."
            }
            r = client.post(f"{BACKEND_URL}/api/v1/resume-studio/jd-match", headers=auth_headers, json=jd_payload)
            data = r.json()
            score = data.get("overall_match_score", 0)
            passed = r.status_code == 200 and score > 70
            record("12. Resume JD Matching", passed, f"Status: {r.status_code}, Match Score: {score}%, Matched Skills: {len(data.get('matched_skills', []))}")
        except Exception as e:
            record("12. Resume JD Matching", False, str(e))
    else:
        record("12. Resume JD Matching", False, "Skipped (no token)")

    # 13. Resume PDF Export
    if candidate_token:
        try:
            auth_headers = {"Authorization": f"Bearer {candidate_token}"}
            export_payload = {
                "version_title": "Production Master Smoke Test Resume",
                "template_id": "software_engineering",
                "is_master": True,
                "content": {
                    "full_name": "Smoke Test Candidate",
                    "email": test_email,
                    "phone": "+1-555-0199",
                    "location": "San Francisco, CA",
                    "skills": ["Python", "FastAPI", "PostgreSQL"],
                    "work_experience": [
                        {
                            "role_title": "Backend Engineer",
                            "company_name": "Acme Inc",
                            "duration": "2023 - Present",
                            "bullets": ["Engineered distributed services with 99.99% availability."]
                        }
                    ]
                }
            }
            r = client.post(f"{BACKEND_URL}/api/v1/resume-studio/export/pdf", headers=auth_headers, json=export_payload)
            passed = r.status_code == 200 and r.content.startswith(b"%PDF")
            record("13. Resume PDF Export", passed, f"Status: {r.status_code}, Size: {len(r.content)} bytes, Header: {r.content[:5]}")
        except Exception as e:
            record("13. Resume PDF Export", False, str(e))
    else:
        record("13. Resume PDF Export", False, "Skipped (no token)")

    # 14. Resume DOCX Export
    if candidate_token:
        try:
            auth_headers = {"Authorization": f"Bearer {candidate_token}"}
            export_payload = {
                "version_title": "Production Master Smoke Test Resume",
                "template_id": "software_engineering",
                "is_master": True,
                "content": {
                    "full_name": "Smoke Test Candidate",
                    "email": test_email,
                    "phone": "+1-555-0199",
                    "location": "San Francisco, CA",
                    "skills": ["Python", "FastAPI", "PostgreSQL"],
                    "work_experience": [
                        {
                            "role_title": "Backend Engineer",
                            "company_name": "Acme Inc",
                            "duration": "2023 - Present",
                            "bullets": ["Engineered distributed services with 99.99% availability."]
                        }
                    ]
                }
            }
            r = client.post(f"{BACKEND_URL}/api/v1/resume-studio/export/docx", headers=auth_headers, json=export_payload)
            passed = r.status_code == 200 and r.content.startswith(b"PK")
            record("14. Resume DOCX Export", passed, f"Status: {r.status_code}, Size: {len(r.content)} bytes, Header: {r.content[:2]}")
        except Exception as e:
            record("14. Resume DOCX Export", False, str(e))
    else:
        record("14. Resume DOCX Export", False, "Skipped (no token)")

    # 15. Admin Dashboard APIs
    if admin_token:
        try:
            admin_headers = {"Authorization": f"Bearer {admin_token}"}
            r_sources = client.get(f"{BACKEND_URL}/api/v1/admin/sources", headers=admin_headers)
            r_health = client.get(f"{BACKEND_URL}/api/v1/admin/health", headers=admin_headers)
            r_runs = client.get(f"{BACKEND_URL}/api/v1/admin/ingestion-runs?limit=5", headers=admin_headers)
            passed = r_sources.status_code == 200 and r_health.status_code == 200 and r_runs.status_code == 200
            total_src = len(r_sources.json()) if isinstance(r_sources.json(), list) else 0
            record("15. Admin Dashboard Telemetry & Sources", passed, f"Sources: {total_src}, Health DB: {r_health.json().get('database_connected')}, Runs retrieved: {len(r_runs.json())}")
        except Exception as e:
            record("15. Admin Dashboard Telemetry & Sources", False, str(e))
    else:
        record("15. Admin Dashboard Telemetry & Sources", False, "Skipped (no admin token)")

    # 16. Standalone Background Worker Execution & Advisory Lock
    try:
        from app.worker import StandaloneWorker
        worker = StandaloneWorker(interval_seconds=300, max_sources_per_tick=3)
        tick_res = worker.execute_tick()
        passed = tick_res.get("lock_acquired") is True
        record("16. Standalone Worker & Advisory Lock", passed, f"Lock Acquired: {tick_res.get('lock_acquired')}, Due Sources: {tick_res.get('due_count')}, Executed: {tick_res.get('executed_count')}")
    except Exception as e:
        record("16. Standalone Worker & Advisory Lock", False, str(e))

    print("\n" + "=" * 80)
    print("PHASE 9 SMOKE TEST SUMMARY")
    print("=" * 80)
    all_passed = True
    for item in results:
        status_str = f"[{item['status']}]".ljust(10)
        print(f"{status_str} {item['test']}")
        if item["status"] != "PASS":
            all_passed = False

    print("\nOVERALL STATUS:", "100% ALL CHECKS PASSED" if all_passed else "SOME CHECKS FAILED")

    with open("backend/production_smoke_test_results.json", "w") as f:
        json.dump(results, f, indent=2)

if __name__ == "__main__":
    main()
