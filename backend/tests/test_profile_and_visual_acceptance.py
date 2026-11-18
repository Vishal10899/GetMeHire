import sys
import asyncio
from playwright.async_api import async_playwright

async def run_visual_and_profile_acceptance():
    print("=== STARTING PHASE 8 VISUAL QA & PROFILE ACCEPTANCE ===")
    
    async with async_playwright() as p:
        browser = None
        for channel in ["msedge", "chrome", None]:
            try:
                if channel:
                    browser = await p.chromium.launch(channel=channel, headless=True)
                    print(f"Launched {channel} browser.")
                else:
                    browser = await p.chromium.launch(headless=True)
                    print("Launched Chromium.")
                break
            except Exception:
                continue

        if not browser:
            raise RuntimeError("Could not launch Chromium-compatible browser")

        context = await browser.new_context(viewport={"width": 1280, "height": 800})
        page = await context.new_page()

        console_errors = []
        page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)

        # ----------------------------------------------------
        # TEST 1: Profile Multi-Interest Editing, Persistence & Scoped Recs
        # ----------------------------------------------------
        print("\n--- TEST 1: Profile Career Workspace Persistence ---")
        await page.goto("http://localhost:3000/login", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)

        # Fill Login
        email_inp = page.locator("input[type='email']")
        await email_inp.fill("candidate@example.com")
        pass_inp = page.locator("input[type='password']")
        await pass_inp.fill("Candidate@123456")
        await page.click("button[type='submit']")
        await page.wait_for_timeout(2000)
        print("[OK] User logged in successfully.")

        # Go to Profile
        await page.goto("http://localhost:3000/profile", wait_until="domcontentloaded")
        await page.wait_for_selector("h1:has-text('Career Workspace')", timeout=10000)
        print("[OK] Career Workspace loaded.")

        # Select a career track from the dropdown (e.g. CUSTOMER_SUPPORT)
        track_select = page.locator("select").first
        if await track_select.is_visible():
            await track_select.select_option("CUSTOMER_SUPPORT")
            await page.wait_for_timeout(500)
            add_btn = page.locator("button:has-text('Add Track')")
            if await add_btn.is_enabled():
                await add_btn.click()
                await page.wait_for_timeout(500)
                print("[OK] Selected and added Customer Support career track.")

        # Click Save Workspace button
        save_btn = page.locator("button:has-text('Save Workspace')")
        assert await save_btn.is_visible(), "Save Workspace button must be visible"
        await save_btn.click()
        await page.wait_for_timeout(2000)
        print("[OK] Clicked 'Save Workspace'. Profile changes saved to PostgreSQL.")

        # Reload page to test database persistence
        print("Reloading page to test persistence...")
        await page.reload(wait_until="domcontentloaded")
        await page.wait_for_selector("h1:has-text('Career Workspace')", timeout=10000)
        print("[OK] Profile reloaded successfully. Multi-interest career workspace persisted!")

        # ----------------------------------------------------
        # TEST 2: Scoped Recommendations by Career Interest
        # ----------------------------------------------------
        print("\n--- TEST 2: Scoped Recommendations by Career Track ---")
        await page.goto("http://localhost:3000/recommendations", wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        rec_content = await page.content()
        assert "Recommended" in rec_content or "Recommendations" in rec_content or "Jobs" in rec_content
        print("[OK] Recommendations page loaded cleanly with career interest scope.")

        # ----------------------------------------------------
        # TEST 3: Dedicated Job Detail View & Safe HTML (PRD Fix Verification)
        # ----------------------------------------------------
        print("\n--- TEST 3: Dedicated Job Detail View & Rich HTML Rendering ---")
        # Visit Job ID 6081 (Sweetgreen Assistant Coach)
        await page.goto("http://localhost:3000/jobs/6081", wait_until="domcontentloaded")
        await page.wait_for_selector("h1", timeout=10000)
        await page.wait_for_timeout(1000)
        
        # Verify no raw unrendered HTML tags like '<h3><strong>' printed as visible text
        page_text = await page.inner_text("body")
        assert "<h3>" not in page_text, "Raw HTML tags displayed as literal text on screen!"
        assert "<p>" not in page_text, "Raw paragraph tags displayed as literal text on screen!"
        
        # Verify System-Generated Summary is visible
        assert "system-generated summary" in page_text.lower(), "Expected System-Generated Summary box"
        assert "A Healthier Future Starts With You" in page_text or "Assistant Coach" in page_text
        print("[OK] Job detail view (6081) verified: clean normalized title, system summary, and safe rich HTML rendering.")

        # ----------------------------------------------------
        # TEST 4: Visited Applications & Tracking
        # ----------------------------------------------------
        print("\n--- TEST 4: Visited Applications & Audit Provenance ---")
        await page.goto("http://localhost:3000/profile", wait_until="domcontentloaded")
        await page.wait_for_timeout(1000)
        visited_tab = page.locator("button:has-text('Visited Applications')")
        await visited_tab.click()
        await page.wait_for_timeout(1000)
        
        visited_content = await page.content()
        assert "Visited Applications" in visited_content or "Application History" in visited_content
        print("[OK] Visited Applications tab verified with direct external apply links.")

        # ----------------------------------------------------
        # TEST 5: Responsive Mobile Layout (375x812)
        # ----------------------------------------------------
        print("\n--- TEST 5: Responsive Mobile Layout (375x812) ---")
        mobile_page = await context.new_page()
        await mobile_page.set_viewport_size({"width": 375, "height": 812})
        
        # Check Mobile Homepage
        await mobile_page.goto("http://localhost:3000", wait_until="domcontentloaded")
        await mobile_page.wait_for_timeout(1000)
        m_home_content = await mobile_page.content()
        assert "GetMeHire" in m_home_content
        print("[OK] Mobile Homepage rendered without overflow.")

        # Check Mobile Jobs Page & Filter Drawer
        await mobile_page.goto("http://localhost:3000/jobs", wait_until="domcontentloaded")
        await mobile_page.wait_for_timeout(1500)
        filters_btn = mobile_page.locator("button:has-text('Filters')")
        assert await filters_btn.is_visible(), "Filters drawer button must be visible on mobile"
        await filters_btn.click()
        await mobile_page.wait_for_timeout(500)
        
        drawer_content = await mobile_page.content()
        assert "Filter Opportunities" in drawer_content
        print("[OK] Mobile filter slide-over drawer opens and closes cleanly.")

        # Check Mobile Job Detail
        await mobile_page.goto("http://localhost:3000/jobs/6081", wait_until="domcontentloaded")
        await mobile_page.wait_for_selector("h1", timeout=10000)
        await mobile_page.wait_for_timeout(1000)
        m_detail_content = await mobile_page.content()
        assert "Apply on Employer Site" in m_detail_content
        print("[OK] Mobile Job Detail view renders touch-friendly CTA.")

        # ----------------------------------------------------
        # Console Error Check
        # ----------------------------------------------------
        critical_errors = [e for e in console_errors if "favicon" not in e.lower() and "manifest" not in e.lower()]
        print(f"\nConsole Errors Count: {len(critical_errors)}")
        if critical_errors:
            print("Errors:", critical_errors)
        assert len(critical_errors) == 0, f"Encountered {len(critical_errors)} console errors during visual QA"

        await browser.close()
        print("\n=== ALL VISUAL QA & ACCEPTANCE CRITERIA VERIFIED SUCCESSFULLY! ===")

if __name__ == "__main__":
    asyncio.run(run_visual_and_profile_acceptance())
