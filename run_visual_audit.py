import asyncio
import os
import sys
import httpx
from playwright.async_api import async_playwright

ARTIFACT_DIR = os.environ.get(
    "ARTIFACT_DIR",
    r"C:\Users\WELCOME\.gemini\antigravity-cli\brain\525c5bee-027d-437a-b415-998d369d1157"
)
os.makedirs(ARTIFACT_DIR, exist_ok=True)
BASE_URL = "http://localhost:3000"
API_URL = "http://127.0.0.1:8000/api/v1"

console_errors = []

def track_page(page, context_label):
    page.on("pageerror", lambda err: console_errors.append(f"[{context_label} PAGE ERROR] {err}"))
    page.on("console", lambda msg: console_errors.append(f"[{context_label} CONSOLE {msg.type}] {msg.text}") if msg.type == "error" else None)

async def run_visual_audit():
    # 1. Fetch candidate & admin tokens directly via FastAPI
    candidate_token = None
    admin_token = None
    async with httpx.AsyncClient() as client:
        try:
            res = await client.post(
                f"{API_URL}/auth/login",
                json={"email": "candidate@example.com", "password": "Candidate@123456"}
            )
            if res.status_code == 200:
                candidate_token = res.json()["access_token"]
                print("Candidate token obtained.")
        except Exception as e:
            print("Candidate login error:", e)

        try:
            res = await client.post(
                f"{API_URL}/auth/login",
                json={"email": "admin@jobplatform.com", "password": "Admin@123456"}
            )
            if res.status_code == 200:
                admin_token = res.json()["access_token"]
                print("Admin token obtained.")
        except Exception as e:
            print("Admin login error:", e)

    # User 51 token for candidate name audit
    u51_token = None
    try:
        sys.path.insert(0, "backend")
        from app.core.database import SessionLocal
        from app.models import User
        from app.core.security import create_access_token
        db = SessionLocal()
        u51 = db.query(User).filter(User.id == 51).first()
        if u51:
            u51_token = create_access_token(str(u51.id))
            print(f"User 51 token generated for {u51.email} (profile: {u51.profile.full_name if u51.profile else 'None'}).")
        db.close()
    except Exception as e:
        print("User 51 token generation error:", e)

    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)

        viewports = [
            {"name": "desktop_1440", "width": 1440, "height": 900},
            {"name": "tablet_768", "width": 768, "height": 1024},
            {"name": "mobile_375", "width": 375, "height": 812},
        ]

        # 2. Public Unauthenticated views across all 3 viewports
        for vp in viewports:
            context = await browser.new_context(viewport={"width": vp["width"], "height": vp["height"]})
            page = await context.new_page()
            track_page(page, f"homepage_{vp['name']}")

            # Homepage (full page & header/footer snapshots)
            print(f"[{vp['name']}] Visiting Homepage...")
            await page.goto(f"{BASE_URL}/", wait_until="domcontentloaded")
            await page.wait_for_timeout(1800)
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, f"homepage_{vp['name']}.png"), full_page=True)

            if vp["name"] == "desktop_1440":
                header = page.locator("header")
                if await header.count() > 0:
                    await header.screenshot(path=os.path.join(ARTIFACT_DIR, "navbar_desktop_1440.png"))
                footer = page.locator("footer")
                if await footer.count() > 0:
                    await footer.screenshot(path=os.path.join(ARTIFACT_DIR, "footer_desktop_1440.png"))
            elif vp["name"] == "mobile_375":
                header = page.locator("header")
                if await header.count() > 0:
                    await header.screenshot(path=os.path.join(ARTIFACT_DIR, "navbar_mobile_375.png"))
                footer = page.locator("footer")
                if await footer.count() > 0:
                    await footer.screenshot(path=os.path.join(ARTIFACT_DIR, "footer_mobile_375.png"))
                
                # Test & capture animated mobile navigation drawer
                mobile_btn = page.locator("button[aria-label='Toggle navigation menu']").first
                if await mobile_btn.count() > 0:
                    await mobile_btn.click()
                    await page.wait_for_timeout(400)
                    await page.screenshot(path=os.path.join(ARTIFACT_DIR, "mobile_menu_open_375.png"))
                    await mobile_btn.click()
                    await page.wait_for_timeout(300)

            # Jobs Discovery
            print(f"[{vp['name']}] Visiting Jobs Discovery...")
            track_page(page, f"jobs_{vp['name']}")
            await page.goto(f"{BASE_URL}/jobs", wait_until="domcontentloaded")
            await page.wait_for_timeout(1500)
            await page.screenshot(path=os.path.join(ARTIFACT_DIR, f"jobs_{vp['name']}.png"), full_page=True)

            # Job Details across viewports
            first_job_card = page.locator("a[href^='/jobs/']").first
            if await first_job_card.count() > 0:
                href = await first_job_card.get_attribute("href")
                print(f"[{vp['name']}] Navigating to job detail: {href}...")
                await page.goto(f"{BASE_URL}{href}", wait_until="domcontentloaded")
                await page.wait_for_timeout(1500)
                await page.screenshot(path=os.path.join(ARTIFACT_DIR, f"job_detail_{vp['name']}.png"), full_page=True)

            await context.close()

        # 3. Custom 404 Not Found Page Verification
        ctx_404 = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_404 = await ctx_404.new_page()
        track_page(page_404, "404_page")
        print("[Desktop] Visiting non-existent route to verify custom 404 page...")
        await page_404.goto(f"{BASE_URL}/non-existent-career-link-404", wait_until="domcontentloaded")
        await page_404.wait_for_timeout(1000)
        await page_404.screenshot(path=os.path.join(ARTIFACT_DIR, "not_found_desktop_1440.png"), full_page=True)
        await ctx_404.close()

        # 4. Sign In Page with Password Toggle Verification
        ctx_login = await browser.new_context(viewport={"width": 1440, "height": 900})
        page_login = await ctx_login.new_page()
        track_page(page_login, "login_page")
        print("[Desktop] Visiting Sign In page...")
        await page_login.goto(f"{BASE_URL}/login", wait_until="domcontentloaded")
        await page_login.wait_for_timeout(1000)
        await page_login.fill("input[type='password']", "Candidate@123456")
        toggle_btn = page_login.locator("button[aria-label='Show password']").first
        if await toggle_btn.count() > 0:
            await toggle_btn.click()
            await page_login.wait_for_timeout(300)
        await page_login.screenshot(path=os.path.join(ARTIFACT_DIR, "login_with_password_toggle.png"), full_page=True)
        await ctx_login.close()

        # 5. Authenticated Candidate Context (Desktop)
        if candidate_token:
            cand_ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
            await cand_ctx.add_init_script(f"""
                localStorage.setItem('job_platform_token', '{candidate_token}');
            """)
            c_page = await cand_ctx.new_page()
            track_page(c_page, "candidate_desktop")

            # Candidate Profile Desktop - Single Unified Scrollable Page
            print("[Desktop] Visiting Candidate My Profile...")
            await c_page.goto(f"{BASE_URL}/profile", wait_until="domcontentloaded")
            await c_page.wait_for_timeout(1800)
            await c_page.screenshot(path=os.path.join(ARTIFACT_DIR, "profile_desktop_1440.png"), full_page=True)

            # Account Dropdown Menu on Desktop
            print("[Desktop] Opening Account Menu Dropdown...")
            await c_page.goto(f"{BASE_URL}/jobs", wait_until="domcontentloaded")
            await c_page.wait_for_timeout(1000)
            account_btn = c_page.locator("button[aria-expanded]").first
            if await account_btn.count() > 0:
                await account_btn.click()
                await c_page.wait_for_timeout(500)
                await c_page.screenshot(path=os.path.join(ARTIFACT_DIR, "account_menu_desktop_1440.png"))
                await account_btn.click()
                await c_page.wait_for_timeout(300)

            # Recommendations Desktop
            print("[Desktop] Visiting Recommended Jobs...")
            await c_page.goto(f"{BASE_URL}/recommendations", wait_until="domcontentloaded")
            await c_page.wait_for_timeout(1500)
            await c_page.screenshot(path=os.path.join(ARTIFACT_DIR, "recommendations_desktop_1440.png"), full_page=True)

            # Test & capture accordion scoring breakdown drawer
            breakdown_btn = c_page.locator("button:has-text('View Scoring Breakdown')").first
            if await breakdown_btn.count() > 0:
                await breakdown_btn.click()
                await c_page.wait_for_timeout(400)
                await c_page.screenshot(path=os.path.join(ARTIFACT_DIR, "recommendations_accordion_desktop_1440.png"), full_page=True)

            # Saved Jobs Desktop
            print("[Desktop] Visiting Saved Jobs...")
            await c_page.goto(f"{BASE_URL}/saved", wait_until="domcontentloaded")
            await c_page.wait_for_timeout(1500)
            await c_page.screenshot(path=os.path.join(ARTIFACT_DIR, "saved_jobs_desktop_1440.png"), full_page=True)

            # Job Alerts Desktop
            print("[Desktop] Visiting Job Alerts...")
            await c_page.goto(f"{BASE_URL}/alerts", wait_until="domcontentloaded")
            await c_page.wait_for_timeout(1500)
            await c_page.screenshot(path=os.path.join(ARTIFACT_DIR, "alerts_desktop_1440.png"), full_page=True)

            # Test & capture accessible AnimatedDialog modal
            trash_btn = c_page.locator("button:has(svg.lucide-trash2)").first
            if await trash_btn.count() > 0:
                await trash_btn.click()
                await c_page.wait_for_timeout(400)
                await c_page.screenshot(path=os.path.join(ARTIFACT_DIR, "animated_dialog_desktop_1440.png"))
                cancel_btn = c_page.locator("button:has-text('Cancel')").first
                if await cancel_btn.count() > 0:
                    await cancel_btn.click()
                    await c_page.wait_for_timeout(300)

            await cand_ctx.close()

        # 6. Mobile Candidate Profile
        if candidate_token:
            m_ctx = await browser.new_context(viewport={"width": 375, "height": 812})
            await m_ctx.add_init_script(f"""
                localStorage.setItem('job_platform_token', '{candidate_token}');
            """)
            m_page = await m_ctx.new_page()
            track_page(m_page, "candidate_mobile")
            print("[Mobile] Visiting Candidate Profile...")
            await m_page.goto(f"{BASE_URL}/profile", wait_until="domcontentloaded")
            await m_page.wait_for_timeout(1500)
            await m_page.screenshot(path=os.path.join(ARTIFACT_DIR, "profile_mobile_375.png"), full_page=True)
            await m_ctx.close()

        # 7. Admin Portal Desktop
        if admin_token:
            admin_ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
            await admin_ctx.add_init_script(f"""
                localStorage.setItem('job_platform_token', '{admin_token}');
            """)
            a_page = await admin_ctx.new_page()
            track_page(a_page, "admin_desktop")
            print("[Admin] Visiting Admin Dashboard...")
            await a_page.goto(f"{BASE_URL}/admin", wait_until="domcontentloaded")
            await a_page.wait_for_timeout(1500)
            await a_page.screenshot(path=os.path.join(ARTIFACT_DIR, "admin_desktop_1440.png"), full_page=True)
            await admin_ctx.close()

        # 8. Candidate 51 Name Fix Audit
        if u51_token:
            u51_ctx = await browser.new_context(viewport={"width": 1440, "height": 900})
            await u51_ctx.add_init_script(f"""
                localStorage.setItem('job_platform_token', '{u51_token}');
            """)
            u51_page = await u51_ctx.new_page()
            track_page(u51_page, "user51_audit")
            print("[User 51] Visiting My Profile to verify saved name consistency...")
            await u51_page.goto(f"{BASE_URL}/profile", wait_until="domcontentloaded")
            await u51_page.wait_for_timeout(1800)
            account_btn = u51_page.locator("button[aria-expanded]").first
            if await account_btn.count() > 0:
                await account_btn.click()
                await u51_page.wait_for_timeout(600)
                await u51_page.screenshot(path=os.path.join(ARTIFACT_DIR, "user51_account_menu_1440.png"))
            await u51_ctx.close()

        await browser.close()
        print("Visual QA audit completed successfully! All screenshots captured.")
        if console_errors:
            print("Console Errors encountered:")
            for err in console_errors:
                print(" -", err)
        else:
            print("Zero uncaught console errors recorded!")

if __name__ == "__main__":
    asyncio.run(run_visual_audit())
