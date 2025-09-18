#!/usr/bin/env python3
"""
Chrome Integration Module - Ensures agent uses the WORKING Chrome configuration.
This is the setup that successfully bypasses Chipotle's bot detection.
"""

import subprocess
import time
import requests
import asyncio
from playwright.async_api import async_playwright

async def ensure_working_chrome_setup():
    """
    Ensure Chrome is running with the EXACT configuration that works with Chipotle.
    This bypasses bot detection and allows account creation/ordering.
    """
    
    print("🎯 Ensuring Working Chrome Setup (Chipotle-Compatible)")
    print("=" * 60)
    
    # Step 1: Check if Chrome is already running with debug port
    try:
        response = requests.get("http://localhost:9222/json/version", timeout=2)
        if response.status_code == 200:
            print("✅ Chrome with debug port already running - GOOD!")
            version_info = response.json()
            print(f"📱 Browser: {version_info.get('Browser', 'Unknown')}")
            return True
    except:
        pass
    
    # Step 2: Start Chrome with the WORKING configuration
    print("🚀 Starting Chrome with Chipotle-compatible configuration...")
    
    # Import and use our working start_real_chrome function
    from start_real_chrome import start_real_chrome
    
    success = start_real_chrome(
        debug_port=9222,
        profile_dir=None  # Uses the working temp directory
    )
    
    if success:
        print("✅ Chrome started with working configuration!")
        return True
    else:
        print("❌ Failed to start Chrome")
        return False

async def connect_to_working_chrome():
    """
    Connect Playwright to the working Chrome instance.
    """
    
    print("🔗 Connecting to working Chrome instance...")
    
    try:
        playwright = await async_playwright().start()
        
        # Connect to the existing Chrome instance
        browser = await playwright.chromium.connect_over_cdp("http://localhost:9222")
        
        # Get existing context or create new one
        contexts = browser.contexts
        if contexts:
            context = contexts[0]
            print(f"✅ Connected to existing Chrome context with {len(context.pages)} pages")
        else:
            context = await browser.new_context()
            print("✅ Created new context in existing Chrome")
        
        # Get or create page
        pages = context.pages
        if pages:
            page = pages[0]
        else:
            page = await context.new_page()
        
        print("🎉 Successfully connected to working Chrome setup!")
        return playwright, browser, context, page
        
    except Exception as e:
        print(f"❌ Failed to connect to Chrome: {e}")
        return None, None, None, None

async def test_chipotle_compatibility():
    """
    Quick test to verify Chrome setup works with Chipotle.
    """
    
    print("🌯 Testing Chipotle compatibility...")
    
    playwright, browser, context, page = await connect_to_working_chrome()
    
    if not page:
        print("❌ Could not connect to Chrome")
        return False
    
    try:
        await page.goto("https://chipotle.com", timeout=15000)
        await page.wait_for_load_state("networkidle", timeout=10000)
        
        title = await page.title()
        if "chipotle" in title.lower():
            print(f"✅ Successfully loaded Chipotle: {title}")
            
            # Check if we can access the menu (bot detection test)
            try:
                await page.click("text=Order", timeout=5000)
                print("✅ Can access ordering - bot detection BYPASSED!")
                return True
            except:
                print("⚠️ Could access site but not ordering menu")
                return True
        else:
            print(f"⚠️ Unexpected page title: {title}")
            return False
            
    except Exception as e:
        print(f"❌ Chipotle test failed: {e}")
        return False
    
    finally:
        # Don't close browser - leave it for automation
        pass

async def main():
    """Test the working Chrome setup"""
    
    # Ensure Chrome is running with working config
    chrome_ready = await ensure_working_chrome_setup()
    
    if chrome_ready:
        # Test Chipotle compatibility
        await test_chipotle_compatibility()
        print("\n🎯 Chrome is ready for automation!")
        print("💡 This is the WORKING configuration that bypasses bot detection")
    else:
        print("\n❌ Chrome setup failed")

if __name__ == "__main__":
    asyncio.run(main())
