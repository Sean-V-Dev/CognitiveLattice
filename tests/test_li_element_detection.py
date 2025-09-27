#!/usr/bin/env python3
"""
Test file to reproduce the li element filtering issue and verify fixes.
This tests the specific "Remove" button li element that was being filtered out.
"""

import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.web_automation.dom_processor import summarize_interactive_elements, INTERACTIVE_TAGS

def test_li_element_detection():
    """Test detection of li elements with interactive attributes."""
    
    print("🔍 TESTING LI ELEMENT DETECTION")
    print("=" * 50)
    
    # Create HTML that simulates the structure you provided
    test_html = """
    <html>
    <body>
        <div>
            <div>
                <header>
                    <div>
                        <div>
                            <div>
                                <div>
                                    <div>
                                        <div>
                                            <div>
                                                <div>
                                                    <div>
                                                        <div>
                                                            <div>
                                                                <div>
                                                                    <div>
                                                                        <div>
                                                                            <div>
                                                                                <div>
                                                                                    <div>
                                                                                        <ul>
                                                                                            <li data-v-4f835758="" data-button="remove-item" data-button-value="Chicken Bowl" tabindex="0" role="link">
                                                                                                Remove
                                                                                                <span data-v-4f835758="" aria-label="Sean" class="screen-reader-offscreen"></span>
                                                                                            </li>
                                                                                            <li>Regular non-interactive item</li>
                                                                                            <li role="button" tabindex="0">Another interactive li</li>
                                                                                            <li data-button="test">Data button li</li>
                                                                                        </ul>
                                                                                    </div>
                                                                                </div>
                                                                            </div>
                                                                        </div>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                </div>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </header>
                <!-- Add some other interactive elements for comparison -->
                <button>Regular Button</button>
                <a href="#">Regular Link</a>
                <input type="text" placeholder="Regular Input">
            </div>
        </div>
    </body>
    </html>
    """
    
    goal = "Remove item from cart"
    
    print(f"🎯 Goal: {goal}")
    print(f"📋 Current INTERACTIVE_TAGS: {INTERACTIVE_TAGS}")
    
    # Test with current DOM processor
    print(f"\n🔍 Testing element detection...")
    elements = summarize_interactive_elements(test_html, goal=goal)
    
    print(f"📊 Found {len(elements)} interactive elements:")
    
    li_elements = []
    other_elements = []
    
    for i, elem in enumerate(elements):
        print(f"  {i+1:2d}. <{elem.tag}> text='{elem.text[:50]}' attrs={elem.attrs}")
        if elem.tag == "li":
            li_elements.append(elem)
        else:
            other_elements.append(elem)
    
    print(f"\n📊 Element breakdown:")
    print(f"  🎯 Li elements found: {len(li_elements)}")
    print(f"  🔘 Other elements: {len(other_elements)}")
    
    # Check for the specific "Remove" button
    remove_button_found = False
    for elem in elements:
        # Check if this is a li with data-button="remove-item"
        if (elem.tag == "li" and 
            elem.attrs.get("data-button") == "remove-item"):
            remove_button_found = True
            print(f"  ✅ Found the specific 'Remove' button!")
            print(f"      Text: '{elem.text}'")
            print(f"      Attrs: {elem.attrs}")
            break
    
    if not remove_button_found:
        print(f"  ❌ The specific 'Remove' button was NOT found!")
        print(f"     This confirms the li element filtering issue.")
    
    # Show what we expect to find
    print(f"\n🎯 Expected interactive li elements:")
    expected_li = [
        "Remove button (data-button='remove-item', role='link', tabindex='0')",
        "Another interactive li (role='button', tabindex='0')", 
        "Data button li (data-button='test')"
    ]
    
    for expected in expected_li:
        print(f"  📌 {expected}")
    
    return remove_button_found, len(li_elements), len(elements)

if __name__ == "__main__":
    print("Testing li element detection before fixes...")
    
    found, li_count, total_count = test_li_element_detection()
    
    print(f"\n{'✅ SUCCESS' if found else '❌ FAILED'}: Remove button detection")
    print(f"📊 Results: {li_count} li elements out of {total_count} total")
    
    if not found:
        print(f"\n🔧 FIXES NEEDED:")
        print(f"  1. Add 'li' to INTERACTIVE_TAGS")
        print(f"  2. Add XPath patterns for interactive li elements") 
        print(f"  3. Enhance clickable element detection for li tags")
        
    sys.exit(0 if found else 1)
