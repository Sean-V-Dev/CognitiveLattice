#!/usr/bin/env python3
"""
Test the nth-child selector fix to ensure we generate reliable selectors.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.dom_processor import summarize_interactive_elements

def test_nth_child_fix():
    """Test that we generate reliable selectors without problematic nth-child."""
    print("🔧 Testing nth-child Selector Fix")
    print("=" * 50)
    
    # Mock HTML similar to Chipotle's problematic structure
    mock_html = """
    <div class="menu-container">
        <div class="display-name mealBurrito" role="link">Burrito Bowl</div>
        <div class="display-name mealBurrito" role="link">Burrito</div>
        <div class="display-name mealLifestyle" role="link">Lifestyle Bowl</div>
        <div class="button meal-card-button">Carne Asada Burrito Bowl</div>
        <div class="button meal-card-button" data-qa-item-name="Premium Bowl">Premium Bowl</div>
        <div class="button meal-card-button" data-testid="custom-bowl">Build Your Own</div>
    </div>
    """
    
    print("🎯 Testing HTML with multiple similar elements")
    print("📊 Expected behavior:")
    print("  - Should prefer data attributes over nth-child")
    print("  - Should use text-based selectors when possible")
    print("  - Should only use nth-child as last resort")
    print("  - nth-child selectors should be verified to work")
    
    try:
        elements = summarize_interactive_elements(mock_html, max_items=10)
        
        print(f"\n🔍 Extracted {len(elements)} elements:")
        print("-" * 40)
        
        problematic_selectors = []
        good_selectors = []
        
        for i, elem in enumerate(elements, 1):
            primary_selector = elem.selectors[0] if elem.selectors else "No selectors"
            print(f"{i}. <{elem.tag}> '{elem.text[:30]}...'")
            print(f"   Primary: {primary_selector}")
            
            # Check selector quality
            if ":nth-child(" in primary_selector:
                problematic_selectors.append((elem.text, primary_selector))
                print(f"   ⚠️  Uses nth-child selector")
            elif any(attr in primary_selector for attr in ['data-qa-item-name', 'data-testid']):
                good_selectors.append((elem.text, primary_selector))
                print(f"   ✅ Uses data attribute selector")
            elif ":has-text(" in primary_selector:
                good_selectors.append((elem.text, primary_selector))
                print(f"   ✅ Uses text-based selector")
            else:
                print(f"   ℹ️  Standard selector")
        
        print(f"\n📈 Selector Quality Analysis:")
        print(f"  ✅ Good selectors (data/text): {len(good_selectors)}")
        print(f"  ⚠️  Problematic selectors (nth-child): {len(problematic_selectors)}")
        
        if problematic_selectors:
            print(f"\n⚠️  Elements still using nth-child:")
            for text, selector in problematic_selectors:
                print(f"    - '{text[:20]}...': {selector}")
        
        # Check for the specific Chipotle case
        burrito_bowls = [e for e in elements if "Burrito Bowl" in e.text]
        if burrito_bowls:
            burrito_selector = burrito_bowls[0].selectors[0]
            print(f"\n🎯 Burrito Bowl selector analysis:")
            print(f"  Selector: {burrito_selector}")
            if ":nth-child(1)" in burrito_selector:
                print(f"  ❌ Still generating problematic nth-child(1)")
            else:
                print(f"  ✅ Fixed - no longer using nth-child(1)")
        
        print(f"\n🎉 Test Results:")
        improvement_ratio = len(good_selectors) / len(elements) if elements else 0
        print(f"  📊 Good selector ratio: {improvement_ratio:.1%}")
        
        if problematic_selectors:
            print(f"  🔄 Still need improvement for {len(problematic_selectors)} elements")
        else:
            print(f"  ✅ All selectors look reliable!")
        
        return elements
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return []

if __name__ == "__main__":
    test_nth_child_fix()
    print(f"\n🔧 nth-child selector fix testing complete!")
