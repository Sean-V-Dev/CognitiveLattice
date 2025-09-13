#!/usr/bin/env python3
"""Debug selector generation for bowl elements"""

import sys
sys.path.append('.')
from tools.web_automation.dom_processor import summarize_interactive_elements, score_interactive_elements

# Simulate a bowl element like what would be found on Chipotle
test_html = '''
<div class="menu-group top-level-menu" data-qa-group-name="Entrees">
  <div class="menu-item-card" data-qa-item-name="Burrito Bowl">
    <div class="item-title">Burrito Bowl</div>
    <div class="item-description">Order</div>
  </div>
  <div class="menu-item-card" data-qa-item-name="Burrito">
    <div class="item-title">Burrito</div>
    <div class="item-description">Order</div>
  </div>
</div>
'''

print("🔍 Testing selector generation for bowl elements...")
elements = summarize_interactive_elements(test_html)
scored = score_interactive_elements(elements, "Select 'Bowl'")

print(f"Found {len(scored)} scored elements:")
for i, elem in enumerate(scored[:5]):
    print(f"\n{i+1}. Element:")
    print(f"   Tag: {elem.tag}")
    print(f"   Text: '{elem.text}'")
    print(f"   Score: {getattr(elem, 'score', 'N/A')}")
    print(f"   Classes: {elem.attrs.get('class', 'N/A')}")
    print(f"   Data attrs: {[(k,v) for k,v in elem.attrs.items() if k.startswith('data-')]}")
    print(f"   Selectors: {elem.selectors}")
