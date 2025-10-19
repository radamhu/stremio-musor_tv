"""Debug script v2 - Find actual program elements."""
import asyncio
from playwright.async_api import async_playwright


async def find_programs(url: str):
    """Find actual program/show elements."""
    print(f"\n{'='*80}")
    print(f"Analyzing: {url}")
    print('='*80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox"])  # headless=False to see what's happening
        page = await browser.new_page()
        
        try:
            print("Loading page...")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Handle cookies
            await asyncio.sleep(1)
            try:
                btn = page.locator('button:has-text("Elfogadom")').first
                if await btn.count() > 0:
                    await btn.click()
                    print("✓ Cookie accepted")
                    await asyncio.sleep(3)
            except:
                pass
            
            # Look for tables (musor.tv likely uses tables for TV schedules)
            print("\nLooking for tables...")
            tables = page.locator("table")
            table_count = await tables.count()
            print(f"Found {table_count} tables")
            
            # Look for program-related elements
            print("\nSearching for program elements...")
            program_selectors = [
                "tr[class*='program']",
                "tr[class*='show']",
                "tr[class*='event']",
                "div[class*='program']",
                "div[class*='broadcast']",
                "a[href*='/musor/']",
                "a[href*='musor']",
            ]
            
            for sel in program_selectors:
                count = await page.locator(sel).count()
                if count > 0:
                    print(f"\n✓ Found {count} elements with selector: {sel}")
                    
                    # Get details of first 3 elements
                    for i in range(min(3, count)):
                        elem = page.locator(sel).nth(i)
                        text = await elem.text_content()
                        classes = await elem.get_attribute("class")
                        href = await elem.get_attribute("href")
                        print(f"  [{i}] Classes: {classes}")
                        if href:
                            print(f"      Href: {href}")
                        print(f"      Text: {text[:100] if text else 'N/A'}...")
            
            # Get all links and filter for program links
            print("\n\nAnalyzing all links...")
            links = page.locator("a")
            link_count = await links.count()
            print(f"Total links: {link_count}")
            
            program_links = []
            for i in range(min(50, link_count)):
                href = await links.nth(i).get_attribute("href")
                text = await links.nth(i).text_content()
                if href and ("/musor/" in href or "channel" in href.lower()):
                    program_links.append((href, text))
            
            if program_links:
                print(f"\nFound {len(program_links)} program-related links:")
                for href, text in program_links[:10]:
                    print(f"  {href} - {text[:50] if text else 'N/A'}")
            
            # Keep browser open for manual inspection
            print("\n\n⏸️  Browser window kept open for 30 seconds for manual inspection...")
            await asyncio.sleep(30)
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await browser.close()


async def main():
    """Run analysis."""
    await find_programs("https://musor.tv/filmek")


if __name__ == "__main__":
    asyncio.run(main())
