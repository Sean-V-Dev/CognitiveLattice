#!/usr/bin/env python3
"""
DOM Diffing Utility
===================

Surgical precision DOM change detection for web automation.
Allows AI agent to focus only on what actually changed after an action.
"""

from bs4 import BeautifulSoup, Tag
from typing import List, Dict, Any, Optional
from datetime import datetime
import re


def find_new_elements(html_before: str, html_after: str) -> str:
    """
    Compares two HTML documents and returns a string containing only the new elements
    that appeared in the 'after' version.
    
    Args:
        html_before: HTML content before the action
        html_after: HTML content after the action
    
    Returns:
        Clean HTML string containing only new elements
    """
    if not html_before or not html_after:
        return ""
    
    # Parse both HTML documents
    soup_before = BeautifulSoup(html_before, 'lxml')
    soup_after = BeautifulSoup(html_after, 'lxml')

    # Create a set of all elements from the 'before' state for fast lookups.
    # Use both tag string and text content for comparison to catch content changes
    before_elements = set()
    for tag in soup_before.find_all():
        element_signature = f"{tag.name}:{tag.get_text(strip=True)}:{str(tag.attrs)}"
        before_elements.add(element_signature)

    new_elements = []
    # Iterate through all elements in the 'after' state
    for tag in soup_after.find_all():
        element_signature = f"{tag.name}:{tag.get_text(strip=True)}:{str(tag.attrs)}"
        
        # If an element signature from the 'after' state is NOT in our set of 'before' elements,
        # it must be new or changed.
        if element_signature not in before_elements:
            # Additional check: only include if it has meaningful content or is interactive
            text_content = tag.get_text(strip=True)
            has_meaningful_content = len(text_content) > 0
            is_interactive = (tag.name in ['a', 'button', 'input', 'select'] or 
                            tag.get('role') in ['button', 'link', 'definition'] or
                            tag.get('onclick') or tag.get('href') or 
                            tag.get('tabindex'))
            
            if has_meaningful_content or is_interactive:
                new_elements.append(tag)

    # Return the new elements as a clean HTML string
    return "\n".join(str(new_element.prettify()) for new_element in new_elements)


def find_removed_elements(html_before: str, html_after: str) -> str:
    """
    Find elements that were removed (disappeared) from before to after.
    
    Args:
        html_before: HTML content before the action
        html_after: HTML content after the action
    
    Returns:
        Clean HTML string containing removed elements
    """
    if not html_before or not html_after:
        return ""
    
    # Parse both HTML documents
    soup_before = BeautifulSoup(html_before, 'lxml')
    soup_after = BeautifulSoup(html_after, 'lxml')

    # Create a set of all elements from the 'after' state
    after_elements = {str(tag) for tag in soup_after.find_all()}

    removed_elements = []
    # Find elements that existed before but not after
    for tag in soup_before.find_all():
        if str(tag) not in after_elements:
            # Check if parent still exists (element directly removed, not just parent)
            if tag.parent and str(tag.parent) in after_elements:
                removed_elements.append(tag)

    return "\n".join(str(removed_element.prettify()) for removed_element in removed_elements)


def analyze_dom_changes(html_before: str, html_after: str) -> Dict[str, Any]:
    """
    Comprehensive DOM change analysis.
    
    Args:
        html_before: HTML content before the action
        html_after: HTML content after the action
    
    Returns:
        Dictionary with detailed change analysis
    """
    new_elements_html = find_new_elements(html_before, html_after)
    removed_elements_html = find_removed_elements(html_before, html_after)
    
    # DEBUG: Save what the DOM diff detects as new elements
    if new_elements_html:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        debug_file = f"debug_dom_diff_new_elements_{timestamp}.txt"
        with open(debug_file, 'w', encoding='utf-8') as f:
            f.write(f"DOM DIFF NEW ELEMENTS DETECTED at {datetime.now()}\n")
            f.write(f"New Elements HTML Length: {len(new_elements_html)} characters\n")
            f.write("=" * 80 + "\n")
            f.write("NEW ELEMENTS HTML:\n")
            f.write(new_elements_html)
            f.write("\n" + "=" * 80 + "\n")
            if removed_elements_html:
                f.write("REMOVED ELEMENTS HTML:\n")
                f.write(removed_elements_html)
        print(f"🔍 DEBUG: Saved DOM diff new elements ({len(new_elements_html)} chars) to {debug_file}")
    
    # Parse new elements to extract interactive elements
    new_interactive = []
    if new_elements_html:
        soup = BeautifulSoup(new_elements_html, 'lxml')
        for tag in soup.find_all():
            if _is_interactive_element(tag):
                new_interactive.append({
                    'tag': tag.name,
                    'text': tag.get_text(strip=True)[:100],
                    'attrs': dict(tag.attrs),
                    'selector': _generate_selector(tag)
                })
    
    # Look for specific patterns in new content
    patterns = _detect_content_patterns(new_elements_html)
    
    return {
        'has_changes': bool(new_elements_html or removed_elements_html),
        'new_elements_html': new_elements_html,
        'removed_elements_html': removed_elements_html,
        'new_interactive_count': len(new_interactive),
        'new_interactive_elements': new_interactive,
        'content_patterns': patterns,
        'change_summary': _summarize_changes(new_elements_html, removed_elements_html, patterns)
    }


def _is_interactive_element(tag: Tag) -> bool:
    """Check if a tag represents an interactive element"""
    interactive_tags = {'a', 'button', 'input', 'select', 'textarea'}
    interactive_roles = {'button', 'link', 'menuitem', 'tab', 'option', 'searchbox', 'definition'}
    
    if tag.name in interactive_tags:
        return True
    
    if tag.get('role') in interactive_roles:
        return True
    
    if tag.get('onclick') or tag.get('href'):
        return True
        
    if tag.get('tabindex') and tag.get('tabindex') != '-1':
        return True
    
    return False


def _generate_selector(tag: Tag) -> str:
    """Generate a CSS selector for the tag"""
    selectors = []
    
    # Tag name
    selectors.append(tag.name)
    
    # ID selector (highest priority)
    if tag.get('id'):
        return f"#{tag.get('id')}"
    
    # Class selector
    if tag.get('class'):
        classes = ' '.join(tag.get('class')[:2])  # First 2 classes to avoid overly specific selectors
        selectors.append(f".{classes.replace(' ', '.')}")
    
    # Attribute selectors for key attributes
    for attr in ['role', 'data-testid', 'aria-label']:
        if tag.get(attr):
            selectors.append(f"[{attr}='{tag.get(attr)}']")
            break
    
    return ''.join(selectors)


def _detect_content_patterns(html: str) -> List[str]:
    """Detect specific content patterns in new HTML"""
    patterns = []
    
    if not html:
        return patterns
    
    # Location/address patterns
    location_indicators = [
        r'Near\s+\w+.*(?:and|&)\s+\w+',  # "Near Main St and Oak"
        r'\d+\s+miles?\s+away',          # "2.5 miles away"
        r'\d+\.\d+\s+mi',                # "1.2 mi"
        r'\d+\s+km',                     # "5 km"
        r'Store\s+#?\d+',                # "Store #1234"
        r'\d{1,5}\s+[A-Z][a-z]+.*(?:St|Ave|Rd|Blvd|Dr|Ln)',  # Street addresses
    ]
    
    for pattern in location_indicators:
        if re.search(pattern, html, re.IGNORECASE):
            patterns.append('location_results')
            break
    
    # Menu/food patterns
    food_indicators = [
        r'Bowl|Burrito|Tacos?|Salad',
        r'Rice|Beans|Chicken|Beef|Pork',
        r'Add\s+to\s+bag|Add\s+item',
        r'\$\d+\.\d{2}',  # Prices
    ]
    
    for pattern in food_indicators:
        if re.search(pattern, html, re.IGNORECASE):
            patterns.append('menu_items')
            break
    
    # Form/input patterns
    if re.search(r'<input|<select|<textarea', html, re.IGNORECASE):
        patterns.append('form_elements')
    
    # Modal/popup patterns
    if re.search(r'modal|popup|overlay|dialog', html, re.IGNORECASE):
        patterns.append('modal_popup')
    
    return patterns


def _summarize_changes(new_html: str, removed_html: str, patterns: List[str]) -> str:
    """Generate a human-readable summary of changes"""
    summary_parts = []
    
    if new_html:
        new_count = len(BeautifulSoup(new_html, 'lxml').find_all())
        summary_parts.append(f"{new_count} new elements appeared")
    
    if removed_html:
        removed_count = len(BeautifulSoup(removed_html, 'lxml').find_all())
        summary_parts.append(f"{removed_count} elements disappeared")
    
    if 'location_results' in patterns:
        summary_parts.append("location search results loaded")
    
    if 'menu_items' in patterns:
        summary_parts.append("menu items appeared")
    
    if 'form_elements' in patterns:
        summary_parts.append("new form fields added")
    
    if 'modal_popup' in patterns:
        summary_parts.append("modal or popup appeared")
    
    if not summary_parts:
        return "No significant changes detected"
    
    return "; ".join(summary_parts)


def should_use_dom_diff(action_type: str, goal: str) -> bool:
    """
    Determine if DOM diffing should be used for this action.
    
    Use DOM diff for:
    - Click actions that might trigger small UI changes
    - Form submissions that load results
    - Actions where we expect granular changes
    - Location selection steps (to isolate new restaurant elements)
    
    Use full DOM for:
    - Navigation to completely new pages
    - Initial page loads
    - Major state changes
    """
    goal_lower = goal.lower()
    
    # USE DOM DIFF for location selection steps - we want to isolate new restaurant elements
    if any(keyword in goal_lower for keyword in ['select', 'choose', 'pick']) and \
       any(keyword in goal_lower for keyword in ['location', 'restaurant', 'store', 'nearest']):
        return True
    
    # Always use diff for clicks (except navigation)
    if action_type == 'click' and 'navigate' not in goal_lower:
        return True
    
    # Use diff for form submissions
    if action_type in ['type', 'submit'] and any(keyword in goal_lower 
                                                 for keyword in ['search', 'enter', 'submit']):
        return True
    
    # Use full DOM for navigation
    if action_type == 'navigate' or 'navigate' in goal_lower:
        return False
    
    # Use full DOM for initial page analysis
    if 'analyze' in goal_lower or 'load' in goal_lower:
        return False
    
    # Default to diff for granular actions
    return True
