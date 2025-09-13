#!/usr/bin/env python3
"""
Debug the selector and clicking issues.
"""

import asyncio
from playwright.async_api import async_playwright

async def test_selectors():
    """Test the selectors that are causing issues."""
    
    # Test selectors from the error
    test_selectors = [
        "a[href*='#menu'], a:has-text('ORDER NOW')",
        "div.display-name.mealBurrito:nth-child(1)",
        "a[href*='#menu']",
        "a:has-text('ORDER NOW')",
        "div.display-name.mealBurrito"
    ]
    
    print("🔍 Testing Playwright selector parsing...")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Load a simple test page
        await page.set_content("""
        <html>
        <body>
            <a href="#menu">Menu</a>
            <a href="#order">ORDER NOW</a>
            <div class="display-name mealBurrito">Burrito</div>
            <div class="display-name mealBurrito">Burrito Bowl</div>
        </body>
        </html>
        """)
        
        for selector in test_selectors:
            try:
                print(f"\n🎯 Testing: {selector}")
                
                # Test if selector is valid
                locator = page.locator(selector)
                count = await locator.count()
                print(f"   Found: {count} elements")
                
                if count > 0:
                    # Test .first()
                    first_locator = locator.first()
                    text = await first_locator.text_content()
                    print(f"   First element text: '{text}'")
                    
                    # Test click (without actually clicking)
                    print(f"   Locator type: {type(first_locator)}")
                    print(f"   ✅ Selector syntax is valid")
                else:
                    print(f"   ⚠️  No elements found")
                    
            except Exception as e:
                print(f"   ❌ Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_selectors())
