#!/usr/bin/env python3
"""Test the new BeautifulSoup DOM processor fix"""

import sys
sys.path.append('.')
from tools.web_automation.dom_processor import summarize_interactive_elements

print('✅ DOM processor imports successfully with BeautifulSoup!')

# Test with nested HTML that would have failed with regex
test_html = '''
<div class="rice-options">
  <div data-qa-item-name="White Rice" class="meal-builder-item-selector-card-container">
    <div class="item-name">White Rice</div>
  </div>
  <div data-qa-item-name="Brown Rice" class="meal-builder-item-selector-card-container">
    <div class="item-name">Brown Rice</div>
  </div>
  <div data-qa-item-name="No Rice" class="meal-builder-item-selector-card-container">
    <div class="item-name">No Rice</div>
  </div>
</div>
'''

print("Testing nested HTML that previously failed...")
elements = summarize_interactive_elements(test_html)
print(f'Found {len(elements)} elements:')
for i, elem in enumerate(elements):
    qa_name = elem.attrs.get('data-qa-item-name', 'N/A')
    print(f'  {i+1}. {elem.tag} - text="{elem.text}" - data-qa-item-name="{qa_name}"')

print("\n🎯 Expected result: All 3 rice options should be found, including White Rice!")
