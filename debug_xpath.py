#!/usr/bin/env python3
"""Debug why some elements aren't being detected by lxml."""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from lxml import html

# Test the specific HTML that's not working
test_html = """
<!-- White Rice - not being detected -->
<div class="item-selector" data-qa-item-name="White Rice">
    <div>White Rice</div>
    <div>210 cal</div>
    <div>Included</div>
</div>

<!-- Downtown Chipotle - not being detected -->
<div class="restaurant-card" data-testid="restaurant-12345">
    <h3>Downtown Chipotle</h3>
    <p>123 Main Street</p>
    <span>0.5 mi away</span>
</div>
"""

tree = html.fromstring(test_html)

# Test our XPath query
xpath_query = (
    "//div[@onclick or @role='button' or @role='menuitem' or @tabindex or "
    "contains(@class, 'btn') or contains(@class, 'clickable') or "
    "contains(@class, 'selector') or contains(@class, 'card') or "
    "contains(@data-qa, 'item') or contains(@data-qa, 'menu') or "
    "contains(@data-testid, 'location') or contains(@data-testid, 'restaurant') or "
    "@data-qa-item-name or @data-qa-group-name or @data-testid]"
)

print("🔍 Testing XPath query...")
found_elements = tree.xpath(xpath_query)
print(f"Found {len(found_elements)} elements with XPath")

for i, elem in enumerate(found_elements, 1):
    attrs = dict(elem.attrib)
    text = elem.text_content().strip()
    print(f"{i}. <{elem.tag}> attrs={attrs} text='{text[:50]}...'")

# Test individual conditions
print(f"\n🔍 Testing individual XPath conditions...")
print(f"Elements with @data-qa-item-name: {len(tree.xpath('//div[@data-qa-item-name]'))}")
print(f"Elements with @data-testid: {len(tree.xpath('//div[@data-testid]'))}")
print(f"Elements with class containing 'selector': {len(tree.xpath('//div[contains(@class, \"selector\")]'))}")
print(f"Elements with class containing 'card': {len(tree.xpath('//div[contains(@class, \"card\")]'))}")

# Show all div elements
print(f"\n🔍 All div elements:")
all_divs = tree.xpath('//div')
for i, div in enumerate(all_divs, 1):
    attrs = dict(div.attrib)
    text = div.text_content().strip()[:30]
    print(f"{i}. <div> {attrs} text='{text}...'")
