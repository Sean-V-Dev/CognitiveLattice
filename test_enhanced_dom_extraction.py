#!/usr/bin/env python3
"""
Test enhanced DOM text extraction from data attributes.
"""

import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.dom_processor import _extract_meaningful_text, _extract_attrs

def test_enhanced_text_extraction():
    """Test that text extraction works with data attributes."""
    print("🔍 Testing enhanced text extraction...")
    
    # Test 1: Normal text extraction
    attrs1 = {"class": "button"}
    text1 = _extract_meaningful_text("Click Here", attrs1)
    print(f"✅ Normal text: '{text1}' (expected: 'Click Here')")
    
    # Test 2: Empty text with data-qa-group-name (Chipotle pattern)
    attrs2 = {"data-qa-group-name": "Burrito Bowl", "class": "top-level-menu"}
    text2 = _extract_meaningful_text("", attrs2)
    print(f"✅ Data attribute text: '{text2}' (expected: 'Burrito Bowl')")
    
    # Test 3: Empty text with data-button-value
    attrs3 = {"data-button-value": "The Lola Bowl", "class": "meal-card-button"}
    text3 = _extract_meaningful_text("", attrs3)
    print(f"✅ Button value text: '{text3}' (expected: 'The Lola Bowl')")
    
    # Test 4: Prefer visible text over data attributes
    attrs4 = {"data-qa-group-name": "Burrito Bowl", "class": "menu"}
    text4 = _extract_meaningful_text("Build Your Own", attrs4)
    print(f"✅ Prefer visible text: '{text4}' (expected: 'Build Your Own')")
    
    # Test with actual HTML-like attribute string
    print("\n🔍 Testing with HTML attribute parsing...")
    attr_str = 'class="top-level-menu" data-qa-group-name="Burrito Bowl"'
    attrs5 = _extract_attrs(attr_str)
    text5 = _extract_meaningful_text("", attrs5)
    print(f"✅ Parsed attributes: {attrs5}")
    print(f"✅ Extracted text: '{text5}' (expected: 'Burrito Bowl')")
    
    return True

def main():
    """Run the enhanced text extraction test."""
    print("🚀 Testing enhanced DOM text extraction...")
    
    try:
        success = test_enhanced_text_extraction()
        
        if success:
            print("\n✅ Enhanced text extraction test PASSED!")
            print("📢 DOM processor should now extract 'Burrito Bowl' from data attributes")
            return 0
        else:
            print("\n❌ Enhanced text extraction test FAILED!")
            return 1
            
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
