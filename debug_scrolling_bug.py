#!/usr/bin/env python3
"""
Debug script to trace the scrolling bug in web automation.
This will help us identify where the "scroll down twice, up twice" behavior comes from.
"""

import asyncio
from tools.web_automation.cognitive_lattice_web_coordinator import execute_cognitive_web_task
from core.external_api_client import ExternalAPIClient
from core.cognitive_lattice import CognitiveLattice, SessionManager

async def debug_scrolling():
    """Test the web automation flow to identify scrolling behavior."""
    
    # Initialize components
    session_manager = SessionManager()
    
    try:
        external_api = ExternalAPIClient()
        print("🌐 External API client initialized")
    except Exception as e:
        print(f"⚠️ Could not initialize External API Client: {e}")
        external_api = None
    
    # Simple test goal
    goal = "go to chipotle.com and click on 'ORDER NOW'"
    url = "https://chipotle.com"
    
    print(f"🧪 Testing goal: {goal}")
    print(f"🌐 Testing URL: {url}")
    print("=" * 60)
    
    try:
        result = await execute_cognitive_web_task(
            goal=goal,
            url=url,
            external_client=external_api,
            cognitive_lattice=session_manager.lattice
        )
        
        print(f"✅ Test completed. Result: {result}")
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(debug_scrolling())
