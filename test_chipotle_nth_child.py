#!/usr/bin/env python3
"""
Test with realistic Chipotle HTML structure to verify nth-child fix.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.dom_processor import summarize_interactive_elements

def test_chipotle_scenario():
    """Test with HTML structure similar to actual Chipotle website."""
    print("🌯 Testing Chipotle-like Scenario")
    print("=" * 50)
    
    # More realistic HTML that would cause the nth-child issue
    chipotle_html = """
    <div class="menu-options">
        <div class="display-name mealBurrito" role="link">Burrito Bowl</div>
        <div class="display-name mealBurrito" role="link">Burrito</div>
        <div class="display-name mealLifestyle" role="link">Lifestyle Bowl</div>
        <div class="display-name mealLifestyle" role="link">Lifestyle Bowl</div>
        <div class="button meal-card-button">Carne Asada Burrito Bowl</div>
        <div class="button meal-card-button">DJ Lagway's Carne Asada Bowl</div>
        <div class="button meal-card-button">The Lola Bowl</div>
        <div data-qa-group-name="Burrito Bowl" class="top-level-menu">Burrito Bowl</div>
        <div data-qa-group-name="Lifestyle Bowl" class="top-level-menu">Lifestyle Bowl</div>
        <button class="order-button">Order Now</button>
    </div>
    """
    
    print("🎯 Testing problematic Chipotle-like structure")
    print("📝 This HTML has:")
    print("  - Multiple div.display-name.mealBurrito elements")
    print("  - Multiple div.display-name.mealLifestyle elements") 
    print("  - Mixed data attributes and generic classes")
    
    try:
        elements = summarize_interactive_elements(chipotle_html, max_items=15)
        
        print(f"\n🔍 Extracted {len(elements)} elements:")
        print("-" * 50)
        
        nth_child_count = 0
        data_attr_count = 0
        text_based_count = 0
        
        for i, elem in enumerate(elements, 1):
            primary_selector = elem.selectors[0] if elem.selectors else "No selectors"
            print(f"{i}. <{elem.tag}> '{elem.text}'")
            print(f"   Primary: {primary_selector}")
            
            # Categorize selector types
            if ":nth-child(" in primary_selector:
                nth_child_count += 1
                print(f"   🔴 nth-child selector")
            elif any(attr in primary_selector for attr in ['data-qa-group-name', 'data-qa-item-name', 'data-testid']):
                data_attr_count += 1
                print(f"   🟢 Data attribute selector")
            elif ":has-text(" in primary_selector:
                text_based_count += 1
                print(f"   🟡 Text-based selector")
            else:
                print(f"   🔵 Standard selector")
            
            # Show all available selectors
            if len(elem.selectors) > 1:
                for j, alt_sel in enumerate(elem.selectors[1:], 2):
                    print(f"      Alt {j}: {alt_sel}")
        
        print(f"\n📊 Selector Distribution:")
        print(f"  🟢 Data attributes: {data_attr_count}")
        print(f"  🟡 Text-based: {text_based_count}")
        print(f"  🔴 nth-child: {nth_child_count}")
        print(f"  🔵 Standard: {len(elements) - nth_child_count - data_attr_count - text_based_count}")
        
        # Check specific cases that caused problems
        burrito_bowls = [e for e in elements if "Burrito Bowl" in e.text and "display-name" in str(e.selectors)]
        lifestyle_bowls = [e for e in elements if "Lifestyle Bowl" in e.text and "display-name" in str(e.selectors)]
        
        print(f"\n🎯 Problem Case Analysis:")
        if burrito_bowls:
            print(f"  📝 Found {len(burrito_bowls)} Burrito Bowl elements")
            for i, bowl in enumerate(burrito_bowls):
                selector = bowl.selectors[0]
                if ":nth-child(1)" in selector:
                    print(f"    ❌ Element {i+1} still uses :nth-child(1)")
                else:
                    print(f"    ✅ Element {i+1} uses better selector: {selector}")
        
        if lifestyle_bowls:
            print(f"  📝 Found {len(lifestyle_bowls)} Lifestyle Bowl elements")
            for i, bowl in enumerate(lifestyle_bowls):
                selector = bowl.selectors[0]
                if ":nth-child(" in selector:
                    print(f"    ⚠️ Element {i+1} uses nth-child: {selector}")
                else:
                    print(f"    ✅ Element {i+1} uses better selector: {selector}")
        
        print(f"\n🎉 Fix Effectiveness:")
        total_elements = len(elements)
        if total_elements > 0:
            nth_child_ratio = nth_child_count / total_elements
            reliable_ratio = (data_attr_count + text_based_count) / total_elements
            
            print(f"  📉 nth-child usage: {nth_child_ratio:.1%} (lower is better)")
            print(f"  📈 Reliable selectors: {reliable_ratio:.1%} (higher is better)")
            
            if nth_child_ratio < 0.2:  # Less than 20%
                print(f"  ✅ Good! Low nth-child usage")
            else:
                print(f"  ⚠️ Still too many nth-child selectors")
        
        return elements
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    test_chipotle_scenario()
    print(f"\n🌯 Chipotle scenario testing complete!")
