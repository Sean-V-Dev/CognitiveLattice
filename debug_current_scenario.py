#!/usr/bin/env python3
"""
Debug script to test the exact ID mapping scenario from the current session.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.web_automation.models import Element, PageContext

def test_current_scenario():
    """Test the exact scenario from the debug logs."""
    
    print("🔧 Testing current ID mapping scenario...")
    
    # Create mock elements matching the current debug output
    mock_elements = [
        Element(tag="div", text="Lifestyle Bowl", selectors=["div.lifestyle-bowl"], score=19.0),
        Element(tag="div", text="Burrito Bowl", selectors=["div.burrito-bowl"], score=18.5),
        Element(tag="div", text="Lifestyle Bowl", selectors=["div.lifestyle-bowl-2"], score=18.5),
        Element(tag="div", text="Build Your Own", selectors=["div.build-your-own"], score=3.5),
    ]
    
    print(f"📋 Original elements (unsorted):")
    for i, elem in enumerate(mock_elements):
        print(f"  Index {i}: text='{elem.text}', score={elem.score}")
    
    # Simulate the scoring and ID assignment process
    scored_elements = sorted(mock_elements, key=lambda x: x.score, reverse=True)
    
    print(f"\n📊 After scoring (sorted by score DESC):")
    for i, elem in enumerate(scored_elements):
        print(f"  Index {i}: text='{elem.text}', score={elem.score}")
    
    # Assign candidate IDs sequentially (1-based)
    for i, element in enumerate(scored_elements, 1):
        element.candidate_id = i
        print(f"🔢 Assigned candidate_id {i} to element: '{element.text}'")
    
    # Create PageContext with scored_elements (this is our fix)
    ctx = PageContext(
        url="https://chipotle.com",
        title="Test Page",
        raw_dom="<html><body>test</body></html>",
        skeleton="test skeleton",
        signature="test signature",
        interactive=scored_elements  # The fix - use scored_elements with IDs
    )
    
    print(f"\n📋 PageContext.interactive elements:")
    for i, element in enumerate(ctx.interactive):
        candidate_id = getattr(element, 'candidate_id', 'MISSING')
        print(f"  Index {i}: candidate_id={candidate_id}, text='{element.text}'")
    
    # Test the step_executor ID lookup for candidate_id 2
    print(f"\n🔧 Testing step_executor lookup for candidate_id 2:")
    target_element = None
    for element in ctx.interactive:
        if getattr(element, 'candidate_id', None) == 2:
            target_element = element
            break
    
    if target_element:
        print(f"  ✅ Found candidate_id 2: '{target_element.text}'")
        print(f"  📍 Selector: {target_element.selectors[0] if target_element.selectors else 'No selector'}")
        
        # Verify this is the correct element
        expected_element = scored_elements[1]  # Second element in sorted list (0-based index)
        if target_element == expected_element:
            print(f"  ✅ CORRECT: This should be 'Burrito Bowl'")
            if target_element.text == "Burrito Bowl":
                print(f"  ✅ SUCCESS: Candidate ID 2 correctly maps to 'Burrito Bowl'")
                return True
            else:
                print(f"  ❌ WRONG: Expected 'Burrito Bowl', got '{target_element.text}'")
                return False
        else:
            print(f"  ❌ MAPPING ERROR: Found wrong element")
            return False
    else:
        print(f"  ❌ NOT FOUND: candidate_id 2 not found")
        return False

if __name__ == "__main__":
    success = test_current_scenario()
    if success:
        print("\n✅ ID mapping is working correctly")
        print("🤔 The issue might be elsewhere in the execution chain")
    else:
        print("\n❌ ID mapping is still broken")
        sys.exit(1)
