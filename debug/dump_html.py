"""Simple HTML dumper to see actual page structure."""
import asyncio
from playwright.async_api import async_playwright


async def dump_html(url: str):
    """Dump full HTML after page loads."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Accept cookies
            await asyncio.sleep(1)
            try:
                await page.click('button:has-text("Elfogadom")', timeout=2000)
                await asyncio.sleep(3)
            except:
                pass
            
            # Get full HTML
            html = await page.content()
            
            # Save to file
            filename = f"/tmp/musor_{url.split('/')[-1]}.html"
            with open(filename, "w", encoding="utf-8") as f:
                f.write(html)
            
            print(f"✓ Saved HTML to: {filename}")
            print(f"  Size: {len(html)} bytes")
            
            # Look for anything that might be a program listing
            if "program" in html.lower():
                print("  Found 'program' in HTML")
            if "film" in html.lower():
                count = html.lower().count("film")
                print(f"  Found 'film' {count} times in HTML")
            if "channel" in html.lower() or "csatorna" in html.lower():
                print("  Found channel references")
                
        finally:
            await browser.close()


async def main():
    await dump_html("https://musor.tv/filmek")
    await dump_html("https://musor.tv/most/tvben")


if __name__ == "__main__":
    asyncio.run(main())
