import asyncio
from playwright.async_api import async_playwright

async def find_overflow():
    async with async_playwright() as p:
        browser = await p.chromium.launch(channel="msedge", headless=True)
        context = await browser.new_context(viewport={"width": 375, "height": 812})
        page = await context.new_page()
        await page.goto("http://localhost:3000/login", wait_until="domcontentloaded")
        await page.wait_for_timeout(500)
        await page.click("button:has-text('Demo Candidate')")
        await page.click("button[type='submit']")
        await page.wait_for_url("**/jobs", timeout=10000)
        await page.goto("http://localhost:3000/profile", wait_until="domcontentloaded")
        await page.wait_for_timeout(1500)
        
        overflowing = await page.evaluate("""() => {
            const docWidth = document.documentElement.clientWidth;
            const elements = Array.from(document.querySelectorAll('*'));
            const bad = [];
            for (const el of elements) {
                const rect = el.getBoundingClientRect();
                if (rect.right > docWidth + 1) {
                    bad.push({
                        tag: el.tagName,
                        className: (el.className || '').toString().substring(0, 50),
                        right: Math.round(rect.right),
                        width: Math.round(rect.width),
                        docWidth: docWidth,
                        text: (el.innerText || '').substring(0, 30).trim()
                    });
                }
            }
            return bad.slice(0, 8);
        }""")
        for item in overflowing:
            print(item)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_overflow())
