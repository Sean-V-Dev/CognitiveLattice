#!/usr/bin/env python3
"""
Test script to verify the scrolling bug fix.
This will test the improved click handling for compound selectors.
"""

import asyncio
from tools.web_automation.browser_engine_tool import BrowserEngineTool

async def test_click_fix():
    """Test the improved click handling."""
    
    browser = BrowserEngineTool(enable_stealth=False, profile_name="test_debug")
    
    try:
        print("🧪 Testing improved click handling...")
        
        # Initialize browser
        result = await browser.initialize_browser(headless=False, browser_type="chromium")
        print(f"🌐 Browser init: {result.get('status')}")
        
        if result.get('status') != 'success':
            print(f"❌ Failed to initialize browser: {result}")
            return
        
        # Navigate to test site
        nav_result = await browser.navigate_to_url("https://chipotle.com")
        print(f"🌐 Navigation: {nav_result.get('status')}")
        
        # Test compound selector (this should now handle multiple matches gracefully)
        compound_selector = "a[href*='menu'], a:has-text('Menu'), a:has-text('ORDER NOW')"
        print(f"🎯 Testing compound selector: {compound_selector}")
        
        click_result = await browser.click_element(compound_selector)
        print(f"🖱️  Click result: {click_result}")
        
        # Wait a moment to observe behavior
        await asyncio.sleep(3)
        
        print("✅ Test completed successfully!")
        
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
    asyncio.run(test_click_fix())
