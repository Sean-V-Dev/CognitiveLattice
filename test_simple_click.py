#!/usr/bin/env python3
"""
Simple test of Playwright compound selectors.
"""

import asyncio
from playwright.async_api import async_playwright

async def test_compound_selector():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        
        # Simple test page
        await page.set_content("""
        <html>
        <body>
            <a href="#menu">Menu Link</a>
            <button>ORDER NOW</button>
        </body>
        </html>
        """)
        
        # Test individual selectors first
        print("🔍 Testing individual selectors:")
        
        try:
            menu_link = page.locator("a[href*='#menu']")
            count1 = await menu_link.count()
            print(f"a[href*='#menu']: {count1} elements")
            
            order_btn = page.locator("a:has-text('ORDER NOW')")
            count2 = await order_btn.count()
            print(f"a:has-text('ORDER NOW'): {count2} elements")
            
            # Test compound selector
            print("\n🔍 Testing compound selector:")
            compound = page.locator("a[href*='#menu'], a:has-text('ORDER NOW')")
            count3 = await compound.count()
            print(f"Compound: {count3} elements")
            
            # Test .first
            if count3 > 0:
                first = compound.first
                text = await first.text_content()
                print(f"First element text: '{text}'")
                
                # Simulate click
                print("Testing click...")
                await first.click()
                print("✅ Click successful")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            traceback.print_exc()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_compound_selector())
