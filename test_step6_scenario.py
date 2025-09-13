#!/usr/bin/env python3
"""
Test realistic Chipotle step 6 scenario with Fajita Veggies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.dom_processor import summarize_interactive_elements, score_interactive_elements

def test_step6_fajita_scenario():
    """Test the complete step 6 scenario where Fajita Veggies should bubble to the top."""
    print("🌯 Testing Step 6 Fajita Veggies Scenario")
    print("=" * 50)
    
    # Mock HTML similar to the actual step 6 DOM structure
    step6_html = """
    <div class="meal-builder">
        <a class="aem-card__button cmp-button" href="/order/group/create">START A GROUP ORDER</a>
        <a class="aem-hero__button cmp-button" href="#menu">ORDER NOW</a>
        <div class="address-text pickup-txt" role="link">6000 Wilmington Pike</div>
        
        <!-- Menu items -->
        <div class="meal-builder-item-selector-card-container" data-qa-item-name="Fresh Tomato Salsa" data-qa-title="Fresh Tomato Salsa">Fresh Tomato Salsa</div>
        <div class="meal-builder-item-selector-card-container" data-qa-item-name="Roasted Chili-Corn Salsa" data-qa-title="Roasted Chili-Corn Salsa">Roasted Chili-Corn Salsa</div>
        <div class="meal-builder-item-selector-card-container" data-qa-item-name="Sour Cream" data-qa-title="Sour Cream">Sour Cream</div>
        <div class="meal-builder-item-selector-card-container" data-qa-item-name="Fajita Veggies" data-qa-title="Fajita Veggies" data-qa-item-id="CMG-5101">Fajita Veggies</div>
        <div class="meal-builder-item-selector-card-container" data-qa-item-name="Cheese" data-qa-title="Cheese">Cheese</div>
        <div class="meal-builder-item-selector-card-container" data-qa-item-name="Romaine Lettuce" data-qa-title="Romaine Lettuce">Romaine Lettuce</div>
        <div class="meal-builder-item-selector-card-container" data-qa-item-name="Queso Blanco" data-qa-title="Queso Blanco">Queso Blanco</div>
        
        <!-- Lots of noise -->
        <div class="item-universal-fac-container hidden">Find a Chipotle for pricing and availability</div>
        <div class="item-universal-fac-container hidden">Find a Chipotle for pricing and availability</div>
        <div class="item-universal-fac-container hidden">Find a Chipotle for pricing and availability</div>
    </div>
    """
    
    goal = "Add 'Fajita Veggies' as a topping."
    
    print(f"🎯 Goal: '{goal}'")
    print(f"📄 Processing realistic step 6 HTML...")
    
    # Extract elements
    elements = summarize_interactive_elements(step6_html, max_items=15)
    print(f"📊 Extracted {len(elements)} elements")
    
    # Show initial state
    print(f"\n📝 Elements before scoring:")
    for i, elem in enumerate(elements[:10], 1):  # Show top 10
        print(f"  {i}. '{elem.text}' (score: {elem.score:.1f})")
    
    # Apply goal-aware scoring
    scored_elements = score_interactive_elements(elements, goal)
    
    print(f"\n🎯 Top candidates after keyword boosting:")
    for i, elem in enumerate(scored_elements[:10], 1):  # Show top 10 
        print(f"  {i}. '{elem.text}' (score: {elem.score:.1f})")
        if "data-qa-item-name" in elem.attrs:
            print(f"      data-qa-item-name: '{elem.attrs['data-qa-item-name']}'")
    
    # Check if Fajita Veggies is in top 5 (what gets sent to LLM)
    fajita_veggies = next((e for e in scored_elements if "Fajita Veggies" in e.text), None)
    
    if fajita_veggies:
        position = scored_elements.index(fajita_veggies) + 1
        print(f"\n🌶️ Fajita Veggies Results:")
        print(f"  Final Position: #{position}")
        print(f"  Final Score: {fajita_veggies.score:.1f}")
        print(f"  Primary Selector: {fajita_veggies.selectors[0] if fajita_veggies.selectors else 'None'}")
        
        if position <= 5:
            print(f"  ✅ SUCCESS: In top 5 candidates (will be sent to LLM)")
        elif position <= 10:
            print(f"  ⚠️  PARTIAL: In top 10 but not top 5")
        else:
            print(f"  ❌ FAILED: Not in top candidates")
            
        # Check if it would have been the issue before
        non_fajita_top5 = [e for e in scored_elements[:5] if "Fajita Veggies" not in e.text]
        if len(non_fajita_top5) == 5:
            print(f"  🔴 PROBLEM: Other elements scored higher than Fajita Veggies")
            for i, elem in enumerate(non_fajita_top5, 1):
                print(f"    {i}. '{elem.text}' - {elem.score:.1f}")
        else:
            print(f"  ✅ Fajita Veggies correctly outscored other elements")
    else:
        print(f"  ❌ ERROR: Fajita Veggies not found in processed elements")
    
    # Simulate what would be sent to the LLM
    top5_for_llm = scored_elements[:5]
    print(f"\n📤 Top 5 candidates that would be sent to LLM:")
    for i, elem in enumerate(top5_for_llm, 1):
        primary_selector = elem.selectors[0] if elem.selectors else "No selector"
        print(f"  {i}. <{elem.tag}> text=\"{elem.text}\" selector={primary_selector}")
    
    return scored_elements

if __name__ == "__main__":
    test_step6_fajita_scenario()
    print(f"\n🌯 Step 6 Fajita Veggies scenario test complete!")
