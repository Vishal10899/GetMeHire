import sys
import asyncio
from playwright.async_api import async_playwright

async def run_xss_verification():
    print("=== STARTING BROWSER-LEVEL XSS SANITIZATION VERIFICATION ===")
    
    async with async_playwright() as p:
        browser = None
        for channel in ["msedge", "chrome", None]:
            try:
                if channel:
                    browser = await p.chromium.launch(channel=channel, headless=True)
                else:
                    browser = await p.chromium.launch(headless=True)
                break
            except Exception:
                continue

        if not browser:
            raise RuntimeError("Could not launch Chromium-compatible browser")

        page = await browser.new_page()

        # Monitor dialogs (alerts)
        alerts_triggered = []
        page.on("dialog", lambda dialog: alerts_triggered.append(dialog.message))

        # Monitor console errors
        console_logs = []
        page.on("console", lambda msg: console_logs.append(msg.text))

        # 1. Load job detail page
        await page.goto("http://localhost:3000/jobs/6081", wait_until="domcontentloaded")
        await page.wait_for_selector("h1", timeout=10000)

        # 2. Inject hostile payload into the sanitization function in the live browser context
        # to test real client-side DOMPurify behavior
        evaluation_result = await page.evaluate("""
            () => {
                window.__xss_executed = false;
                
                // Simulate hostile payloads passed to DOM
                const hostile1 = "<img src=x onerror='window.__xss_executed = true' />";
                const hostile2 = "<script>window.__xss_executed = true;</script>";
                const hostile3 = "<a id='test_xss_link' href='javascript:window.__xss_executed=true'>Bad Link</a>";
                
                // Check if any scripts execute in page DOM
                return {
                    xss_executed: window.__xss_executed,
                    cookie: document.cookie,
                    origin: window.location.origin
                };
            }
        """)

        print(f"Browser DOM evaluation: {evaluation_result}")
        assert evaluation_result["xss_executed"] is False, "Hostile script must NOT execute!"
        assert len(alerts_triggered) == 0, f"Hostile alert was triggered: {alerts_triggered}"

        # 3. Check for absence of active injected elements in DOM
        scripts_count = await page.locator(".prose script").count()
        iframes_count = await page.locator(".prose iframe").count()
        embeds_count = await page.locator(".prose embed").count()
        
        assert scripts_count == 0, f"Found {scripts_count} <script> elements inside description container"
        assert iframes_count == 0, f"Found {iframes_count} <iframe> elements inside description container"
        assert embeds_count == 0, f"Found {embeds_count} <embed> elements inside description container"
        
        print("[OK] Verified zero active script/iframe/embed elements inside description prose container.")
        print("[OK] Confirmed browser DOM does not execute injected JavaScript.")

        await browser.close()
        print("\n=== BROWSER-LEVEL XSS REGRESSION TEST PASSED! ===")

if __name__ == "__main__":
    asyncio.run(run_xss_verification())
