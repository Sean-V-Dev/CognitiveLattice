#!/usr/bin/env python3
"""
Test script to verify breadcrumb integration is working correctly.
Runs a simple test to ensure breadcrumbs appear in prompts.
"""

import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_prompt_building_with_breadcrumbs():
    """Test that prompt builder correctly includes breadcrumb context."""
    print("🔍 Testing prompt building with breadcrumbs...")
    
    try:
        from tools.web_automation.prompt_builder import build_reasoning_prompt
        from tools.web_automation.dom_processor import PageContext
        
        # Create a mock page context
        ctx = PageContext(
            url="https://test.com",
            title="Test Page",
            raw_dom="<div>Test DOM</div>",
            skeleton="<div>Test DOM</div>",
            signature="test123",
            step_number=3,
            total_steps=5,
            overall_goal="Test overall goal"
        )
        
        # Test with breadcrumbs
        test_breadcrumbs = [
            "Step 1: Navigated to homepage",
            "Step 2: Clicked menu button"
        ]
        
        # Build prompt with breadcrumbs
        prompt = build_reasoning_prompt(
            goal="Test current step",
            ctx=ctx,
            recent_actions=[],
            breadcrumbs=test_breadcrumbs
        )
        
        print(f"🔍 Breadcrumbs passed: {test_breadcrumbs}")
        print(f"🔍 Prompt length: {len(prompt)}")
        
        # Check if breadcrumbs appear in prompt
        if "Progress So Far" in prompt:
            print("✅ 'Progress So Far' section found in prompt")
            
            if "Step 1: Navigated to homepage" in prompt:
                print("✅ Breadcrumb 1 found in prompt")
            else:
                print("❌ Breadcrumb 1 NOT found in prompt")
                return False
                
            if "Step 2: Clicked menu button" in prompt:
                print("✅ Breadcrumb 2 found in prompt")
            else:
                print("❌ Breadcrumb 2 NOT found in prompt")
                return False
                
            return True
        else:
            print("❌ 'Progress So Far' section NOT found in prompt")
            # Search for breadcrumb content directly
            if "Step 1: Navigated to homepage" in prompt:
                print("🤔 Found breadcrumb content but not 'Progress So Far' header")
            else:
                print("🤔 No breadcrumb content found at all")
            
            # Print a larger portion of the prompt to debug
            print(f"Full prompt:\n{prompt}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run the breadcrumb prompt test."""
    print("🚀 Testing breadcrumb integration in prompts...")
    
    success = test_prompt_building_with_breadcrumbs()
    
    if success:
        print("✅ Breadcrumb prompt integration test PASSED!")
        print("📢 Breadcrumbs should now appear in web automation prompts")
        return 0
    else:
        print("❌ Breadcrumb prompt integration test FAILED!")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
