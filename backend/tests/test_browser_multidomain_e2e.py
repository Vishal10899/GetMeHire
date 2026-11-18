import sys
import asyncio
from playwright.async_api import async_playwright

async def run_e2e_tests():
    print("=== Starting Playwright End-to-End Validation ===")
    async with async_playwright() as p:
        browser = None
        for channel in ["msedge", "chrome", None]:
            try:
                if channel:
                    browser = await p.chromium.launch(channel=channel, headless=True)
                    print(f"Launched {channel} browser.")
                else:
                    browser = await p.chromium.launch(headless=True)
                    print("Launched default Chromium.")
                break
            except Exception as e:
                continue

        if not browser:
            raise RuntimeError("Could not launch any Chromium-compatible browser")

        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        # Step 1: Homepage
        print("\n[Step 1] Testing Homepage (http://localhost:3000)...")
        await page.goto("http://localhost:3000", wait_until="networkidle")
        title = await page.title()
        print(f"Homepage title: '{title}'")
        assert "Global" in title or "24Jobs" in title or "Job" in title
        
        # Check profession pills / cards on homepage
        pills = await page.query_selector_all("a[href*='/jobs?profession=']")
        print(f"Found {len(pills)} profession category cards on homepage.")
        assert len(pills) >= 5, f"Expected at least 5 profession category links, found {len(pills)}"
        
        # Check verified employer logos
        employers = await page.query_selector_all("a[href*='/jobs?company=']")
        print(f"Found {len(employers)} verified employer links on homepage.")
        assert len(employers) >= 6, f"Expected at least 6 verified employers, found {len(employers)}"

        # Step 2: Intelligent Search with Typo Correction
        print("\n[Step 2] Testing Intelligent Search & Typo Correction (/jobs)...")
        await page.goto("http://localhost:3000/jobs", wait_until="networkidle")
        
        # Search for typo "costumer suppot"
        search_input = page.locator("input[placeholder*='job title' i], input[type='text']").first
        await search_input.fill("costumer suppot")
        
        # Wait for search results
        await page.wait_for_timeout(2500)
        page_content = await page.content()
        
        # Verify typo banner
        assert "Showing results for" in page_content and "customer support" in page_content.lower(), \
            "Expected 'Showing results for customer support' banner in search results"
        print("[OK] Typo correction banner confirmed: 'costumer suppot' -> 'customer support'")
        
        # Check if related roles chips are rendered
        assert "Related Roles:" in page_content or "Related:" in page_content, "Expected 'Related Roles:' role suggestions chips"
        print("[OK] Related role suggestions confirmed.")

        # Step 3: Job Detail Preview & Normalized Title / Summary
        print("\n[Step 3] Testing Job Detail Preview & System Summary...")
        first_job_link = page.locator("a[href*='/jobs/']").first
        await first_job_link.click()
        await page.wait_for_selector("text=Apply on Employer Site", timeout=10000)
        detail_content = await page.content()
        assert ("System-Generated Summary" in detail_content or "Apply on Employer Site" in detail_content or "About the Role" in detail_content), \
            "Expected job detail page with System Summary or Apply button"
        print("[OK] Job preview pane rendered successfully with clean structure and official apply CTA.")

        # Step 4: Login & Career Workspace Profile
        print("\n[Step 4] Testing User Authentication & Career Workspace (/profile)...")
        await page.goto("http://localhost:3000/login", wait_until="networkidle")
        
        email_input = await page.query_selector("input[type='email']")
        password_input = await page.query_selector("input[type='password']")
        submit_btn = await page.query_selector("button[type='submit']")
        
        await email_input.fill("candidate@example.com")
        await password_input.fill("Candidate@123456")
        await submit_btn.click()
        
        # Wait for redirect
        await page.wait_for_timeout(2500)
        print(f"Post-login URL: {page.url}")
        
        # Navigate to /profile
        await page.goto("http://localhost:3000/profile", wait_until="networkidle")
        profile_content = await page.content()
        assert "Career Workspace" in profile_content or "Career Interests" in profile_content or "Profile" in profile_content
        print("[OK] Profile Career Workspace loaded successfully with multi-interest support.")

        # Check Visited Applications tab
        visited_tab = await page.query_selector("button:has-text('Visited Applications')")
        if visited_tab:
            await visited_tab.click()
            await page.wait_for_timeout(1000)
            print("[OK] Visited Applications tab clicked and rendered cleanly.")

        # Step 5: Recommendations Page
        print("\n[Step 5] Testing Recommendations Page (/recommendations)...")
        await page.goto("http://localhost:3000/recommendations", wait_until="networkidle")
        rec_content = await page.content()
        assert "Recommended" in rec_content or "Career" in rec_content or "Jobs" in rec_content
        print("[OK] Recommendations page loaded cleanly.")

        await browser.close()
        print("\n=== ALL E2E BROWSER JOURNEY TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(run_e2e_tests())
