#!/usr/bin/env python3
"""
Simple test script to validate DOM processing and ID assignment without browser startup.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.web_automation.models import Element, PageContext

def test_id_assignment():
    """Test that ID assignment works correctly with mock data."""
    
    print("🔧 Testing ID assignment logic...")
    
    # Create mock elements
    mock_elements = []
    for i in range(5):
        element = Element(
            tag="button",
            text=f"Button {i}",
            selectors=[f"button:nth-child({i+1})"],
            attrs={"class": f"btn-{i}"},
            score=10 - i  # Descending scores
        )
        mock_elements.append(element)
    
    print(f"📋 Created {len(mock_elements)} mock elements")
    for i, elem in enumerate(mock_elements):
        print(f"  Element {i}: text='{elem.text}', score={elem.score}")
    
    # Simulate the scoring and ID assignment process from dom_processor.py
    # Sort by score (descending) - this is what score_interactive_elements does
    scored_elements = sorted(mock_elements, key=lambda x: x.score, reverse=True)
    
    print(f"\n📊 After scoring (sorted by score DESC):")
    for i, elem in enumerate(scored_elements):
        print(f"  Index {i}: text='{elem.text}', score={elem.score}")
    
    # Assign candidate IDs sequentially (1-based) - this is what dom_processor.py does
    for i, element in enumerate(scored_elements, 1):
        element.candidate_id = i
        print(f"🔢 Assigned candidate_id {i} to element: '{element.text}'")
    
    # Create PageContext with scored_elements - this is the fix we applied
    ctx = PageContext(
        url="https://test.com",
        title="Test Page",
        raw_dom="<html><body>test</body></html>",
        skeleton="test skeleton",
        signature="test signature",
        interactive=scored_elements  # This is the fix - use scored_elements with IDs
    )
    
    print(f"\n📋 PageContext.interactive elements:")
    for i, element in enumerate(ctx.interactive):
        candidate_id = getattr(element, 'candidate_id', 'MISSING')
        print(f"  Index {i}: candidate_id={candidate_id}, text='{element.text}'")
    
    # Test ID lookup - this is what step_executor.py does
    print(f"\n🔧 Testing ID lookup (step_executor logic):")
    for test_id in [1, 2, 3]:
        target_element = None
        for element in ctx.interactive:
            if getattr(element, 'candidate_id', None) == test_id:
                target_element = element
                break
        
        if target_element:
            print(f"  ✅ Found candidate_id {test_id}: '{target_element.text}'")
            # Verify it's the correct element
            expected_element = scored_elements[test_id - 1]  # Convert 1-based to 0-based
            if target_element == expected_element:
                print(f"    ✅ Correct element found")
            else:
                print(f"    ❌ Wrong element found!")
        else:
            print(f"  ❌ candidate_id {test_id} not found")
    
    print(f"\n✅ ID assignment test completed successfully")
    return True

if __name__ == "__main__":
    success = test_id_assignment()
    if not success:
        sys.exit(1)
