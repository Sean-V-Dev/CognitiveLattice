#!/usr/bin/env python3
"""Debug the is_clickable_div function."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.dom_processor import is_clickable_div

# Test the specific elements
test_cases = [
    {
        'attrs': {'class': 'item-selector', 'data-qa-item-name': 'White Rice'},
        'text': 'White Rice 210 cal Included',
        'name': 'White Rice element'
    },
    {
        'attrs': {'class': 'restaurant-card', 'data-testid': 'restaurant-12345'},
        'text': 'Downtown Chipotle 123 Main Street 0.5 mi away',
        'name': 'Downtown Chipotle element'
    },
    {
        'attrs': {'class': 'meal-builder-item-selector-card-container', 'data-qa-item-name': 'Chicken'},
        'text': 'Chicken $2.00 Responsibly raised with no antibiotics 220 cal Add',
        'name': 'Chicken element (working)'
    }
]

print("🔍 Testing is_clickable_div function...")
print("-" * 50)

for test_case in test_cases:
    result = is_clickable_div(test_case['attrs'], test_case['text'])
    status = "✅" if result else "❌"
    print(f"{status} {test_case['name']}: {result}")
    print(f"   Attrs: {test_case['attrs']}")
    print(f"   Text: '{test_case['text'][:50]}...'")
    print()
