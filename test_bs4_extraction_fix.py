#!/usr/bin/env python3
"""
Test demonstrating the fix for BeautifulSoup comprehensive text extraction.

This shows how the improved _extract_meaningful_text function now:
1. Prioritizes data attributes (like data-qa-item-name) 
2. Filters out text with price markers
3. Extracts clean first words from messy text
4. Keeps simple clean text intact

This should resolve the clicking issues where BeautifulSoup was extracting
too much comprehensive text (like "Chicken$2.00Responsibly raised220 calAdd")
instead of clean, targetable text (like "Chicken").
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.dom_processor import _extract_meaningful_text

def test_text_extraction_fix():
    """Test cases demonstrating the BeautifulSoup text extraction fix."""
    
    test_cases = [
        {
            'name': 'Chipotle menu item with data attribute',
            'raw_text': 'Chicken$2.00Responsibly raised with no antibiotics220 calAdd',
            'attrs': {'data-qa-item-name': 'Chicken'},
            'expected': 'Chicken',
            'reason': 'Should prioritize clean data attribute over messy comprehensive text'
        },
        {
            'name': 'Simple clean button text',
            'raw_text': 'Order Now',
            'attrs': {},
            'expected': 'Order Now',
            'reason': 'Should keep short clean text as-is'
        },
        {
            'name': 'Complex container without data attributes',
            'raw_text': 'Chicken Bowl $12.99 Build your own Customize',
            'attrs': {},
            'expected': 'Chicken Bowl',
            'reason': 'Should extract first clean words before price markers'
        },
        {
            'name': 'Bowl selection (successful case from logs)',
            'raw_text': 'Burrito BowlOrder',
            'attrs': {},
            'expected': 'Burrito BowlOrder',
            'reason': 'Should keep reasonably clean short text'
        },
        {
            'name': 'Text with calories and pricing',
            'raw_text': 'White Rice 210 cal $1.50 Extra charge applies',
            'attrs': {},
            'expected': 'White Rice',
            'reason': 'Should extract clean item name before nutritional info'
        }
    ]
    
    print("🔧 Testing BeautifulSoup text extraction fix...")
    print("=" * 60)
    
    all_passed = True
    
    for i, test_case in enumerate(test_cases, 1):
        result = _extract_meaningful_text(test_case['raw_text'], test_case['attrs'])
        passed = result == test_case['expected']
        all_passed = all_passed and passed
        
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"\nTest {i}: {test_case['name']}")
        print(f"Raw text: '{test_case['raw_text']}'")
        print(f"Expected: '{test_case['expected']}'")
        print(f"Got:      '{result}'")
        print(f"Status:   {status}")
        print(f"Reason:   {test_case['reason']}")
        
        if not passed:
            print(f"❌ Expected '{test_case['expected']}' but got '{result}'")
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! The BeautifulSoup text extraction fix is working.")
        print("\nThis should resolve the clicking issues where:")
        print("- Step 2 (Bowl selection) succeeded with simple text")
        print("- Steps 3-8 (Chicken, rice, etc.) failed due to comprehensive text extraction")
        print("\nNow all steps should get clean, targetable element text.")
    else:
        print("❌ Some tests failed. The fix needs more work.")
    
    return all_passed

if __name__ == "__main__":
    test_text_extraction_fix()
