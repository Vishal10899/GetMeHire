import sys
import time
from playwright.sync_api import sync_playwright

def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True
        )
        page = browser.new_page()

        requests_log = []
        page.on("request", lambda req: (print(f"[REQ {len(requests_log)+1}] {req.method} {req.url}"), requests_log.append(req.url)) if "/api/v1/jobs" in req.url else None)
        page.on("console", lambda msg: print(f"[CONSOLE] {msg.type}: {msg.text}"))

        print("\n=== STEP 1: Navigate to /jobs ===")
        page.goto("http://localhost:3000/jobs", wait_until="networkidle")

        print("\n=== STEP 2: Type 'data-anlyt' into search input ===")
        search_input = page.locator("input[placeholder*='Search by job title']")
        search_input.click()
        search_input.fill("")
        
        # Type character by character with 100ms delay
        search_input.type("data-anlyt", delay=100)

        print("\n=== STEP 3: Wait 5 seconds after typing ===")
        time.sleep(5)

        # Check skeleton/loading state
        is_loading_visible = page.locator("text=Searching verified opportunities...").is_visible()
        print(f"Is 'Searching verified opportunities...' visible? {is_loading_visible}")

        # Check if job cards rendered
        cards_count = page.locator("h3").count()
        print(f"Number of h3 elements (job titles / headers): {cards_count}")

        print(f"\n--- Total /api/v1/jobs requests: {len(requests_log)} ---")
        for i, u in enumerate(requests_log, 1):
            print(f"{i}. {u}")

        browser.close()

if __name__ == "__main__":
    run()
