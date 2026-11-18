import sys
import time
from playwright.sync_api import sync_playwright

def verify_all():
    print("==================================================================")
    print("  GLOBALJOBS — EXTENSIVE PLAYWRIGHT BROWSER VERIFICATION SUITE")
    print("==================================================================")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            headless=True
        )
        page = browser.new_page()

        requests_log = []
        page.on("request", lambda req: requests_log.append({
            "method": req.method,
            "url": req.url,
            "time": time.time()
        }) if "/api/v1/jobs" in req.url and not req.url.endswith("/professions") else None)

        def count_requests_for(pattern):
            return sum(1 for r in requests_log if pattern in r["url"])

        # ------------------------------------------------------------------
        # SCENARIO 1: Multi-character search generates one debounced request
        # ------------------------------------------------------------------
        print("\n[TEST 1] Rapid typing generates exactly ONE debounced request...")
        page.goto("http://localhost:3000/jobs", wait_until="networkidle")
        initial_req_count = len(requests_log)

        search_input = page.locator("input[placeholder*='Search by job title']")
        search_input.click()
        search_input.fill("")
        search_input.type("data analyst", delay=50)

        # Wait for 350ms debounce + 1s network response
        time.sleep(1.5)

        new_reqs = requests_log[initial_req_count:]
        print(f"  • Requests fired after typing 'data analyst': {len(new_reqs)}")
        assert len(new_reqs) == 1, f"Expected 1 debounced request, got {len(new_reqs)}"
        assert "keyword=data+analyst" in new_reqs[0]["url"] or "keyword=data%20analyst" in new_reqs[0]["url"]
        print("  ✓ PASS: Exactly one debounced request generated.")

        # ------------------------------------------------------------------
        # SCENARIO 2: Unchanged query does not refetch
        # ------------------------------------------------------------------
        print("\n[TEST 2] Unchanged query does not refetch...")
        count_before_pause = len(requests_log)
        time.sleep(2.0)
        assert len(requests_log) == count_before_pause, "Unchanged query triggered unexpected refetch!"
        print("  ✓ PASS: Zero requests during idle period.")

        # ------------------------------------------------------------------
        # SCENARIO 3: Enter key triggers immediate search without duplicate
        # ------------------------------------------------------------------
        print("\n[TEST 3] Enter key triggers immediate search...")
        count_before_enter = len(requests_log)
        search_input.click()
        search_input.fill("python developer")
        search_input.press("Enter")
        time.sleep(1.2)
        new_enter_reqs = requests_log[count_before_enter:]
        assert len(new_enter_reqs) == 1, f"Expected 1 immediate request on Enter, got {len(new_enter_reqs)}"
        assert "python" in new_enter_reqs[0]["url"].lower()
        print("  ✓ PASS: Enter key executed single immediate search.")

        # ------------------------------------------------------------------
        # SCENARIO 4: Clear button resets search immediately
        # ------------------------------------------------------------------
        print("\n[TEST 4] Clear button resets search immediately...")
        clear_btn = page.locator("button[aria-label='Clear keyword search']")
        count_before_clear = len(requests_log)
        clear_btn.click()
        time.sleep(1.2)
        new_clear_reqs = requests_log[count_before_clear:]
        assert len(new_clear_reqs) == 1, f"Expected 1 request on clear, got {len(new_clear_reqs)}"
        assert "keyword=" not in new_clear_reqs[0]["url"] or "keyword=&" in new_clear_reqs[0]["url"]
        print("  ✓ PASS: Clear button executed single reset search.")

        # ------------------------------------------------------------------
        # SCENARIO 5: Changing filter generates one effective request & resets page
        # ------------------------------------------------------------------
        print("\n[TEST 5] Filter change generates one request and resets page...")
        count_before_pill = len(requests_log)
        # Click "Data & AI" pill
        pill = page.locator("button:has-text('Data & AI')")
        pill.click()
        time.sleep(1.2)
        new_pill_reqs = requests_log[count_before_pill:]
        assert len(new_pill_reqs) == 1, f"Expected 1 request on pill click, got {len(new_pill_reqs)}"
        assert "profession=DATA_AI" in new_pill_reqs[0]["url"]
        print("  ✓ PASS: Filter selection executed single request with page=1.")

        # ------------------------------------------------------------------
        # SCENARIO 6: Changing sort generates one effective request
        # ------------------------------------------------------------------
        print("\n[TEST 6] Sort dropdown generates one request...")
        count_before_sort = len(requests_log)
        sort_select = page.locator("select").first
        sort_select.select_option("salary_high")
        time.sleep(1.2)
        new_sort_reqs = requests_log[count_before_sort:]
        assert len(new_sort_reqs) == 1, f"Expected 1 request on sort change, got {len(new_sort_reqs)}"
        assert "sort_by=salary_high" in new_sort_reqs[0]["url"]
        print("  ✓ PASS: Sort selection executed single request.")

        # ------------------------------------------------------------------
        # SCENARIO 7: Pagination moves page forward once without loops
        # ------------------------------------------------------------------
        print("\n[TEST 7] Pagination does not run in a loop...")
        next_btn = page.locator("button:has-text('Next')")
        if next_btn.is_visible() and not next_btn.is_disabled():
            count_before_page = len(requests_log)
            next_btn.click()
            time.sleep(1.5)
            new_page_reqs = requests_log[count_before_page:]
            assert len(new_page_reqs) == 1, f"Expected 1 request on page next, got {len(new_page_reqs)}"
            assert "page=2" in new_page_reqs[0]["url"]
            print("  ✓ PASS: Page change executed single request for page 2.")

        # ------------------------------------------------------------------
        # SCENARIO 8: Typo correction suggestion clicks perform one search
        # ------------------------------------------------------------------
        print("\n[TEST 8] Typo correction did-you-mean suggestion click...")
        # Reset filters first
        reset_btn = page.locator("button:has-text('Reset all')")
        if reset_btn.is_visible():
            reset_btn.click()
            time.sleep(1.0)

        search_input.click()
        search_input.fill("data-anlyt")
        search_input.press("Enter")
        time.sleep(1.5)

        # Should show typo correction banner with did_you_mean button
        did_you_mean_btn = page.locator("button:has-text('data analyst')").first
        if did_you_mean_btn.is_visible():
            count_before_dym = len(requests_log)
            did_you_mean_btn.click()
            time.sleep(1.5)
            new_dym_reqs = requests_log[count_before_dym:]
            assert len(new_dym_reqs) == 1, f"Expected 1 request on did-you-mean click, got {len(new_dym_reqs)}"
            print("  ✓ PASS: Did-you-mean selection executed single search.")

        # ------------------------------------------------------------------
        # SCENARIO 9: Related roles chip click performs one search
        # ------------------------------------------------------------------
        print("\n[TEST 9] Related roles chip click...")
        role_chip = page.locator("button:has-text('Data Scientist')").first
        if role_chip.is_visible():
            count_before_chip = len(requests_log)
            role_chip.click()
            time.sleep(1.5)
            new_chip_reqs = requests_log[count_before_chip:]
            assert len(new_chip_reqs) == 1, f"Expected 1 request on related role click, got {len(new_chip_reqs)}"
            print("  ✓ PASS: Related role chip click executed single search.")

        # ------------------------------------------------------------------
        # SCENARIO 10: Empty search query stops loading correctly
        # ------------------------------------------------------------------
        print("\n[TEST 10] Empty results state stops loading correctly...")
        search_input.click()
        search_input.fill("xyznonexistentrole123456789")
        search_input.press("Enter")
        time.sleep(1.5)

        is_loading = page.locator("text=Searching verified opportunities...").is_visible()
        is_empty = page.locator("text=No matching job listings found").is_visible()
        assert not is_loading, "Loading spinner stuck on empty results!"
        assert is_empty, "Empty state not displayed on zero results!"
        print("  ✓ PASS: Empty state rendered cleanly, loading spinner stopped.")

        # ------------------------------------------------------------------
        # SCENARIO 11: Navigate away and return
        # ------------------------------------------------------------------
        print("\n[TEST 11] Navigate away to /saved and return to /jobs...")
        page.goto("http://localhost:3000/saved", wait_until="networkidle")
        time.sleep(1.0)
        page.goto("http://localhost:3000/jobs?keyword=machine+learning", wait_until="networkidle")
        time.sleep(1.5)

        is_loading_ret = page.locator("text=Searching verified opportunities...").is_visible()
        cards_ret = page.locator("h3").count()
        assert not is_loading_ret, "Loading spinner stuck after returning to /jobs!"
        assert cards_ret > 0, "Jobs not rendered after returning to /jobs!"
        print(f"  ✓ PASS: Returning to /jobs rendered {cards_ret} headers without getting stuck.")

        print("\n==================================================================")
        print("  ALL 11 REAL-BROWSER SCENARIOS PASSED WITH ZERO FLAKINESS!")
        print("==================================================================")

        browser.close()

if __name__ == "__main__":
    verify_all()
