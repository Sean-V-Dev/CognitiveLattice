#!/usr/bin/env python3
"""
Debug the summarize_interactive_elements function.
"""

from tools.web_automation.dom_processor import summarize_interactive_elements
import re

def debug_element_detection():
    """Debug why elements aren't being detected."""
    
    # Simple test HTML
    html = '<div class="add-to-cart">Add to Bag</div>'
    goal = "Click on add to bag button"
    
    print(f"HTML: {html}")
    print(f"Goal: {goal}")
    
    # Test the regex pattern directly
    interactive_div_pattern = re.compile(r"<\s*(div|span)\b([^>]*)>(.*?)</\s*\1\s*>", re.I | re.S)
    matches = list(interactive_div_pattern.finditer(html))
    
    print(f"\nRegex matches found: {len(matches)}")
    for i, match in enumerate(matches):
        print(f"  Match {i+1}:")
        print(f"    Full match: {match.group(0)}")
        print(f"    Tag: {match.group(1)}")
        print(f"    Attributes: {match.group(2)}")
        print(f"    Content: {match.group(3)}")
    
    # Test with lxml if available
    try:
        from lxml import html as lxml_html
        print(f"\nlxml available: True")
        tree = lxml_html.fromstring(html)
        divs = tree.cssselect('div')
        print(f"lxml found {len(divs)} div elements")
        for div in divs:
            print(f"  Div: {div.attrib}, text: '{div.text_content()}'")
    except ImportError:
        print(f"\nlxml available: False")
    
    # Test the actual function
    print(f"\nTesting summarize_interactive_elements...")
    elements = summarize_interactive_elements(html, goal=goal)
    print(f"Function returned {len(elements)} elements")
    
    # Test with more complex HTML
    complex_html = '''
    <div class="container">
        <button>Regular Button</button>
        <div class="add-to-cart" onclick="addItem()">Add to Bag</div>
        <div data-testid="menu-item">Bowl</div>
    </div>
    '''
    
    print(f"\nTesting with complex HTML:")
    print(complex_html)
    complex_elements = summarize_interactive_elements(complex_html, goal=goal)
    print(f"Complex HTML returned {len(complex_elements)} elements:")
    for elem in complex_elements:
        print(f"  - <{elem.tag}> '{elem.text}' {elem.attrs}")

if __name__ == "__main__":
    debug_element_detection()
