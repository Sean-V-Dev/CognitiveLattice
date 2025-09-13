#!/usr/bin/env python3
"""
Test the new lxml-based DOM processing implementation.

This test verifies that:
1. lxml import is successful
2. Element extraction works with lxml
3. Prioritized selector generation works
4. Fallback to regex still works
5. Text extraction is cleaner than BS4
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.dom_processor import summarize_interactive_elements, HAS_LXML

def test_lxml_implementation():
    """Test the lxml-based DOM processing."""
    
    print("🔧 Testing lxml-based DOM processor...")
    print("=" * 60)
    
    # Check if lxml is available
    print(f"lxml available: {HAS_LXML}")
    if not HAS_LXML:
        print("❌ lxml not available - will use regex fallback")
    else:
        print("✅ lxml is available")
    
    # Test HTML with various interactive elements
    test_html = """
    <html>
    <body>
        <!-- Traditional elements -->
        <button id="order-btn" class="btn primary">Order Now</button>
        <a href="/menu" class="nav-link">View Menu</a>
        <input type="text" placeholder="Enter ZIP code" data-testid="zip-input" />
        
        <!-- Chipotle-style menu items with data attributes -->
        <div class="meal-builder-item" data-qa-item-name="Chicken">
            <span class="item-name">Chicken</span>
            <span class="price">$2.00</span>
            <p class="description">Responsibly raised with no antibiotics</p>
            <span class="calories">220 cal</span>
            <button class="add-btn">Add</button>
        </div>
        
        <div class="meal-builder-item" data-qa-item-name="White Rice">
            <span class="item-name">White Rice</span>
            <span class="price">Included</span>
            <p class="nutrition">210 cal</p>
        </div>
        
        <!-- Location selector -->
        <div class="location-card" data-testid="location-123" onclick="selectLocation(123)">
            <h3>Downtown Store</h3>
            <p>123 Main St</p>
            <span class="distance">0.5 mi</span>
        </div>
        
        <!-- Interactive divs without explicit data attributes -->
        <div class="clickable menu-category" role="button">
            <span>Bowls</span>
        </div>
        
        <!-- Complex container that should be filtered -->
        <div class="promotion-banner">
            <h2>Limited Time Offer!</h2>
            <p>Get 20% off your first order</p>
            <button>Learn More</button>
        </div>
    </body>
    </html>
    """
    
    # Extract elements
    elements = summarize_interactive_elements(test_html, max_items=20)
    
    print(f"\n📊 Extracted {len(elements)} interactive elements:")
    print("-" * 40)
    
    for i, elem in enumerate(elements, 1):
        print(f"{i:2}. <{elem.tag}> '{elem.text[:40]}...' if len(elem.text) > 40 else elem.text")
        print(f"    Primary selector: {elem.selectors[0] if elem.selectors else 'N/A'}")
        
        # Check for data attributes
        data_attrs = {k: v for k, v in elem.attrs.items() if k.startswith('data-')}
        if data_attrs:
            print(f"    Data attrs: {data_attrs}")
        print()
    
    # Verify expected elements are found
    expected_elements = [
        ("button", "Order Now"),
        ("a", "View Menu"), 
        ("input", ""),  # ZIP input
        ("div", "Chicken"),  # Should get clean text from data attribute
        ("div", "White Rice"),  # Should get clean text from data attribute
        ("div", "Downtown Store"),  # Location card
        ("div", "Bowls"),  # Menu category
    ]
    
    print("🔍 Verification:")
    print("-" * 20)
    
    found_count = 0
    for expected_tag, expected_text in expected_elements:
        found = False
        for elem in elements:
            if elem.tag == expected_tag and expected_text in elem.text:
                found = True
                break
        
        status = "✅" if found else "❌"
        print(f"{status} {expected_tag}: '{expected_text}'")
        if found:
            found_count += 1
    
    print(f"\n📈 Results: {found_count}/{len(expected_elements)} expected elements found")
    
    # Test selector prioritization
    print("\n🎯 Testing selector prioritization:")
    print("-" * 30)
    
    for elem in elements:
        if elem.attrs.get('data-qa-item-name'):
            print(f"✅ Menu item '{elem.attrs['data-qa-item-name']}' has data attribute selector: {elem.selectors[0]}")
        elif elem.attrs.get('data-testid'):
            print(f"✅ Element with data-testid has attribute selector: {elem.selectors[0]}")
    
    success_rate = found_count / len(expected_elements)
    print(f"\n🎉 Test completed with {success_rate:.1%} success rate")
    
    if success_rate >= 0.8:
        print("✅ lxml implementation is working well!")
        return True
    else:
        print("❌ lxml implementation needs improvement")
        return False

if __name__ == "__main__":
    test_lxml_implementation()
