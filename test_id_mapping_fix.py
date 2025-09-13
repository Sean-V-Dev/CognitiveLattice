#!/usr/bin/env python3
"""
Test script to validate the ID-to-selector mapping fix.
Tests that candidate IDs are correctly assigned and mapped during execution.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.web_automation.browser_controller import BrowserController
from tools.web_automation.dom_processor import summarize_interactive_elements
from tools.web_automation.prompt_builder import build_reasoning_prompt
from tools.web_automation.models import PageContext

async def test_id_mapping_fix():
    """Test that candidate IDs are correctly assigned and mapped."""
    
    browser_controller = BrowserController()
    
    try:
        # Initialize browser and navigate to Chipotle
        await browser_controller.initialize()
        
        print("🌐 Navigating to Chipotle...")
        await browser_controller.navigate("https://chipotle.com")
        
        # Get page object from browser_controller internals
        page = browser_controller.page
        
        # Get DOM context with ID assignments
        print("\n🔍 Processing DOM and assigning candidate IDs...")
        ctx = await summarize_interactive_elements(page)
        
        # Show first few candidates
        print(f"\n📋 First 10 candidates from ctx.interactive:")
        for i in range(min(10, len(ctx.interactive))):
            element = ctx.interactive[i]
            candidate_id = getattr(element, 'candidate_id', 'MISSING')
            element_text = element.text[:50] if element.text else 'No text'
            print(f"  Index {i}: candidate_id={candidate_id}, text='{element_text}'")
        
        # Build prompt to see what agent gets
        goal = "Find the menu or order button"
        prompt = build_reasoning_prompt(goal, ctx)
        
        print(f"\n📝 Candidate section from prompt (first 10):")
        # Extract candidates section
        lines = prompt.split('\n')
        in_candidates = False
        candidate_count = 0
        for line in lines:
            if 'Available interactive elements:' in line:
                in_candidates = True
                continue
            elif in_candidates:
                if line.strip() and line.startswith('ID'):
                    print(f"  {line}")
                    candidate_count += 1
                    if candidate_count >= 10:
                        break
                elif line.strip() and not line.startswith('ID'):
                    break
        
        # Test ID lookup manually
        print(f"\n🔧 Testing ID lookup consistency:")
        if len(ctx.interactive) >= 3:
            for test_idx in [0, 1, 2]:
                test_element = ctx.interactive[test_idx]
                expected_id = getattr(test_element, 'candidate_id', None)
                element_text = test_element.text[:30] if test_element.text else 'No text'
                print(f"  Element at index {test_idx}:")
                print(f"    Expected candidate_id: {expected_id}")
                print(f"    Element text: '{element_text}'")
                
                # Test lookup
                found_element = None
                for element in ctx.interactive:
                    if getattr(element, 'candidate_id', None) == expected_id:
                        found_element = element
                        break
                
                if found_element == test_element:
                    print(f"    ✅ ID lookup successful: Found correct element")
                else:
                    print(f"    ❌ ID lookup failed: Found different element")
                    if found_element:
                        found_text = found_element.text[:30] if found_element.text else 'No text'
                        print(f"    Found element text: '{found_text}'")
        
        # Check for duplicate IDs
        print(f"\n🔧 Checking for duplicate candidate IDs:")
        id_counts = {}
        for element in ctx.interactive:
            candidate_id = getattr(element, 'candidate_id', None)
            if candidate_id is not None:
                id_counts[candidate_id] = id_counts.get(candidate_id, 0) + 1
        
        duplicates = {id_val: count for id_val, count in id_counts.items() if count > 1}
        if duplicates:
            print(f"  ❌ Found duplicate IDs: {duplicates}")
        else:
            print(f"  ✅ All IDs are unique")
            
        print(f"\n📊 Summary:")
        print(f"  Total interactive elements: {len(ctx.interactive)}")
        print(f"  Elements with candidate_id: {len([e for e in ctx.interactive if hasattr(e, 'candidate_id')])}")
        print(f"  ID range: {min(id_counts.keys()) if id_counts else 'None'} to {max(id_counts.keys()) if id_counts else 'None'}")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await browser_controller.close()

if __name__ == "__main__":
    success = asyncio.run(test_id_mapping_fix())
    if success:
        print("\n✅ ID mapping test completed")
    else:
        print("\n❌ ID mapping test failed")
        sys.exit(1)
