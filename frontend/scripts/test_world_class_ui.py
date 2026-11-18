import asyncio
import os
import sys
from playwright.async_api import async_playwright

SCREENSHOT_DIR = r"C:\Users\WELCOME\.gemini\antigravity-cli\brain\aee234ef-9627-42b9-81d0-d5b9541953a8"

async def test_ui_and_responsiveness():
    print("Launching Edge browser for UI testing...", flush=True)
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        
        viewports = [
            ("mobile_375", 375, 812),
            ("tablet_768", 768, 1024),
            ("desktop_1440", 1440, 900),
        ]
        
        for name, width, height in viewports:
            context = await browser.new_context(
                viewport={"width": width, "height": height},
                device_scale_factor=2,
            )
            page = await context.new_page()
            page.set_default_navigation_timeout(60000)
            page.set_default_timeout(60000)
            
            # 1. Homepage
            print(f"Testing Homepage at {name} ({width}x{height})...", flush=True)
            await page.goto("http://localhost:3000/", wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            
            # Check smooth scroll style on html
            smooth_scroll = await page.evaluate("() => getComputedStyle(document.documentElement).scrollBehavior")
            print(f"[{name}] HTML scroll-behavior: {smooth_scroll}", flush=True)
            assert smooth_scroll == "smooth", f"Expected scroll-behavior: smooth, got {smooth_scroll}"
            
            # Check horizontal overflow
            overflow = await page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
            print(f"[{name}] Horizontal overflow: {overflow}", flush=True)
            assert not overflow, f"Horizontal overflow detected on {name}!"
            
            # Screenshot
            home_shot = os.path.join(SCREENSHOT_DIR, f"homepage_{name}.png")
            await page.screenshot(path=home_shot, full_page=False)
            print(f"[{name}] Saved homepage screenshot", flush=True)
            
            # 2. Jobs Page
            print(f"Testing Jobs Page at {name}...", flush=True)
            await page.goto("http://localhost:3000/jobs", wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            
            jobs_overflow = await page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
            assert not jobs_overflow, f"Horizontal overflow on jobs page for {name}!"
            
            jobs_shot = os.path.join(SCREENSHOT_DIR, f"jobs_{name}.png")
            await page.screenshot(path=jobs_shot, full_page=False)
            print(f"[{name}] Saved jobs screenshot", flush=True)
            
            await context.close()
        
        # 3. Authenticated Journey: Login & Profile
        print("\nTesting Authenticated Candidate Workspace...", flush=True)
        auth_context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )
        auth_page = await auth_context.new_page()
        auth_page.set_default_navigation_timeout(60000)
        auth_page.set_default_timeout(60000)
        
        # Go to login
        await auth_page.goto("http://localhost:3000/login", wait_until="domcontentloaded")
        await auth_page.wait_for_timeout(1000)
        await auth_page.click("button:has-text('Demo Candidate')")
        await auth_page.wait_for_timeout(500)
        await auth_page.click("button[type='submit']")
        await auth_page.wait_for_timeout(4000)
        print(f"[OK] Logged in with Demo Candidate (URL: {auth_page.url})", flush=True)
        
        # Go to Profile
        await auth_page.goto("http://localhost:3000/profile", wait_until="domcontentloaded")
        await auth_page.wait_for_timeout(2000)
        
        profile_shot = os.path.join(SCREENSHOT_DIR, "profile_desktop_1440.png")
        await auth_page.screenshot(path=profile_shot, full_page=False)
        print(f"[OK] Profile snapshot saved to {profile_shot}", flush=True)
        
        # Test tab switching: Preferences & Skills
        await auth_page.click("button:has-text('Preferences & Skills')")
        await auth_page.wait_for_timeout(800)
        assert await auth_page.is_visible("text=All Verified Candidate Skills")
        print("[OK] Preferences & Skills tab rendered correctly", flush=True)
        
        # Test tab switching: Application History
        await auth_page.click("button:has-text('Application History')")
        await auth_page.wait_for_timeout(800)
        assert await auth_page.is_visible("text=Visited Employer Application Links")
        print("[OK] Application History tab rendered correctly", flush=True)
        
        # 4. Recommendations Page
        print("\nTesting Recommendations Page...", flush=True)
        await auth_page.goto("http://localhost:3000/recommendations", wait_until="domcontentloaded")
        await auth_page.wait_for_timeout(2000)
        recs_shot = os.path.join(SCREENSHOT_DIR, "recommendations_desktop_1440.png")
        await auth_page.screenshot(path=recs_shot, full_page=False)
        print(f"[OK] Recommendations snapshot saved to {recs_shot}", flush=True)
        
        # 4b. Test Direct Tab Query Param on Profile (/profile?tab=history)
        print("\nTesting Direct Tab Query Param Navigation (/profile?tab=history)...", flush=True)
        await auth_page.goto("http://localhost:3000/profile?tab=history", wait_until="domcontentloaded")
        await auth_page.wait_for_selector("text=Visited Employer Application Links", timeout=15000)
        print("[OK] Direct query param /profile?tab=history opened Application History tab", flush=True)

        # 5. Job Detail Page: verify 'Role Snapshot' and zero AI smells
        print("\nTesting Dedicated Job Page for clean layout & Role Snapshot...", flush=True)
        await auth_page.goto("http://localhost:3000/jobs/1", wait_until="domcontentloaded")
        await auth_page.wait_for_selector("text=Role Snapshot", timeout=15000)
        
        content = await auth_page.content()
        assert "role snapshot" in content.lower(), "Role Snapshot header not found!"
        assert "system-generated summary:" not in content.lower(), "AI smell 'system-generated summary:' found!"
        
        detail_shot = os.path.join(SCREENSHOT_DIR, "job_detail_desktop_1440.png")
        await auth_page.screenshot(path=detail_shot, full_page=False)
        print(f"[OK] Job detail snapshot saved to {detail_shot}", flush=True)

        # 6. Admin Panel Operations & Telemetry Verification
        print("\nTesting Admin Panel & ATS Auto-Discovery...", flush=True)
        admin_context = await browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=2,
        )
        admin_page = await admin_context.new_page()
        admin_page.set_default_navigation_timeout(60000)
        admin_page.set_default_timeout(60000)
        await admin_page.goto("http://localhost:3000/login", wait_until="domcontentloaded")
        await admin_page.wait_for_timeout(1000)
        await admin_page.click("button:has-text('Platform Admin')")
        await admin_page.wait_for_timeout(500)
        await admin_page.click("button[type='submit']")
        await admin_page.wait_for_timeout(4000)
        print(f"[OK] Logged in with Platform Admin (URL: {admin_page.url})", flush=True)

        await admin_page.goto("http://localhost:3000/admin", wait_until="domcontentloaded")
        await admin_page.wait_for_selector("button:has-text('Auto-Discover ATS')", timeout=15000)

        # Verify operational controls exist
        assert await admin_page.is_visible("button:has-text('Auto-Discover ATS')")
        assert await admin_page.is_visible("button:has-text('Run Scheduler')")
        assert await admin_page.is_visible("button:has-text('Expire Stale (14d)')")
        print("[OK] Admin operational controls (Auto-Discover, Scheduler, Expire Stale) verified", flush=True)

        # Test Auto-Discover Modal
        await admin_page.click("button:has-text('Auto-Discover ATS')")
        await admin_page.wait_for_selector("text=Auto-Discover & Ingest ATS", timeout=10000)

        # Fill and probe
        await admin_page.fill("input[placeholder*='Company token or ATS URL']", "openai")
        await admin_page.click("button:has-text('Probe')")
        await admin_page.wait_for_function(
            "() => document.body.innerText.includes('Detected!') || document.body.innerText.includes('No active ATS board detected')",
            timeout=20000
        )
        print("[OK] Real-time ATS Board Probe successfully executed", flush=True)

        # Dismiss modal
        await admin_page.click("button:has-text('Dismiss')")
        await admin_page.wait_for_timeout(400)

        admin_shot = os.path.join(SCREENSHOT_DIR, "admin_desktop_1440.png")
        await admin_page.screenshot(path=admin_shot, full_page=False)
        print(f"[OK] Admin telemetry snapshot saved to {admin_shot}", flush=True)
        await admin_context.close()
        
        # Mobile Profile View
        print("\nTesting Mobile Profile View (375x812)...", flush=True)
        mobile_context = await browser.new_context(
            viewport={"width": 375, "height": 812},
            device_scale_factor=2,
        )
        mobile_page = await mobile_context.new_page()
        mobile_page.set_default_navigation_timeout(60000)
        mobile_page.set_default_timeout(60000)
        await mobile_page.goto("http://localhost:3000/login", wait_until="domcontentloaded")
        await mobile_page.wait_for_timeout(1000)
        await mobile_page.click("button:has-text('Demo Candidate')")
        await mobile_page.wait_for_timeout(500)
        await mobile_page.click("button[type='submit']")
        await mobile_page.wait_for_timeout(4000)
        print(f"[OK] Mobile logged in with Demo Candidate (URL: {mobile_page.url})", flush=True)
        await mobile_page.goto("http://localhost:3000/profile", wait_until="domcontentloaded")
        await mobile_page.wait_for_timeout(1500)
        
        mobile_overflow = await mobile_page.evaluate("() => document.documentElement.scrollWidth > document.documentElement.clientWidth")
        print(f"[mobile_375] Profile overflow: {mobile_overflow}", flush=True)
        assert not mobile_overflow, "Horizontal overflow on mobile profile!"
        
        mobile_profile_shot = os.path.join(SCREENSHOT_DIR, "profile_mobile_375.png")
        await mobile_page.screenshot(path=mobile_profile_shot, full_page=False)
        print(f"[OK] Mobile profile snapshot saved to {mobile_profile_shot}", flush=True)
        
        await browser.close()
        print("\n=== ALL UI/UX AND RESPONSIVENESS CHECKS PASSED ===", flush=True)

if __name__ == "__main__":
    asyncio.run(test_ui_and_responsiveness())
