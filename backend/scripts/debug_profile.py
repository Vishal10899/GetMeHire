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
    page.click('button[type="submit"]')
    page.wait_for_timeout(3000)
    print('Current URL after submit:', page.url)
    
    page.goto('http://localhost:3000/profile', wait_until='domcontentloaded')
    page.wait_for_timeout(3000)
    print('Profile URL:', page.url)
    print('Loading text present?', 'Loading candidate workspace' in page.content())
    tabs = page.query_selector_all('[role="tab"]')
    print('Tabs count:', len(tabs))
    for t in tabs:
        print('  Tab text:', repr(t.inner_text()))
    b.close()
