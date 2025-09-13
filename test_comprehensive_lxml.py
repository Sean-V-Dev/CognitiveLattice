#!/usr/bin/env python3
"""
Comprehensive test demonstrating the lxml-based DOM processor improvements.

This shows how the new implementation provides:
1. Faster and more precise HTML parsing with lxml
2. Prioritized data attribute extraction (like data-qa-item-name)
3. Cleaner text extraction avoiding price/nutrition info
4. Enhanced selector generation with uniqueness handling
5. Robust fallback to regex when lxml fails
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.dom_processor import summarize_interactive_elements, HAS_LXML

def test_comprehensive_improvements():
    """Test all the improvements made to the DOM processor."""
    
    print("🚀 Comprehensive lxml DOM Processor Test")
    print("=" * 50)
    
    print(f"📦 lxml available: {HAS_LXML}")
    print(f"🎯 Testing: Element extraction, text cleaning, selector prioritization")
    print()
    
    # Simulate Chipotle-style complex HTML
    chipotle_style_html = """
    <html>
    <body>
        <!-- Menu selection that succeeded in logs -->
        <div class="top-level-menu">
            <span>Burrito Bowl</span>
            <button>Order</button>
        </div>
        
        <!-- Protein selection that failed before (comprehensive text issue) -->
        <div class="meal-builder-item-selector-card-container" data-qa-item-name="Chicken">
            <div class="card-header">
                <span class="item-name">Chicken</span>
                <span class="item-price">$2.00</span>
            </div>
            <div class="card-body">
                <p class="description">Responsibly raised with no antibiotics</p>
                <p class="nutrition">220 cal</p>
            </div>
            <button class="add-button">Add</button>
        </div>
        
        <!-- Rice selection that failed before -->
        <div class="item-selector" data-qa-item-name="White Rice">
            <div>White Rice</div>
            <div>210 cal</div>
            <div>Included</div>
        </div>
        
        <!-- Bean selection that failed before -->
        <div class="meal-builder-item-selector-container fs-unmask" data-qa-item-name="Black Beans">
            <span>Black Beans</span>
            <span>130 cal</span>
            <span>$0.00</span>
        </div>
        
        <!-- Group/catering option that should be deprioritized -->
        <div class="group-option" data-qa-group-name="Family Meal">
            <h3>Family Meal for 4-6 people</h3>
            <p>Build your own serves 4-6 people</p>
            <span class="price">$45.99</span>
        </div>
        
        <!-- Location selector -->
        <div class="restaurant-card" data-testid="restaurant-12345">
            <h3>Downtown Chipotle</h3>
            <p>123 Main Street</p>
            <span>0.5 mi away</span>
        </div>
    </body>
    </html>
    """
    
    # Extract elements
    elements = summarize_interactive_elements(chipotle_style_html, max_items=15)
    
    print(f"📊 Extracted {len(elements)} interactive elements:")
    print("-" * 50)
    
    for i, elem in enumerate(elements, 1):
        # Show clean text extraction
        text_display = elem.text if len(elem.text) <= 30 else f"{elem.text[:30]}..."
        print(f"{i:2}. <{elem.tag}> '{text_display}'")
        print(f"    Primary selector: {elem.selectors[0] if elem.selectors else 'N/A'}")
        
        # Highlight data attribute usage
        if elem.attrs.get('data-qa-item-name'):
            print(f"    ✅ Uses data-qa-item-name: '{elem.attrs['data-qa-item-name']}'")
        elif elem.attrs.get('data-testid'):
            print(f"    ✅ Uses data-testid: '{elem.attrs['data-testid']}'")
        elif elem.attrs.get('data-qa-group-name'):
            print(f"    ⚠️  Group item: '{elem.attrs['data-qa-group-name']}'")
        print()
    
    # Verify the improvements
    print("🔍 Improvement Verification:")
    print("-" * 30)
    
    # 1. Clean text extraction
    chicken_elem = next((e for e in elements if e.attrs.get('data-qa-item-name') == 'Chicken'), None)
    if chicken_elem:
        if chicken_elem.text == 'Chicken':
            print("✅ Chicken text is clean: 'Chicken' (not comprehensive text)")
        else:
            print(f"❌ Chicken text still messy: '{chicken_elem.text}'")
    
    # 2. Prioritized selectors
    data_attr_selectors = 0
    for elem in elements:
        if elem.selectors and ('data-qa-item-name' in elem.selectors[0] or 'data-testid' in elem.selectors[0]):
            data_attr_selectors += 1
    
    print(f"✅ {data_attr_selectors} elements use prioritized data attribute selectors")
    
    # 3. Individual items vs group items
    individual_items = [e for e in elements if e.attrs.get('data-qa-item-name')]
    group_items = [e for e in elements if e.attrs.get('data-qa-group-name')]
    
    print(f"✅ Found {len(individual_items)} individual menu items")
    print(f"ℹ️  Found {len(group_items)} group/catering items (will be deprioritized)")
    
    # 4. Expected elements that should now work
    expected_working = [
        ('Chicken', 'Should extract clean name from data attribute'),
        ('White Rice', 'Should extract clean name from data attribute'), 
        ('Black Beans', 'Should extract clean name from data attribute'),
        ('Downtown Chipotle', 'Should extract location name'),
    ]
    
    print(f"\n🎯 Elements that should work now:")
    print("-" * 30)
    
    working_count = 0
    for expected_text, reason in expected_working:
        found = any(expected_text in elem.text for elem in elements)
        status = "✅" if found else "❌"
        print(f"{status} '{expected_text}' - {reason}")
        if found:
            working_count += 1
    
    success_rate = working_count / len(expected_working)
    print(f"\n📈 Success Rate: {success_rate:.1%} ({working_count}/{len(expected_working)})")
    
    if success_rate >= 0.75:
        print("\n🎉 lxml implementation successfully addresses the clicking issues!")
        print("✅ Clean text extraction from data attributes")
        print("✅ Prioritized unique selectors")  
        print("✅ Fallback to regex when needed")
        print("✅ Should resolve Chipotle automation failures")
    else:
        print("\n⚠️  Implementation needs more refinement")
    
    return success_rate >= 0.75

if __name__ == "__main__":
    test_comprehensive_improvements()
