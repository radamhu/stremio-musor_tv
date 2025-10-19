"""Debug script to inspect musor.tv HTML structure."""
import asyncio
from playwright.async_api import async_playwright


async def inspect_page(url: str):
    """Inspect page structure to find correct selectors."""
    print(f"\n{'='*80}")
    print(f"Inspecting: {url}")
    print('='*80)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
        page = await browser.new_page()
        
        try:
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # Try to accept cookies - try multiple selectors
            try:
                await asyncio.sleep(1)  # Wait for cookie dialog to appear
                
                cookie_selectors = [
                    'button:has-text("Elfogadom")',
                    'button:has-text("Accept")',
                    'button:has-text("Egyetértek")',
                    'button[class*="agree"]',
                    'button[class*="accept"]',
                    '.qc-cmp2-summary-buttons button'
                ]
                
                clicked = False
                for selector in cookie_selectors:
                    try:
                        btn = page.locator(selector).first
                        if await btn.count() > 0:
                            await btn.click(timeout=2000)
                            print(f"✓ Cookie accepted via: {selector}")
                            clicked = True
                            await asyncio.sleep(2)  # Wait for content to load
                            break
                    except:
                        continue
                
                if not clicked:
                    print("- No cookie button found")
            except Exception as e:
                print(f"- Cookie handling error: {e}")
            
            # Get page title
            title = await page.title()
            print(f"\nPage title: {title}")
            
            # Try different common selectors
            selectors = [
                "article",
                "div[class*='card']",
                "div[class*='program']",
                "div[class*='item']",
                "div[class*='show']",
                "div[class*='movie']",
                "li[class*='program']",
                "li[class*='item']",
                ".broadcast",
                "[data-program]",
                "[data-broadcast]",
            ]
            
            print("\nTesting selectors:")
            for selector in selectors:
                count = await page.locator(selector).count()
                if count > 0:
                    print(f"  ✓ {selector}: {count} elements")
                    
                    # Get first element details
                    if count > 0:
                        first = page.locator(selector).first
                        classes = await first.get_attribute("class")
                        print(f"    Classes: {classes}")
                        
                        # Try to find title/text
                        text = await first.text_content()
                        if text:
                            text_preview = text.strip()[:100]
                            print(f"    Text preview: {text_preview}...")
                        break
            
            # Wait a bit more for dynamic content
            await asyncio.sleep(3)
            
            # Get body HTML snippet - look for main content area
            print("\n\nLooking for main content containers...")
            content_selectors = ["main", "#content", "#main", ".content", ".main", "div[id*='app']", "div[class*='container']"]
            for sel in content_selectors:
                count = await page.locator(sel).count()
                if count > 0:
                    print(f"  Found: {sel} ({count} elements)")
                    try:
                        html = await page.locator(sel).first.evaluate("el => el.innerHTML")
                        print(f"  Content preview (first 1000 chars):")
                        print(html[:1000])
                        print("\n  ... (truncated)\n")
                        break
                    except:
                        pass
            
            # Take a screenshot for manual inspection
            screenshot_path = f"/tmp/musor_debug_{url.split('/')[-1]}.png"
            await page.screenshot(path=screenshot_path, full_page=True)
            print(f"\n📸 Screenshot saved to: {screenshot_path}")
            
        except Exception as e:
            print(f"ERROR: {e}")
        finally:
            await browser.close()


async def main():
    """Run inspection on both pages."""
    pages = [
        "https://musor.tv/most/tvben",
        "https://musor.tv/filmek"
    ]
    
    for url in pages:
        await inspect_page(url)


if __name__ == "__main__":
    asyncio.run(main())
