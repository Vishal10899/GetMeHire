from playwright.sync_api import sync_playwright
import time

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=r'C:\Program Files\Google\Chrome\Application\chrome.exe', headless=True)
    page = b.new_page()
    page.goto('http://localhost:3000/register', wait_until='domcontentloaded')
    page.wait_for_timeout(1000)
    page.fill('input[type="text"]', 'Sarah Chen')
    page.fill('input[type="email"]', f'sarah_{int(time.time())}@example.com')
    pw = page.query_selector_all('input[type="password"]')
    pw[0].fill('GlobalJobsPass2026!')
    pw[1].fill('GlobalJobsPass2026!')
    page.click('input[type="checkbox"]')
    
    # Listen to console
    page.on('console', lambda msg: print('BROWSER CONSOLE:', msg.type, msg.text))
    
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    print('URL after submit:', page.url)
    err = page.query_selector('.bg-red-50')
    if err:
        print('Error text:', err.inner_text())
    b.close()
