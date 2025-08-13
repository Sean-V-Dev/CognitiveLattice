#!/usr/bin/env python3
"""
DOM Skeleton Utility
===================

Creates clean, token-efficient DOM skeletons from full HTML pages.
Removes noise (scripts, styles, etc.) while preserving structure and interactive elements.
"""

from bs4 import BeautifulSoup, Comment
import re
from typing import Set, List

def create_dom_skeleton(full_html: str, max_depth: int = 12) -> str:
    """
    Takes a full HTML string and strips it down to a highly efficient "skeleton"
    by preserving only interactive elements and their direct structural parents.
    
    Args:
        full_html: The full HTML content to process
        max_depth: Maximum depth to traverse (for compatibility, not used in this implementation)
    """
    if not full_html or not full_html.strip():
        return ""

    soup = BeautifulSoup(full_html, 'lxml')

    # STEP 1: Remove all the obvious noise tags completely
    tags_to_remove = ['script', 'style', 'meta', 'link', 'noscript', 'head', 'title', 'iframe', 'svg']
    for tag in soup.find_all(tags_to_remove):
        tag.decompose()

    # STEP 2: Remove HTML comments
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # STEP 3: Identify all "important" interactive elements
    important_elements = set()
    interactive_selectors = [
        'a[href]', 'button', 'input', 'select', 'textarea',
        '[role="button"]', '[role="link"]', '[role="option"]', '[role="menuitem"]',
        '[onclick]', '[data-testid]', '[data-qa-restaurant-id]'
    ]
    for selector in interactive_selectors:
        for element in soup.select(selector):
            important_elements.add(element)

    # STEP 4: "Bubble Up" importance to the parent containers of interactive elements
    # This preserves the essential structure around the things we care about.
    parents_to_keep = set()
    for element in important_elements:
        parent = element.parent
        # Go up a few levels to get meaningful container context
        for _ in range(3): # Go up 3 levels, or to the body
            if parent and parent.name != 'body':
                parents_to_keep.add(parent)
                parent = parent.parent
            else:
                break
    
    all_important_elements = important_elements.union(parents_to_keep)

    # STEP 5: Aggressively prune everything that is NOT important
    for tag in soup.find_all(True):
        if tag not in all_important_elements:
            # This is a non-essential tag. We will strip it but keep its text content.
            tag.unwrap() # .unwrap() removes the tag and leaves its contents behind.

    # STEP 6: Final attribute and whitespace cleanup
    attributes_to_keep = [
        'id', 'class', 'name', 'type', 'value', 'href', 'placeholder', 
        'title', 'aria-label', 'role', 'data-testid', 'data-qa-restaurant-id'
    ]
    for tag in soup.find_all(True):
        # Get current attributes
        current_attrs = list(tag.attrs.keys())
        for attr in current_attrs:
            if attr not in attributes_to_keep:
                del tag[attr]
    
    return soup.prettify()

def get_skeleton_stats(skeleton_html: str) -> dict:
    """
    Analyze the DOM skeleton to provide token count estimates and element statistics.
    
    Args:
        skeleton_html: The cleaned DOM skeleton
        
    Returns:
        Dictionary with statistics about the skeleton
    """
    # Rough token count estimation (1 token ≈ 4 characters for HTML)
    estimated_tokens = len(skeleton_html) // 4
    
    # Count different element types
    soup = BeautifulSoup(skeleton_html, 'html.parser')
    
    interactive_count = len(soup.find_all(['a', 'button', 'input', 'select', 'textarea', 'form']))
    structural_count = len(soup.find_all(['div', 'span', 'section', 'ul', 'li']))
    total_elements = len(soup.find_all(True))
    
    return {
        'estimated_tokens': estimated_tokens,
        'character_count': len(skeleton_html),
        'total_elements': total_elements,
        'interactive_elements': interactive_count,
        'structural_elements': structural_count,
        'compression_ratio': f"{len(skeleton_html) / max(len(skeleton_html), 1):.1%}" if skeleton_html else "0%"
    }


def extract_clickable_elements(skeleton_html: str) -> List[dict]:
    """
    Extract all clickable/interactive elements from the DOM skeleton with their selectors.
    
    Args:
        skeleton_html: The cleaned DOM skeleton
        
    Returns:
        List of dictionaries containing element information
    """
    soup = BeautifulSoup(skeleton_html, 'html.parser')
    clickable_elements = []
    
    # Interactive element types - expanded to catch more elements
    interactive_selectors = [
        'a[href]',           # Links
        'button',            # All buttons
        'input',             # ALL input elements (not just specific types)
        'select',            # Dropdowns
        'textarea',          # Text areas
        '[role="button"]',   # ARIA buttons
        '[role="link"]',     # ARIA links  
        '[role="searchbox"]', # Search inputs
        '[role="textbox"]',  # Text inputs
        '[role="combobox"]', # Combo boxes (autocomplete inputs)
        '[role="listbox"]',  # Autocomplete results container
        '[role="option"]',   # Autocomplete result items
        '[aria-controls]',     # Elements controlling other widgets (e.g., input -> listbox)
        '[aria-expanded]',     # Disclosure widgets
        '[aria-haspopup]',     # Menus / popovers
        '[onclick]',           # Elements with click handlers
        '[tabindex]',          # Focusable elements (including tabindex="0")
        '[aria-label]'         # Elements with accessibility labels (often interactive)
    ]
    
    # Track elements we've already added to avoid duplicates
    added_elements = set()
    
    for selector in interactive_selectors:
        try:
            elements = soup.select(selector)
            for elem in elements:
                # Create a unique identifier for this element
                element_id = f"{elem.name}_{elem.get('id', '')}_{elem.get('class', '')}_{elem.get_text(strip=True)[:20]}"
                
                if element_id in added_elements:
                    continue  # Skip duplicates
                
                # Filter out non-clickable elements
                if _is_non_clickable_element(elem):
                    continue
                
                added_elements.add(element_id)
                
                # Build selector for this element
                css_selector = _build_css_selector(elem)
                
                # Extract text content
                text_content = elem.get_text(strip=True)
                
                # Get important attributes
                attrs = {}
                for attr in ['id', 'class', 'type', 'name', 'placeholder', 'aria-label', 'title', 'role', 'aria-controls']:
                    if elem.get(attr):
                        attrs[attr] = elem.get(attr)
                
                clickable_elements.append({
                    'tag': elem.name,
                    'selector': css_selector,
                    'text': text_content,
                    'attrs': attrs,
                    'element_html': str(elem)[:200] + "..." if len(str(elem)) > 200 else str(elem)
                })
        except Exception as e:
            print(f"⚠️ Error with selector {selector}: {e}")
            continue
    
    return clickable_elements


def _is_non_clickable_element(element) -> bool:
    """
    Check if an element is non-clickable despite having tabindex or other interactive attributes.
    
    Args:
        element: BeautifulSoup element to check
        
    Returns:
        True if element should be excluded from clickable elements
    """
    # Exclude heading elements that only have tabindex (like "Nearby" text labels)
    if (element.get('role') == 'heading' and 
        element.get('tabindex') and 
        not element.get('onclick') and 
        not element.get('href') and
        element.name in ['span', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
        return True
    
    # Exclude elements that are just text labels with tabindex but no real interaction
    if (element.get('tabindex') and 
        not element.get('onclick') and 
        not element.get('href') and
        not element.get('aria-controls') and
        not element.get('aria-expanded') and
        element.name in ['span', 'div'] and
        element.get('role') not in ['button', 'link', 'option', 'menuitem', 'definition']):
        
        # Additional check: if text looks like a label (common patterns)
        text = element.get_text(strip=True).lower()
        label_patterns = ['nearby', 'results', 'showing', 'found', 'total', 'categories', 'filters']
        if any(pattern in text for pattern in label_patterns):
            return True
    
    return False


def _build_css_selector(element) -> str:
    """Build a simple, reliable CSS selector for the given BeautifulSoup element."""
    
    # Priority 1: Use ID if present (most reliable)
    if element.get('id'):
        return f"#{element.get('id')}"
    
    # Priority 2: Use data-qa-restaurant-id for restaurant selection (most specific for location selection)
    if element.get('data-qa-restaurant-id'):
        return f"[data-qa-restaurant-id='{element.get('data-qa-restaurant-id')}']"
    
    # Priority 3: Use role attribute for modern web apps (especially searchbox, textbox, combobox, listbox, option)
    if element.get('role') in ['searchbox', 'textbox', 'button', 'link', 'combobox', 'listbox', 'option']:
        return f"{element.name}[role='{element.get('role')}']"
    
    # Priority 3: Use aria-label for accessible elements (common in modern SPAs)
    if element.get('aria-label'):
        aria_label = element.get('aria-label').replace("'", "\\'")
        # Use partial match for aria-label to be more robust
        if len(aria_label) > 20:
            # Use first few words for long aria-labels
            aria_words = aria_label.split()[:3]
            aria_short = ' '.join(aria_words)
            return f"{element.name}[aria-label*='{aria_short}']"
        else:
            return f"{element.name}[aria-label='{aria_label}']"
    
    # Priority 4: Use name attribute for form elements
    if element.get('name'):
        return f"{element.name}[name='{element.get('name')}']"
    
    # Priority 5: Use data-testid or similar test attributes
    for test_attr in ['data-testid', 'data-cy', 'data-test']:
        if element.get(test_attr):
            return f"[{test_attr}='{element.get(test_attr)}']"
    
    # Priority 6: Use simple class combinations (max 2 classes to avoid complexity)
    if element.get('class'):
        classes = element.get('class')
        if isinstance(classes, list):
            # Filter out complex classes with special characters
            simple_classes = [c for c in classes[:2] if not any(char in c for char in ['!', '[', ']', ':', '--'])]
            if simple_classes:
                class_str = '.'.join(simple_classes)
                return f"{element.name}.{class_str}"
    
    # Priority 7: Use type attribute for inputs
    if element.name == 'input' and element.get('type'):
        return f"input[type='{element.get('type')}']"
    
    # Priority 8: Use href for links (partial match for uniqueness)
    if element.name == 'a' and element.get('href'):
        href = element.get('href')
        if len(href) > 10:  # Use partial href if long
            href_part = href.split('/')[-1] or href.split('/')[-2]
            return f"a[href*='{href_part}']"
        else:
            return f"a[href='{href}']"
    
    # Fallback: Just the tag name (least specific but always works)
    return element.name


# Test function to validate the skeleton creation
def test_dom_skeleton():
    """Test the DOM skeleton functionality with a sample HTML."""
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <style>.hidden { display: none; }</style>
        <script>console.log('test');</script>
    </head>
    <body>
        <div class="find-a-chipotle-container">
            <div class="find-a-chipotle-container-button d-flex text-no-decoration color-brown">
                <div class="find-a-chipotle d-inline-flex align-center transition">
                    <div alt="Find A Chipotle" tabindex="-1" role="img" class="icon mr-10px">
                        <svg width="24" height="24.17" viewBox="0 0 24 24.17">
                            <path fill="currentColor" d="M12 0a7.875..."></path>
                        </svg>
                    </div>
                    <span tabindex="0" role="link" class="text findChipotle-text">Find A Chipotle</span>
                </div>
            </div>
        </div>
        <button class="order-btn" id="order-now">Order Now</button>
        <input type="text" placeholder="Enter ZIP code" name="zipcode">
    </body>
    </html>
    """
    
    print("🧪 Testing DOM Skeleton Creation")
    print("=" * 40)
    
    # Create skeleton
    skeleton = create_dom_skeleton(sample_html)
    print("📋 DOM Skeleton:")
    print(skeleton)
    print()
    
    # Get statistics
    stats = get_skeleton_stats(skeleton)
    print("📊 Skeleton Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    # Extract clickable elements
    clickables = extract_clickable_elements(skeleton)
    print("🖱️ Clickable Elements Found:")
    for i, elem in enumerate(clickables, 1):
        print(f"  {i}. {elem['tag']} - {elem['selector']}")
        print(f"     Text: '{elem['text']}'")
        print(f"     Attrs: {elem['attrs']}")
        print()


if __name__ == "__main__":
    test_dom_skeleton()
