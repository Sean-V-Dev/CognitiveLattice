#!/usr/bin/env python3
"""
Test the overlay handling fix with a simple Chipotle test.
"""

import asyncio
from tools.web_automation.browser_engine_tool import BrowserEngineTool

async def test_overlay_fix():
    """Test clicking elements with overlay interference."""
    
    browser = BrowserEngineTool(enable_stealth=False, profile_name="overlay_test")
    
    try:
        print("🧪 Testing overlay handling fix...")
        
        # Initialize browser
        result = await browser.initialize_browser(headless=False, browser_type="chromium")
        print(f"🌐 Browser init: {result.get('status')}")
        
        if result.get('status') != 'success':
            print(f"❌ Failed to initialize browser: {result}")
            return
        
        # Navigate to Chipotle
        nav_result = await browser.navigate_to_url("https://chipotle.com")
        print(f"🌐 Navigation: {nav_result.get('status')}")
        
        # Wait a moment for page to load
        await asyncio.sleep(3)
        
        # Test clicking ORDER NOW (compound selector)
        print("🎯 Testing ORDER NOW click...")
        order_selector = "a[href*='menu'], a:has-text('Menu'), a:has-text('ORDER NOW')"
        order_result = await browser.click_element(order_selector)
        print(f"🖱️  ORDER NOW result: {order_result.get('status')} - {order_result.get('message')}")
        
        # Wait for navigation
        await asyncio.sleep(4)
        
        # Test clicking Burrito Bowl
        print("🎯 Testing Bowl selection...")
        bowl_selector = "div.top-level-menu:has-text('Burrito BowlOrder')"
        bowl_result = await browser.click_element(bowl_selector)
        print(f"🖱️  Bowl result: {bowl_result.get('status')} - {bowl_result.get('message')}")
        
        # Wait for page to load
        await asyncio.sleep(3)
        
        # Test clicking Chicken (this should now work with our overlay handling)
        print("🎯 Testing Chicken selection with overlay handling...")
        chicken_selector = "div.selection-icon-button.optionChicken"
        chicken_result = await browser.click_element(chicken_selector)
        print(f"🖱️  Chicken result: {chicken_result.get('status')} - {chicken_result.get('message')}")
        
        # Wait to observe
        await asyncio.sleep(3)
        
        print("✅ Test completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        try:
            await browser.close_browser(save_state=False)
            print("🧹 Browser closed")
        except Exception as e:
            print(f"⚠️ Error closing browser: {e}")

if __name__ == "__main__":
    asyncio.run(test_overlay_fix())
