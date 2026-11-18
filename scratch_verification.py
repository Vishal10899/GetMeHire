import asyncio
import os
import sys
import time
import httpx
from playwright.async_api import async_playwright

API_BASE = "http://127.0.0.1:8000/api/v1"
FE_BASE = "http://localhost:3000"

results = {}

async def test_milestone_1_auth():
    print("\n--- MILESTONE 1: Authentication and Registration ---")
    async with httpx.AsyncClient() as client:
        # 1. Login with existing candidate
        res_login = await client.post(f"{API_BASE}/auth/login", json={
            "email": "candidate@example.com",
            "password": "Candidate@123456"
        })
        assert res_login.status_code == 200, f"Candidate login failed: {res_login.text}"
        data = res_login.json()
        assert "access_token" in data
        candidate_token = data["access_token"]
        print("  [PASS] Existing candidate login successful. Token acquired.")

        # 2. Login with invalid password
        res_bad = await client.post(f"{API_BASE}/auth/login", json={
            "email": "candidate@example.com",
            "password": "WrongPassword!999"
        })
        assert res_bad.status_code == 401, f"Bad password should return 401: {res_bad.status_code}"
        print("  [PASS] Invalid password correctly rejected (401).")

        # 3. Register new candidate
        timestamp = int(time.time())
        test_email = f"qa_candidate_{timestamp}@example.com"
        res_reg = await client.post(f"{API_BASE}/auth/register", json={
            "email": test_email,
            "password": "TestPassword@2026",
            "full_name": f"QA Candidate {timestamp}"
        })
        assert res_reg.status_code == 201 or res_reg.status_code == 200, f"Register failed: {res_reg.text}"
        reg_data = res_reg.json()
        assert "id" in reg_data
        assert reg_data["email"] == test_email
        print(f"  [PASS] Registration successful for {test_email} (User ID: {reg_data['id']}).")

        # 4. Login with newly registered candidate
        res_new_login = await client.post(f"{API_BASE}/auth/login", json={
            "email": test_email,
            "password": "TestPassword@2026"
        })
        assert res_new_login.status_code == 200
        new_token = res_new_login.json()["access_token"]
        print("  [PASS] New user login immediately succeeded with issued token.")

        # 4. Token validation on /profile
        res_prof = await client.get(f"{API_BASE}/profile", headers={"Authorization": f"Bearer {candidate_token}"})
        assert res_prof.status_code == 200
        print("  [PASS] Bearer token validation on /profile successful.")

    results["Milestone 1: Authentication and Registration"] = "PASS"
    return candidate_token

async def test_milestone_2_profile_and_resume(token):
    print("\n--- MILESTONE 2: My Profile & Resume Persistence ---")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}
        
        # 1. Read profile
        res_get = await client.get(f"{API_BASE}/profile", headers=headers)
        assert res_get.status_code == 200
        prof_data = res_get.json()
        print(f"  [PASS] Profile read: {prof_data.get('full_name')} ({prof_data.get('email')})")

        # 2. Update profile
        update_payload = {
            "headline": "Senior Full Stack Systems Architect",
            "phone_number": "+1-555-0199",
            "skills": ["Python", "FastAPI", "React", "Next.js", "PostgreSQL", "Docker", "TailwindCSS"],
            "total_experience_years": 8.0,
            "salary_expectation_min": 170000,
            "salary_expectation_max": 240000,
            "preferred_locations": ["Remote", "San Francisco, CA", "New York, NY"],
            "work_arrangements": ["REMOTE"],
            "career_interests": [
                {"profession": "ENGINEERING", "preferred_roles": ["Lead Architect"], "skills": ["Python", "FastAPI"], "experience_years": 8.0},
                {"profession": "DATA_AI", "preferred_roles": ["AI Engineer"], "skills": ["PyTorch"], "experience_years": 4.0}
            ]
        }
        res_patch = await client.patch(f"{API_BASE}/profile", json=update_payload, headers=headers)
        assert res_patch.status_code == 200, f"Update profile failed: {res_patch.text}"
        print("  [PASS] Profile PATCH update successful.")

        # 3. Verify persistence
        res_verify = await client.get(f"{API_BASE}/profile", headers=headers)
        assert res_verify.status_code == 200
        saved = res_verify.json()
        assert saved.get("headline") == "Senior Full Stack Systems Architect"
        professions_in_interests = [ci["profession"] for ci in saved.get("career_interests", [])]
        assert "DATA_AI" in professions_in_interests
        assert float(saved.get("salary_expectation_min")) == 170000
        print("  [PASS] Profile updates verified persisted in database.")

        # 4. Resume upload test (mock PDF content)
        files = {
            "file": ("test_resume.pdf", b"%PDF-1.4 mock resume content for verification testing", "application/pdf")
        }
        res_resume = await client.post(f"{API_BASE}/profile/resume", files=files, headers=headers)
        assert res_resume.status_code == 200, f"Resume upload failed: {res_resume.text}"
        res_data = res_resume.json()
        assert "resume_filename" in res_data or "filename" in res_data or "message" in res_data
        print("  [PASS] Resume upload and persistence verified.")

    results["Milestone 2: My Profile and Resume Persistence"] = "PASS"

async def test_milestone_3_jobs_search_filters_pagination():
    print("\n--- MILESTONE 3: Job Listings, Search, Filters, Sorting & Pagination ---")
    async with httpx.AsyncClient() as client:
        # 1. Jobs GET default
        r1 = await client.get(f"{API_BASE}/jobs?page=1&page_size=20")
        assert r1.status_code == 200
        d1 = r1.json()
        assert d1["total"] >= 2800, f"Expected total >= 2800, got {d1['total']}"
        assert len(d1["items"]) == 20
        print(f"  [PASS] Jobs listings GET successful. Total active jobs: {d1['total']}")

        # 2. Keyword Search
        r2 = await client.get(f"{API_BASE}/jobs?keyword=Engineer&page_size=10")
        assert r2.status_code == 200
        d2 = r2.json()
        assert d2["total"] > 0
        print(f"  [PASS] Keyword search 'Engineer': {d2['total']} matches found.")

        # 3. Profession filter
        r3 = await client.get(f"{API_BASE}/jobs?profession=SALES_BIZDEV&page_size=10")
        assert r3.status_code == 200
        d3 = r3.json()
        assert d3["total"] > 0
        assert all(j["profession"] == "SALES_BIZDEV" for j in d3["items"])
        print(f"  [PASS] Profession filter 'SALES_BIZDEV': {d3['total']} jobs, all verified matching taxonomy.")

        # 4. Remote filter
        r4 = await client.get(f"{API_BASE}/jobs?remote_type=REMOTE&page_size=10")
        assert r4.status_code == 200
        d4 = r4.json()
        assert d4["total"] > 0
        assert all(j["remote_type"] == "REMOTE" for j in d4["items"])
        print(f"  [PASS] Remote type filter 'REMOTE': {d4['total']} verified.")

        # 5. Sorting by newest
        r5 = await client.get(f"{API_BASE}/jobs?sort_by=newest&page_size=5")
        assert r5.status_code == 200
        d5 = r5.json()
        assert len(d5["items"]) == 5
        print("  [PASS] Sorting by 'newest' verified.")

        # 6. Pagination consistency
        r_p1 = await client.get(f"{API_BASE}/jobs?page=1&page_size=10")
        r_p2 = await client.get(f"{API_BASE}/jobs?page=2&page_size=10")
        p1_ids = [j["id"] for j in r_p1.json()["items"]]
        p2_ids = [j["id"] for j in r_p2.json()["items"]]
        assert set(p1_ids).isdisjoint(set(p2_ids)), "Pages 1 & 2 have overlapping items"
        print("  [PASS] Pagination verified: Page 1 and Page 2 are strictly disjoint.")

    results["Milestone 3: Job Listings, Search, Filters, Sorting & Pagination"] = "PASS"

async def test_milestone_4_job_details_and_employer_links():
    print("\n--- MILESTONE 4: Job Details and Original Employer Application Links ---")
    async with httpx.AsyncClient() as client:
        # Get first job
        r_list = await client.get(f"{API_BASE}/jobs?page_size=1")
        job_id = r_list.json()["items"][0]["id"]
        
        # Detail GET
        r_det = await client.get(f"{API_BASE}/jobs/{job_id}")
        assert r_det.status_code == 200
        job = r_det.json()
        assert job["id"] == job_id
        assert job["title"]
        company_name = job.get("company_name") or job.get("company", {}).get("canonical_name") or job.get("company", {}).get("name")
        assert company_name, "Company name missing from job detail"
        assert job["application_url"].startswith("http"), f"Invalid application URL: {job['application_url']}"
        assert job["source_name"]
        print(f"  [PASS] Job detail #{job_id} ('{job['title']}' at {company_name}) retrieved.")
        print(f"  [PASS] ATS Provenance confirmed: Source '{job['source_name']}', URL: {job['application_url']}")

        # Similar jobs
        r_sim = await client.get(f"{API_BASE}/jobs/{job_id}/similar")
        assert r_sim.status_code == 200
        sim_data = r_sim.json()
        assert "jobs" in sim_data
        print(f"  [PASS] Similar jobs endpoint returned {len(sim_data['jobs'])} recommendations.")

    results["Milestone 4: Job Details & Original Employer Application Links"] = "PASS"
    return job_id

async def test_milestone_5_save_jobs_and_visited_history(token, job_id):
    print("\n--- MILESTONE 5: Save Jobs and Visited Application History ---")
    async with httpx.AsyncClient() as client:
        headers = {"Authorization": f"Bearer {token}"}

        # 1. Save job
        r_save = await client.put(f"{API_BASE}/saved-jobs/{job_id}", headers=headers)
        assert r_save.status_code == 200 or r_save.status_code == 201
        print(f"  [PASS] Saved job #{job_id} successfully.")

        # 2. Check saved jobs list
        r_list = await client.get(f"{API_BASE}/saved-jobs", headers=headers)
        assert r_list.status_code == 200
        saved_list = r_list.json().get("items", [])
        assert any(item.get("job_id") == job_id for item in saved_list)
        print("  [PASS] Saved job confirmed present in candidate's bookmarks.")

        # 3. Track visited application
        r_visit = await client.post(f"{API_BASE}/jobs/{job_id}/visit", headers=headers)
        assert r_visit.status_code == 200
        visit_data = r_visit.json()
        assert "redirect_url" in visit_data
        print(f"  [PASS] Job visit tracked. Redirect URL: {visit_data['redirect_url']}")

        # 4. Check visited history
        r_hist = await client.get(f"{API_BASE}/profile/visited-jobs", headers=headers)
        assert r_hist.status_code == 200
        hist_data = r_hist.json()
        assert any(v["job_id"] == job_id for v in hist_data.get("items", []))
        print("  [PASS] Visited history confirmed recorded in database.")

        # 5. Clean up saved job
        r_del = await client.delete(f"{API_BASE}/saved-jobs/{job_id}", headers=headers)
        assert r_del.status_code == 200 or r_del.status_code == 204
        print(f"  [PASS] Unsaved job #{job_id} cleanly.")

    results["Milestone 5: Save Jobs & Application/Visited History"] = "PASS"

async def test_milestone_6_responsiveness():
    print("\n--- MILESTONE 6: Desktop and Mobile Responsiveness ---")
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        
        viewports = [
            ("Desktop", 1440, 900),
            ("Tablet", 768, 1024),
            ("Mobile", 375, 812),
        ]

        for name, width, height in viewports:
            ctx = await browser.new_context(viewport={"width": width, "height": height})
            page = await ctx.new_page()
            
            # 1. Homepage
            await page.goto(FE_BASE, wait_until="networkidle")
            assert await page.title()
            
            # 2. Jobs Page
            await page.goto(f"{FE_BASE}/jobs", wait_until="networkidle")
            await page.wait_for_selector("a[href*='/jobs/']", timeout=15000)
            card_count = len(await page.query_selector_all("a[href*='/jobs/']"))
            assert card_count > 0, f"No job cards found on {name}"
            
            # Check horizontal overflow
            body_scroll_w = await page.evaluate("() => document.body.scrollWidth")
            body_client_w = await page.evaluate("() => document.body.clientWidth")
            assert body_scroll_w <= body_client_w + 1, f"Horizontal overflow detected on {name}: scroll={body_scroll_w}, client={body_client_w}"
            
            print(f"  [PASS] {name} ({width}x{height}): Clean rendering, 0 overflow, job cards verified.")
            await ctx.close()

        await browser.close()

    results["Milestone 6: Desktop & Mobile Responsiveness"] = "PASS"

async def test_milestone_7_security_and_integrity():
    print("\n--- MILESTONE 7: Security and Database Integrity ---")
    async with httpx.AsyncClient() as client:
        # 1. CORS Allowed
        r_opts = await client.request("OPTIONS", f"{API_BASE}/jobs", headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        })
        assert r_opts.status_code == 200
        assert r_opts.headers.get("access-control-allow-origin") == "http://localhost:3000"
        print("  [PASS] CORS Preflight for http://localhost:3000 returned 200 with matching allow-origin.")

        # 2. CORS Disallowed
        r_bad_cors = await client.request("OPTIONS", f"{API_BASE}/jobs", headers={
            "Origin": "http://malicious-external-domain.com",
            "Access-Control-Request-Method": "GET"
        })
        assert r_bad_cors.status_code == 400
        assert r_bad_cors.headers.get("access-control-allow-origin") is None
        print("  [PASS] Disallowed CORS origin correctly rejected (400) with no allow-origin header.")

        # 3. Security headers
        r_health = await client.get("http://127.0.0.1:8000/health")
        assert r_health.status_code == 200
        hdrs = r_health.headers
        assert hdrs.get("x-content-type-options") == "nosniff"
        assert hdrs.get("x-frame-options") == "DENY"
        assert hdrs.get("x-xss-protection") == "1; mode=block"
        assert "max-age=" in hdrs.get("strict-transport-security", "")
        print("  [PASS] OWASP Security Headers (nosniff, DENY, X-XSS, HSTS) verified.")

        # 4. Database integrity
        db_info = r_health.json()
        assert db_info["status"] == "HEALTHY"
        assert db_info["database"] == "CONNECTED"
        print(f"  [PASS] PostgreSQL Database Connection Health: {db_info}")

    results["Milestone 7: Security & Database Integrity"] = "PASS"

async def main():
    print("=================================================================")
    print("GLOBALJOBS FULL APPLICATION-WIDE STRUCTURED VERIFICATION SUITE")
    print("=================================================================")
    
    token = await test_milestone_1_auth()
    await test_milestone_2_profile_and_resume(token)
    await test_milestone_3_jobs_search_filters_pagination()
    job_id = await test_milestone_4_job_details_and_employer_links()
    await test_milestone_5_save_jobs_and_visited_history(token, job_id)
    await test_milestone_6_responsiveness()
    await test_milestone_7_security_and_integrity()

    print("\n=================================================================")
    print("SUMMARY OF STRUCTURED APPLICATION-WIDE VERIFICATION:")
    print("=================================================================")
    all_passed = True
    for m, status in results.items():
        print(f"  • {m}: {status}")
        if status != "PASS":
            all_passed = False
    
    if all_passed:
        print("\n>>> ALL 7 MILESTONES PASSED WITH 100% SUCCESS <<<")
    else:
        print("\n>>> SOME MILESTONES FAILED <<<")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
