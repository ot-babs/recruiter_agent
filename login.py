import os, re, json, asyncio
from playwright.async_api import async_playwright

EMAIL = os.getenv("LINKEDIN_EMAIL")
PWD   = os.getenv("LINKEDIN_PASSWORD")
if not (EMAIL and PWD):
    raise RuntimeError("Set LINKEDIN_EMAIL and LINKEDIN_PASSWORD env vars!")

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--disable-blink-features=AutomationControlled"])
        ctx = await browser.new_context()
        page = await ctx.new_page()

        await page.goto("https://www.linkedin.com/login")
        await page.fill("#username", EMAIL)
        await page.fill("#password", PWD)

        # wait until we leave /login for either the feed or a profile page
        async with page.expect_navigation(
                url=re.compile(r"https://www\.linkedin\.com/(feed|in/).*")):
            await page.click('button[type="submit"]')

        print("✅ Logged in as:", await page.title())
        with open("linkedin_cookies.json", "w") as f:
            json.dump(await ctx.cookies(), f, indent=2)

        await browser.close()

asyncio.run(main())
