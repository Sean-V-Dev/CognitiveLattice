# tools/web_automation/dom_processor.py
"""
Pure DOM processing: compression, skeleton creation, element extraction, and scoring.
No LLM calls, no lattice integration, no file I/O - just DOM data processing.
"""
import re
import hashlib
import os
from typing import Dict, Any, List
from datetime import datetime
from utils.dom_skeleton import create_dom_skeleton
from .models import Element, PageContext

# lxml for faster, more precise HTML parsing
try:
    from lxml import html
    HAS_LXML = True
except ImportError:
    HAS_LXML = False

# Debug flag - set WEB_AGENT_DEBUG=1 to enable debug outputs
DEBUG = bool(int(os.getenv("WEB_AGENT_DEBUG", "0")))

# Single DOM truncation constant with goal-aware override
DOM_TRUNCATE_CHARS = int(os.getenv("WEB_AGENT_DOM_TRUNCATE_CHARS", "50000"))  # Increased from 18000
DOM_TRUNCATE_CHARS_LOCATION = int(os.getenv("WEB_AGENT_DOM_TRUNCATE_CHARS_LOCATION", "70000"))
DOM_TRUNCATE_CHARS_ACTION = int(os.getenv("WEB_AGENT_DOM_TRUNCATE_CHARS_ACTION", "100000"))  # New larger limit for actions

# Interactive element processing limits
INTERACTIVE_MAX_ITEMS = int(os.getenv("WEB_AGENT_INTERACTIVE_MAX_ITEMS", "2000"))  # Already increased
INTERACTIVE_INCLUDE_TEXT_MAX = int(os.getenv("WEB_AGENT_INTERACTIVE_INCLUDE_TEXT_MAX", "80"))

# Keyword boosts for scoring
KEYWORD_BOOST = [
    "order", "buy", "shop", "start", "begin", "find", "location", "search", "submit",
    "accept", "agree", "continue", "next", "add", "cart", "checkout", "zip", "address",
    "pickup", "delivery", "login", "sign in", "apply", "continue as guest",
]

INTERACTIVE_TAGS = {"a", "button", "input", "select", "li"}
INTERACTIVE_ROLES = {
    "button", "link", "dialog", "combobox", "textbox", "menuitem", "option", 
    "tab", "switch", "checkbox", "radio", "menu", "menuitemcheckbox", 
    "menuitemradio", "treeitem"
}


def _safe_get_class_string(attrs: Dict[str, Any]) -> str:
    """Safely get class attribute as string, handling AttributeValueList objects"""
    class_value = attrs.get('class', '')
    
    # Debug logging to catch anomalies
    if DEBUG:
        print(f"🔍 Raw class value: {repr(class_value)} (type: {type(class_value)})")
    
    if hasattr(class_value, '__iter__') and not isinstance(class_value, str):
        # Handle AttributeValueList or other iterable types
        # Strip whitespace and filter out empty classes
        cleaned_classes = [str(cls).strip() for cls in class_value if str(cls).strip()]
        result = ' '.join(cleaned_classes)
        if DEBUG and cleaned_classes:
            print(f"🔍 Processed iterable classes: {cleaned_classes} -> '{result}'")
        return result
    
    # Handle string class values - strip and normalize whitespace
    result = str(class_value).strip()
    if DEBUG and result:
        print(f"🔍 Processed string class: '{result}'")
    return result


def compress_dom(raw_dom: str, goal: str = "") -> str:
    """Compress DOM by removing scripts/styles and applying goal-aware size limits with smart truncation."""
    # Determine max size based on goal type
    goal_lower = goal.lower()
    if any(keyword in goal_lower for keyword in ['select', 'choose', 'pick', 'nearest']) and \
       any(keyword in goal_lower for keyword in ['location', 'restaurant', 'store']):
        max_chars = DOM_TRUNCATE_CHARS_LOCATION
        if DEBUG:
            print(f"🎯 Using extended DOM limit ({max_chars}) for location selection")
    elif any(keyword in goal_lower for keyword in ['add', 'submit', 'continue', 'next', 'buy', 'order', 'checkout']):
        max_chars = DOM_TRUNCATE_CHARS_ACTION  # Use larger limit for action-heavy goals
        if DEBUG:
            print(f"🎯 Using action DOM limit ({max_chars}) for action goal")
    else:
        max_chars = DOM_TRUNCATE_CHARS
    
    # Clean the DOM
    cleaned = re.sub(r"<!----+>", "", raw_dom)
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", cleaned, flags=re.DOTALL|re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    
    if len(cleaned) <= max_chars:
        return cleaned
    
    # SMART TRUNCATION: Try to preserve complete elements
    # Find all top-level container divs
    container_pattern = r'<div[^>]*(?:class="[^"]*(?:container|wrapper|content|main|body|footer|header|nav|section)[^"]*")[^>]*>.*?</div>'
    containers = re.findall(container_pattern, cleaned, re.DOTALL | re.IGNORECASE)
    
    # Build DOM by prioritizing complete containers
    result = ""
    for container in containers:
        if len(result) + len(container) < max_chars:
            result += container + " "
        else:
            # If we can't fit the whole container, at least try to get its interactive elements
            result += container[:max_chars - len(result)]
            break
    
    return result if result else cleaned[:max_chars]


def page_signature(raw_dom: str) -> str:
    """Create a hash signature for the DOM to detect changes."""
    return hashlib.sha256(raw_dom.encode("utf-8")).hexdigest()[:16]


def _extract_meaningful_text(raw_text: str, attrs: Dict[str, Any], tag_name: str = "") -> str:
    """Extract meaningful text from element, with tag-specific prioritization."""
    
    # For li elements, prioritize visible text over data attributes
    # This ensures interactive li elements show their actual button text
    if tag_name == "li":
        text = _norm_text(raw_text)
        if text and len(text.strip()) >= 2 and len(text.strip()) <= 50:
            clean_ratio = len([c for c in text if c.isalnum() or c.isspace()]) / len(text)
            if clean_ratio > 0.7:
                return text
    
    # PRIORITY 1: Try data attributes first (these are usually clean and specific)
    data_attrs_to_check = [
        'data-qa-item-name',      # QA Item names (highest priority for menu items)
        'data-qa-group-name',     # Chipotle menu groups
        'data-qa-name',           # QA test names
        'data-qa-title',          # QA titles
        'data-qa-label',          # QA labels
        'data-item-name',         # Generic item names
        'data-label',             # Generic labels
        'data-title',             # Generic titles
        'data-name',              # Generic names
        'data-text',              # Generic text
        'data-value',             # Generic values
        'data-button-value',      # Button values
        'data-menu-name',         # Menu names
        'data-category',          # Categories
    ]
    
    for attr_name in data_attrs_to_check:
        if attr_name in attrs and attrs[attr_name]:
            extracted = str(attrs[attr_name]).strip()
            if extracted and len(extracted) > 1:
                # Clean up the extracted text
                return _norm_text(extracted)
    
    # PRIORITY 2: If raw text is short and clean, use it
    text = _norm_text(raw_text)
    if text and len(text.strip()) >= 2 and len(text.strip()) <= 50:
        # Check if text looks clean (no excessive punctuation or complex content)
        clean_ratio = len([c for c in text if c.isalnum() or c.isspace()]) / len(text)
        has_price_markers = any(marker in text for marker in ['$', '£', '€', '¥', 'cal', 'kcal'])
        if clean_ratio > 0.7 and not has_price_markers:
            return text
    
    # PRIORITY 3: Try to extract just the first meaningful part of longer text
    if text and len(text.strip()) > 50:
        # Try to get the first sentence or phrase before common delimiters
        first_part = text.split('.')[0].split('$')[0].split('\n')[0].strip()
        if 2 <= len(first_part) <= 30:
            return _norm_text(first_part)
    
    # PRIORITY 4: For messy text without data attributes, try to extract the first few words
    if text and len(text.strip()) > 20:  # Lower threshold to catch more cases
        # Look for the first 1-3 words that look like menu items
        words = text.split()
        if len(words) >= 2:
            # Try combinations of first few words
            for word_count in [2, 3, 1]:
                if word_count <= len(words):
                    candidate = ' '.join(words[:word_count])
                    # Check if this looks like a reasonable menu item name
                    if (2 <= len(candidate) <= 30 and 
                        not any(char in candidate for char in ['$', '℃', '%', 'cal']) and
                        not candidate.lower().startswith(('add', 'build', 'custom', 'order'))):
                        return _norm_text(candidate)
    
    # PRIORITY 5: Fallback to original text if nothing else works
    if text and len(text.strip()) > 20:
        # Remove common noise like prices, calories, etc.
        cleaned = re.sub(r'[\$\€\£¥]?\d+\.?\d*|\d+cal|kcal|extra.*|add.*', '', text, flags=re.I).strip()
        cleaned = re.sub(r'\s+', ' ', cleaned)  # Collapse spaces
        if 2 <= len(cleaned) <= 30:
            return cleaned
    return text if text else ""


def _norm_text(t: str) -> str:
    """Normalize text for processing."""
    t = re.sub(r"\s+", " ", (t or "")).strip()
    return t[:INTERACTIVE_INCLUDE_TEXT_MAX]


def _extract_attrs(attr_str: str) -> Dict[str, str]:
    """Enhanced attribute parser that handles complex nested structures."""
    attrs = {}
    
    # Original regex patterns
    for m in re.finditer(r'(\w[\w:-]*)\s*=\s*"([^"]*)"', attr_str or ""):
        attrs[m.group(1).lower()] = m.group(2)
    for m in re.finditer(r"(\w[\w:-]*)\s*=\s*'([^']*)'", attr_str or ""):
        attrs[m.group(1).lower()] = m.group(2)
    
    # ENHANCED: Look for data-qa-item-name specifically in the entire HTML chunk
    if 'data-qa-item-name' not in attrs:
        qa_match = re.search(r'data-qa-item-name="([^"]*)"', attr_str or "", re.I)
        if qa_match:
            attrs['data-qa-item-name'] = qa_match.group(1)
    
    return attrs


def _candidate_selectors(tag: str, attrs: Dict[str, str], text: str) -> List[str]:
    """Generate candidate selectors for an element, prioritizing unique selectors first."""
    
    def esc(v: str, lim: int = 24) -> str:
        """Escape and limit text for safe selector usage."""
        v = (v or "")[:lim].replace('"', r'\"')
        return v
    
    sels = []
    
    # PRIORITY 1: Data attributes (most unique and reliable)
    if attrs.get("data-qa-group-name"):
        sels.append(f'{tag}[data-qa-group-name="{esc(attrs["data-qa-group-name"])}"]')
    if attrs.get("data-qa-item-name"):
        sels.append(f'{tag}[data-qa-item-name="{esc(attrs["data-qa-item-name"])}"]')
    if attrs.get("data-testid"):
        sels.append(f"{tag}[data-testid=\"{esc(attrs['data-testid'])}\"]")
    if attrs.get("data-qa-name"):
        sels.append(f"{tag}[data-qa-name=\"{esc(attrs['data-qa-name'])}\"]")
    
    # PRIORITY 2: ID
    if attrs.get("id"):
        sels.append(f"#{attrs['id']}")
    
    # PRIORITY 3: Classes - handle them properly, with malformed class detection
    classes = _safe_get_class_string(attrs).strip()
    if classes:
        # Split classes properly and only use valid CSS class names
        class_list = classes.split()
        valid_classes = []
        
        for c in class_list:
            # Skip empty classes and classes with invalid characters
            if c and not any(char in c for char in ' \t\n\r'):
                # Additional validation: skip classes that look malformed (mixed camelCase + spaces)
                # e.g., "mealBurrito" when original was "mealBurrito Bowl"
                if len(c) > 8 and c[0].islower() and any(char.isupper() for char in c[1:]):
                    # This looks like a truncated camelCase class - likely malformed
                    if DEBUG:
                        print(f"⚠️ Skipping potentially malformed class: '{c}' from '{classes}'")
                    continue
                valid_classes.append(c)
        
        if valid_classes:
            # Use only the first 1-2 valid classes for the selector
            if len(valid_classes) >= 2:
                sels.append(f"{tag}.{valid_classes[0]}.{valid_classes[1]}")
            elif len(valid_classes) == 1:
                sels.append(f"{tag}.{valid_classes[0]}")
    
    # PRIORITY 4: Role-based selectors
    role = attrs.get("role")
    if role:
        sels.append(f"[role=\"{esc(role, 32)}\"]")
        if text:
            sels.append(f"[role=\"{esc(role, 32)}\"]:has-text(\"{esc(text, 48)}\")")
    
    # PRIORITY 5: Other attributes
    aria = attrs.get("aria-label")
    if aria:
        sels.append(f"[aria-label*=\"{esc(aria)}\"]")
    name = attrs.get("name")
    if name:
        sels.append(f"{tag}[name*=\"{esc(name)}\"]")
    placeholder = attrs.get("placeholder")
    if placeholder:
        sels.append(f"{tag}[placeholder*=\"{esc(placeholder)}\"]")
    href = attrs.get("href")
    if href and tag == "a":
        sels.append(f"a[href*=\"{esc(href, 32)}\"]")
    
    # PRIORITY 6: Text-based selectors (fallback)
    if text:
        sels.append(f"{tag}:has-text(\"{esc(text, 48)}\")")
    
    # de-dupe while preserving order
    seen = set()
    uniq = []
    for s in sels:
        if s not in seen:
            seen.add(s)
            uniq.append(s)
    return uniq[:5]  # Return top 5 selectors, first is primary


def _extract_goal_keywords(goal: str) -> List[str]:
    """Extract meaningful keywords from the goal to use for element detection."""
    if not goal:
        return []
    
    # Clean the goal text
    goal_lower = goal.lower()
    
    # Remove common stop words but keep action words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'this', 'that', 'these', 'those'}
    
    # Split into words and filter
    words = re.findall(r'\b\w+\b', goal_lower)
    keywords = [word for word in words if len(word) > 2 and word not in stop_words]
    
    return keywords


def is_clickable_element(tag: str, attrs: Dict[str, str], text: str, goal: str = "") -> bool:
    """Determine if an element (div/span/li) is likely clickable based on attributes and content."""
    
    # Special handling for li elements
    if tag == "li":
        # Li with role="link" or role="button" is definitely clickable
        if attrs.get("role") in ["button", "link", "menuitem"]:
            return True
        # Li with data-button attribute (like your remove button)
        if attrs.get("data-button"):
            return True
        # Li with tabindex (indicating keyboard navigation)
        if "tabindex" in attrs and attrs["tabindex"] != "-1":
            return True
        # Li with onclick handler
        if attrs.get("onclick"):
            return True
    
    # Continue with existing logic for all element types
    return _is_clickable_element_base(attrs, text, goal)

def is_clickable_div(attrs: Dict[str, str], text: str, goal: str = "") -> bool:
    """Determine if a div/span is likely clickable based on attributes and content."""
    # Keep existing function for backward compatibility
    return _is_clickable_element_base(attrs, text, goal)

def _is_clickable_element_base(attrs: Dict[str, str], text: str, goal: str = "") -> bool:
    """Base clickable detection logic shared by is_clickable_element and is_clickable_div."""
    # Priority 1: Check for ANY data- attribute (often indicates interactivity)
    has_data_attr = any(k.startswith('data-') for k in attrs.keys())
    if has_data_attr and len(text.strip()) > 0:
        return True  # Any data attribute with text is likely interactive
    
    # Priority 2: QA test attributes (highest priority - these are explicit markers)
    qa_attrs = [
        "data-qa-item-name", "data-qa-group-name", "data-qa-name",
        "data-testid", "data-test-id"
    ]
    if any(attrs.get(attr) for attr in qa_attrs):
        return True
    
    # Priority 3: Check for explicit click indicators
    if attrs.get("onclick"): return True
    if attrs.get("role") in ["button", "link", "tab", "menuitem", "option"]: return True
    if "tabindex" in attrs and attrs["tabindex"] != "-1": return True
    
    # Priority 4: Check for button-like classes (more generic patterns)
    classes = _safe_get_class_string(attrs).lower()
    button_patterns = ['btn', 'button', 'click', 'action', 'submit', 'cta', 'link', 'add-to-', 'menu-item']
    if any(pattern in classes for pattern in button_patterns):
        return True
    
    # Priority 5: Check if it has meaningful text that suggests action or matches goal
    if text and len(text.strip()) > 0:
        text_lower = text.lower()
        
        # Generic action words that apply to any website
        generic_action_words = ['add', 'submit', 'continue', 'next', 'select', 'choose', 
                               'buy', 'order', 'checkout', 'proceed', 'confirm', 'save',
                               'find', 'locate', 'search', 'start', 'begin', 'enter']
        
        # Check for generic action words
        if any(word in text_lower for word in generic_action_words):
            return True
        
        # Extract keywords from the goal and check if element text matches
        if goal:
            goal_keywords = _extract_goal_keywords(goal)
            # Check if any goal keyword appears in the element text (word boundary matching)
            import re
            if any(re.search(r'\b' + re.escape(keyword) + r'\b', text_lower) for keyword in goal_keywords):
                return True
    
    # Priority 6: Menu items with data attributes (e.g., Chipotle menu categories)
    menu_attrs = [
        "data-menu-item", "data-menu-category", "data-item-name", 
        "data-category", "data-meal-type"
    ]
    if any(attrs.get(attr) for attr in menu_attrs):
        return True
        
    # Priority 7: Location/store containers with identifying attributes
    location_attrs = [
        "data-qa-restaurant-id", "data-store-id", "data-location-id", 
        "data-shop-id", "data-venue-id", "data-place-id"
    ]
    if any(attrs.get(attr) for attr in location_attrs):
        return True
    
    # Check for navigation/location keywords in text or classes
    combined_text = " ".join([
        text.lower(),
        classes,
        attrs.get("data-testid", "").lower(),
        attrs.get("aria-label", "").lower()
    ])
    
    # Special boost for obvious location finder elements
    location_phrases = [
        "find location", "find store", "store locator", 
        "location finder", "enter location", "location search",
        "find a store", "store finder", "find locations"
    ]
    
    for phrase in location_phrases:
        if phrase in combined_text:
            return True
            
    return False


def find_deepest_interactive_element(html_chunk: str, goal: str = "") -> List[Element]:
    """Find the deepest (most specific) interactive element in an HTML chunk."""
    elements = []
    
    # Check if this chunk itself is interactive
    if '<div' in html_chunk[:20]:  # This is a div element - be more lenient with position
        # Extract the opening tag to get attributes
        opening_tag_match = re.search(r'<div[^>]*>', html_chunk)
        if not opening_tag_match:
            return elements
            
        attrs = _extract_attrs(opening_tag_match.group(0))
        
        # Look for nested interactive elements first (depth-first approach)
        nested_found = False
        
        # Priority 1: Find divs with role="button" inside (skip the opening tag)
        content_after_opening = html_chunk[opening_tag_match.end():]
        if 'role="button"' in content_after_opening:
            # Find the first complete nested div with role="button"
            inner_button_pattern = r'<div[^>]*role="button"[^>]*>(?:[^<]|<(?!/div>))*</div>'
            inner_button = re.search(inner_button_pattern, content_after_opening, re.S)
            if inner_button:
                nested_found = True
                # Recursively process the inner button
                deeper_elements = find_deepest_interactive_element(inner_button.group(0), goal)
                if deeper_elements:
                    elements.extend(deeper_elements)
        
        # Priority 2: Find divs with button classes inside (only if no role="button" found)
        if not nested_found and 'class="' in content_after_opening:
            # Look for button-like classes in nested divs
            inner_button_pattern = r'<div[^>]*class="[^"]*(?:button|btn|add-to-)[^"]*"[^>]*>(?:[^<]|<(?!/div>))*</div>'
            inner_buttons = re.findall(inner_button_pattern, content_after_opening, re.S)
            if inner_buttons:
                nested_found = True
                for inner in inner_buttons[:1]:  # Only process the first one to avoid duplicates
                    deeper_elements = find_deepest_interactive_element(inner, goal)
                    if deeper_elements:
                        elements.extend(deeper_elements)
        
        # Priority 3: Find divs with data-qa attributes (highest specificity)
        if not nested_found and ('data-qa-' in content_after_opening or 'data-testid' in content_after_opening):
            qa_pattern = r'<div[^>]*(?:data-qa-[^=]*="[^"]*"|data-testid="[^"]*")[^>]*>(?:[^<]|<(?!/div>))*</div>'
            qa_elements = re.findall(qa_pattern, content_after_opening, re.S)
            if qa_elements:
                nested_found = True
                for qa_elem in qa_elements[:1]:  # Only process the first one
                    deeper_elements = find_deepest_interactive_element(qa_elem, goal)
                    if deeper_elements:
                        elements.extend(deeper_elements)
        
        # If no nested interactive elements found, check if this element itself is interactive
        if not nested_found:
            text = re.sub(r'<[^>]+>', ' ', html_chunk).strip()
            if is_clickable_div(attrs, text, goal):
                # Include relevant attributes and any data-* attributes  
                relevant_attrs = ["id", "class", "name", "role", "aria-label", "onclick", "data-testid", "tabindex"]
                for k in attrs.keys():
                    if k.startswith("data-"):
                        relevant_attrs.append(k)
                        
                filtered_attrs = {k: attrs.get(k, "") for k in relevant_attrs if k in attrs}
                
                elements.append(Element(
                    tag='div',
                    text=_extract_meaningful_text(text, attrs, 'div'),
                    attrs=filtered_attrs,
                    selectors=_candidate_selectors('div', attrs, text)
                ))
    
    return elements


def summarize_interactive_elements(html_content: str, max_items: int = INTERACTIVE_MAX_ITEMS, goal: str = "") -> List[Element]:
    """Extract interactive elements from HTML using lxml (primary) or regex (fallback)."""
    elements: List[Element] = []

    if HAS_LXML:
        try:
            tree = html.fromstring(html_content or "")
            
            # 1) Traditional interactive elements (buttons, links, inputs, selects)
            for tag_name in INTERACTIVE_TAGS:
                # Use CSS for speed and precision
                for elem in tree.cssselect(tag_name):
                    attrs = dict(elem.attrib)  # Clean dict, no BS4 list issues
                    raw_text = elem.text_content().strip() or ""  # Like BS4 get_text
                    text = _extract_meaningful_text(raw_text, attrs, tag_name)
                    selectors = _candidate_selectors(tag_name, attrs, text)
                    
                    # Same relevant attrs as before
                    relevant_attrs = [
                        "id", "class", "name", "role", "aria-label", "placeholder", "href",
                        "onclick", "data-testid", "tabindex"
                    ] + [k for k in attrs.keys() if k.startswith("data-")]
                    
                    elements.append(Element(
                        tag=tag_name,
                        text=text,
                        attrs={k: attrs.get(k, "") for k in relevant_attrs},
                        selectors=selectors
                    ))
                    if len(elements) >= max_items:
                        return elements

            
              # 2) Interactive divs/spans - use element identity instead of XPath
            processed_elements = set()

            def _add_clickable(elem):
                if id(elem) in processed_elements:
                    return False
                processed_elements.add(id(elem))
                
                attrs_dict = dict(elem.attrib)
                raw_text = elem.text_content().strip() or ""
                text = _extract_meaningful_text(raw_text, attrs_dict, elem.tag)

                if is_clickable_div(attrs_dict, text, goal):
                    selectors = _candidate_selectors(elem.tag, attrs_dict, text)

                    # Try to make the first selector unique; safe aria refinement + XPath fallback
                    if selectors and len(tree.cssselect(selectors[0])) > 1:
                        unique_selector_found = False
                        if attrs_dict.get('role'):
                            s = f"{selectors[0]}[role='{attrs_dict['role']}']"
                            if len(tree.cssselect(s)) == 1:
                                selectors.insert(0, s)
                                unique_selector_found = True
                        if not unique_selector_found and attrs_dict.get('aria-label'):
                            # Use the existing esc function from _candidate_selectors instead
                            aria_escaped = attrs_dict['aria-label'][:20].replace('"', r'\"')
                            s = f"{selectors[0]}[aria-label*=\"{aria_escaped}\"]"
                            if len(tree.cssselect(s)) == 1:
                                selectors.insert(0, s)
                                unique_selector_found = True
                        # Around line 324, replace the undefined 'path' with tree.getpath(elem):

                        
                        
                        if not unique_selector_found:
                            try:
                                # Don't insert XPath at position 0 - keep CSS selectors as primary
                                xpath = tree.getpath(elem)
                                selectors.append(xpath)  # Append at end, not insert at beginning
                            except AttributeError:
                                # Skip XPath fallback entirely if getpath isn't available
                                pass

                    relevant_attrs = [
                        "id", "class", "name", "role", "aria-label", "onclick", "data-testid", "tabindex"
                    ] + [k for k in attrs_dict.keys() if k.startswith("data-")]

                    elements.append(Element(
                        tag=elem.tag,
                        text=text,
                        attrs={k: attrs_dict.get(k, "") for k in relevant_attrs},
                        selectors=selectors
                    ))
                    return True
                return False

            # 2a) STRONG-LABEL PASS: data-* label attributes (works across many sites)
            strong_label_cards = tree.xpath(
                "//div[@data-qa-item-name or @data-qa-title or @data-qa-name or "
                "@data-testid or @data-test-id or @data-item-name or @data-name or @data-title or @data-label] | "
                "//span[@data-qa-item-name or @data-qa-title or @data-qa-name or "
                "@data-testid or @data-test-id or @data-item-name or @data-name or @data-title or @data-label]"
            )
            for elem in strong_label_cards:
                if len(elements) >= max_items:
                    return elements
                _add_clickable(elem)

            # 2b) GENERIC CLICKABLES: no data-* required; needs descendant text/aria/alt
            generic_clickables = tree.xpath(
                "("
                  "//div["
                    "@onclick or @role='button' or @role='menuitem' or @role='option' or @role='tab' or "
                    "(@tabindex and not(@tabindex='-1')) or "
                    "contains(concat(' ',normalize-space(@class),' '),' btn ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' button ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' clickable ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' card ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' tile ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' menu-item ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' option ') or "
                    ".//button or .//a[@href or @role='button'] or "
                    ".//*[@role='button' or @role='menuitem' or @role='option'] or "
                    ".//input[@type='radio' or @type='checkbox']"
                  "] | "
                  "//span["
                    "@onclick or @role='button' or @role='menuitem' or @role='option' or @role='tab' or "
                    "(@tabindex and not(@tabindex='-1')) or "
                    "contains(concat(' ',normalize-space(@class),' '),' btn ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' button ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' clickable ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' card ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' tile ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' menu-item ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' option ') or "
                    ".//button or .//a[@href or @role='button'] or "
                    ".//*[@role='button' or @role='menuitem' or @role='option'] or "
                    ".//input[@type='radio' or @type='checkbox']"
                  "]"
                ")"
                "["
                  "string-length(normalize-space(.)) > 1 or "
                  ".//*[@aria-label][string-length(normalize-space(@aria-label))>0] or "
                  ".//img[@alt][string-length(normalize-space(@alt))>0]"
                "]"
            )
            for elem in generic_clickables:
                if len(elements) >= max_items:
                    return elements
                _add_clickable(elem)

            # 2c) INTERACTIVE LIST ITEMS: li elements with roles or data attributes
            interactive_list_items = tree.xpath(
                "//li["
                    "@role='button' or @role='link' or @role='menuitem' or "
                    "@onclick or @data-button or @data-qa-item-name or "
                    "(@tabindex and not(@tabindex='-1')) or "
                    "contains(concat(' ',normalize-space(@class),' '),' btn ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' button ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' clickable ') or "
                    "contains(concat(' ',normalize-space(@class),' '),' menu-item ') or "
                    ".//button or .//a[@href or @role='button']"
                "]"
                "["
                  "string-length(normalize-space(.)) > 0"
                "]"
            )
            for elem in interactive_list_items:
                if len(elements) >= max_items:
                    return elements
                _add_clickable(elem)

            # 2d) CATCH-ALL PASS: Check all remaining divs/spans/li with enhanced clickable detection
            # This ensures we don't miss elements that don't match the hardcoded XPath patterns
            # but would be detected by the goal-aware clickable detection functions
            catch_all_elements = tree.xpath("//div | //span | //li")
            for elem in catch_all_elements:
                if len(elements) >= max_items:
                    return elements
                # Use enhanced detection that handles li elements specifically
                tag_name = elem.tag.lower()
                attrs_dict = dict(elem.attrib)
                text = (elem.text or "").strip()
                if is_clickable_element(tag_name, attrs_dict, text, goal):
                    _add_clickable(elem)

            return elements

            
        except Exception as e:
            print(f"⚠️ lxml parsing failed: {e}, falling back to regex")
            # Fall back to regex logic below
    
    # FALLBACK: Regex-based extraction (original logic)
    # Traditional interactive elements (a, button, input, select)
    pattern = re.compile(r"<\s*(a|button|input|select)\b([^>]*)>(.*?)</\s*\1\s*>", re.I | re.S)
    self_closing = re.compile(r"<\s*(input)\b([^>]*)/?>", re.I)  # Only input is self-closing
    
    # Interactive DIVs and SPANs with click handlers, roles, or navigation keywords
    interactive_div_pattern = re.compile(r"<\s*(div|span)\b([^>]*)>(.*?)</\s*\1\s*>", re.I | re.S)
    
    # 1) Capture traditional interactive elements
    for m in pattern.finditer(html_content or ""):
        tag = m.group(1).lower()
        attrs = _extract_attrs(m.group(2))
        raw_text = re.sub(r"<[^>]+>", " ", m.group(3))
        text = _extract_meaningful_text(raw_text, attrs, tag)
        selectors = _candidate_selectors(tag, attrs, text)
        
        # Include relevant attributes and any data-* attributes
        relevant_attrs = ["id", "class", "name", "role", "aria-label", "placeholder", "href", "onclick", "data-testid", "tabindex"]
        for k in attrs.keys():
            if k.startswith("data-"):
                relevant_attrs.append(k)
        
        elements.append(Element(
            tag=tag,
            text=text,
            attrs={k: attrs.get(k, "") for k in relevant_attrs},
            selectors=selectors
        ))

    # 2) Capture self-closing elements
    for m in self_closing.finditer(html_content or ""):
        tag = m.group(1).lower()
        attrs = _extract_attrs(m.group(2))
        text = ""  # Self-closing elements have no inner text
        selectors = _candidate_selectors(tag, attrs, text)
        
        elements.append(Element(
            tag=tag,
            text=text,
            attrs={k: attrs.get(k, "") for k in ["id","class","name","role","aria-label","placeholder","href","onclick","data-testid","tabindex"]},
            selectors=selectors
        ))

    # 3) Capture interactive divs and spans using depth-first search
    processed_chunks = set()  # Track processed HTML chunks to avoid duplicates
    
    for m in interactive_div_pattern.finditer(html_content or ""):
        full_element_html = m.group(0)  # The complete matched element
        
        # Create a hash of the element to avoid processing duplicates
        element_hash = hashlib.md5(full_element_html.encode()).hexdigest()
        if element_hash in processed_chunks:
            continue
        processed_chunks.add(element_hash)
        
        # Use the new depth-first search to find the deepest interactive element
        deeper_elements = find_deepest_interactive_element(full_element_html, goal)
        
        # Add the deepest elements found
        elements_added = False
        for element in deeper_elements:
            elements.append(element)
            elements_added = True
            if len(elements) >= max_items:
                return elements
        
        # If no deeper elements found, fallback to original logic
        if not elements_added:
            tag = m.group(1).lower()
            attrs = _extract_attrs(m.group(2))
            raw_text = re.sub(r"<[^>]+>", " ", m.group(3))
            text = _extract_meaningful_text(raw_text, attrs, tag)
            
            if is_clickable_div(attrs, text, goal):
                selectors = _candidate_selectors(tag, attrs, text)
                
                # Include relevant attributes and any data-* attributes
                relevant_attrs = ["id", "class", "name", "role", "aria-label", "onclick", "data-testid", "tabindex"]
                for k in attrs.keys():
                    if k.startswith("data-"):
                        relevant_attrs.append(k)
                
                elements.append(Element(
                    tag=tag,
                    text=text,
                    attrs={k: attrs.get(k, "") for k in relevant_attrs},
                    selectors=selectors
                ))

    return elements  # Don't slice here - let scoring function handle the limit


def score_interactive_elements(elements: List[Element], goal: str) -> List[Element]:
    """Score and sort interactive elements based on goal relevance."""
    goal_lower = goal.lower()
    wants_location = any(k in goal_lower for k in ("location", "store", "restaurant", "zip", "postal"))
    
    for element in elements:
        score = 0.0
        text = element.text.lower()
        attrs = element.attrs
        roles = (attrs.get("role") or "").lower()
        placeholder = (attrs.get("placeholder") or "").lower()
        aria = (attrs.get("aria-label") or "").lower()
        name = (attrs.get("name") or "").lower()
        href = (attrs.get("href") or "").lower()
        classes = _safe_get_class_string(attrs).lower()
        
        # Base score for interactive tag/role with STRONG priority for truly interactive elements
        if element.tag in INTERACTIVE_TAGS: 
            # PRIORITY BOOST: True interactive elements get massive base boost
            if element.tag == "a" and attrs.get("href"):
                score += 5.0  # Massive boost for actual links
            elif element.tag == "button":
                score += 4.0  # Big boost for buttons
            elif element.tag == "input":
                score += 3.0  # Good boost for inputs
            elif element.tag == "select":
                score += 3.0  # Good boost for selects
            elif element.tag == "li" and (attrs.get("role") in ["button", "menuitem"] or attrs.get("onclick") or attrs.get("data-button")):
                score += 2.5  # Good boost for interactive li elements
            else:
                score += 1.0  # Standard boost for other interactive tags
                
        if roles in INTERACTIVE_ROLES: 
            score += 0.5

        # PRIORITY BOOST: Elements with semantic data attributes
        data_attrs_priority = [
            "data-qa-group-name", "data-qa-item-name", "data-qa-name", 
            "data-button", "data-menu-item", "data-item-name"
        ]
        for attr_name in data_attrs_priority:
            if attrs.get(attr_name):
                score += 2.0  # Major boost for semantic data attributes
                if DEBUG:
                    print(f"🎯 Boosting element with {attr_name}='{attrs[attr_name]}' by +2.0")
                break  # Only apply once per element

        # Location finder boosts - only apply if goal wants location
        if wants_location:
            location_finder_phrases = ["find location", "find store", "store locator", "find a store", "find locations"]
            for phrase in location_finder_phrases:
                if phrase in text or phrase in classes:
                    score += 3.0  # MASSIVE boost for location finder
                    
            # Extra boost for generic location finder patterns
            if ("find" in text and any(w in text for w in ("store", "location", "restaurant", "shop"))):
                score += 2.5  # High boost for "find [location type]" patterns
                
        # Enhanced keyword boosts for web automation
        all_text = " ".join([text, placeholder, aria, name, href, classes])
        for kw in KEYWORD_BOOST:
            if kw in all_text: 
                score += 0.8  # Increased from 0.6 like old system
        
        # Extra boost for primary action indicators (matching old system)
        primary_actions = ["order now", "buy now", "get started", "begin", "add to cart", "checkout", "start", "shop now"]
        for action in primary_actions:
            if action in all_text: 
                score += 1.2  # Strong boost for primary actions
        
        # Modal dismissal keywords
        modal_keywords = ["accept", "agree", "continue", "close", "got it", "dismiss", "ok"]
        for mk in modal_keywords:
            if mk in all_text: 
                score += 0.7

        # ENHANCED: Strongly prioritize input fields for location/ZIP entry
        if element.tag == "input":
            score += 0.5  # Base boost for inputs
            
            # Big boost for location/ZIP input fields
            location_input_keywords = ["zip", "postal", "address", "location", "city", "state"]
            for lk in location_input_keywords:
                if lk in placeholder or lk in aria or lk in name:
                    # MASSIVE boost for location inputs - they should rank highest for location goals
                    if wants_location:
                        score += 8.0  # MASSIVE boost when goal wants location
                    else:
                        score += 2.0  # Regular boost otherwise
                    
            # Boost for text inputs (where you can type)
            input_type = (attrs.get("type") or "").lower()
            if input_type in ["text", "search", "tel", ""]:
                score += 0.8
                
        # Enhanced scoring for interactive divs/spans - conditional on clickability
        if element.tag in ["div", "span"]:
            # SPECIAL CASE: Form container elements should get base boost
            form_container_classes = ["input-container", "form-group", "field-container", "input-field", "form-control"]
            is_form_container = any(container_class in classes for container_class in form_container_classes)
            
            if is_form_container:
                score += 2.0  # Base boost for form containers to compete with interactive elements
                if DEBUG:
                    print(f"📋 Form container boost: '{text}' got +2.0 for class containing form indicator")
            
            # Use the same is_clickable_div logic from element extraction
            attrs_dict = {k: v for k, v in element.attrs.items()}  # Convert to dict if needed
            if is_clickable_div(attrs_dict, element.text, goal):
                # PENALTY: Divs/spans that are just text containers shouldn't beat real interactive elements
                # Only give boost if they have clear interactive indicators
                has_strong_interactive_signals = (
                    attrs.get("onclick") or 
                    attrs.get("role") in ["button", "menuitem", "option", "tab"] or
                    (attrs.get("tabindex") and attrs.get("tabindex") != "-1") or
                    any(attr.startswith("data-qa-") for attr in attrs.keys()) or
                    "btn" in classes or "button" in classes or
                    is_form_container  # Form containers are considered strong signals
                )
                
                if has_strong_interactive_signals:
                    score += 1.2  # Good boost for truly interactive divs
                else:
                    score += 0.3  # Small boost for divs that might be clickable but lack strong signals
                    # Additional penalty if this looks like a text container with multiple navigation words
                    nav_words_in_text = sum(1 for word in ["menu", "catering", "rewards", "values", "nutrition"] 
                                          if word in text.lower())
                    if nav_words_in_text >= 3:
                        score -= 1.0  # Penalty for navigation bar containers
                
        # Location-related keywords for buttons/links
        location_keywords = ["find location", "store locator", "enter zip"]
        for lk in location_keywords:
            if lk in all_text: 
                score += 1.5  # Good boost but less than input fields

        # PENALTY: Reduce score for "all locations" type links 
        if "all" in text and "location" in text:
            score -= 1.0  # Penalty for "all locations" links
            
        # PENALTY: Reduce score for "view all" type links
        if "view" in text and ("all" in text or "more" in text):
            score -= 0.8

        # Penalty for generic or problematic elements
        if "javascript:" in href: 
            score -= 0.5
        if element.tag == "a" and not href: 
            score -= 0.3
        if len(text) > 100: 
            score -= 0.2  # Very long text might be noisy

        # Boost for meaningful text
        if 3 <= len(text) <= 50: 
            score += 0.3
        elif len(text) > 50: 
            score += 0.1

        # Boost for specific attributes that indicate interactivity
        if attrs.get("onclick"): 
            score += 0.4
        if attrs.get("data-testid"): 
            score += 0.3
        if "btn" in classes or "button" in classes: 
            score += 0.5
            
        # NAVIGATION BOOST: Links with page section hrefs (like #menu, #about, etc.)
        if element.tag == "a" and href:
            if href.startswith("#") and len(href) > 1:  # Page section links like #menu
                score += 2.0  # Big boost for internal navigation links
            elif any(nav_word in href for nav_word in ["menu", "order", "location", "store"]):
                score += 1.5  # Good boost for navigation-related links

        # COMPOUND SCORING: Extract goal keywords and apply massive boosts
        goal_keywords = []
        goal_words = goal_lower.split()
        
        # Extract meaningful words from goal (skip common words)
        skip_words = {'the', 'a', 'an', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'over', 'under', 'between', 'among', 'through', 'during', 'before', 'after', 'above', 'below', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall', 'and', 'or', 'but', 'nor', 'so', 'yet', 'as', 'if', 'then', 'than', 'when', 'where', 'while', 'how', 'why', 'what', 'which', 'who', 'whom', 'whose', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'his', 'hers', 'ours', 'theirs', 'myself', 'yourself', 'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves'}
        
        # ALSO skip action/instruction words that shouldn't match menu items
        # NOTE: Removed 'enter' and 'type' as they're important for form field detection
        action_words = {'select', 'choose', 'pick', 'click', 'build', 'your', 'own', 'option', 'as', 'order', 'get', 'go', 'find', 'then', 'me'}
        
        # Separate high-priority target words from action words
        target_keywords = []  
        general_keywords = []  # Action words, modifiers
        
        for word in goal_words:
            clean_word = word.strip('.,!?;:"()[]{}\'').lower()  # Added single quotes
            if len(clean_word) >= 2 and clean_word not in skip_words:
                if clean_word in action_words:
                    general_keywords.append(clean_word)
                else:
                    target_keywords.append(clean_word)
        
        # Count matches with different weights (case insensitive)
        # Use word boundary matching to avoid false positives like "enter" matching "center"
        import re
        text_lower = text.lower()
        target_matches = sum(1 for kw in target_keywords if re.search(r'\b' + re.escape(kw) + r'\b', text_lower))
        general_matches = sum(1 for kw in general_keywords if re.search(r'\b' + re.escape(kw) + r'\b', text_lower))
        
        # Only show debug for elements that actually get keyword matches
        if target_matches > 0 or general_matches > 0:
            print(f"🔍 '{text}' -> keywords: {target_keywords} -> matches: target={target_matches}, general={general_matches}")
        
        # Apply weighted compound boosts
        total_boost = 0
        if target_matches > 0:
            # TARGET WORDS get massive boost (food items, proteins, etc.)
            target_boost = target_matches * 3.0  # 3.0 per target word
            total_boost += target_boost
            
        if general_matches > 0:
            # GENERAL/ACTION WORDS get smaller boost
            general_boost = general_matches * 0.5  # 0.5 per action word
            total_boost += general_boost
        
        # Apply compound boosts based on total matches + high-value attributes
        if total_boost > 0:
            # MASSIVE compound boost if element has BOTH goal keywords AND high-value data attributes
            high_value_attrs = ['data-qa-item-name', 'data-qa-group-name', 'data-menu-item', 'data-item-name', 'data-testid', 'data-track']
            has_high_value_attr = any(attr_name in attrs for attr_name in high_value_attrs)
            
            if has_high_value_attr:
                compound_boost = total_boost * 3.0  # Triple the boost for high-value attributes
                score += compound_boost
                # Debug logging for compound boosts
                print(f"🎯 COMPOUND BOOST: '{text}' got +{compound_boost:.1f} (target: {target_matches}, general: {general_matches}, high-value attrs: {has_high_value_attr})")
            else:
                score += total_boost
                # Debug logging for keyword-only boosts  
                print(f"🔍 KEYWORD BOOST: '{text}' got +{total_boost:.1f} (target: {target_matches}, general: {general_matches})")
        
        # ENHANCED: Check for multi-word exact matches (like "fajita veggies")
        # This gives even bigger boost when the exact phrase appears
        # COMMENTED OUT: Site-specific phrase matching logic
        # goal_phrase = goal_lower.replace("add", "").replace("'", "").replace('"', "").replace("as a topping", "").replace("as", "").strip()
        # if len(goal_phrase.split()) >= 2 and goal_phrase in text.lower():
        #     phrase_boost = 5.0  # MASSIVE boost for exact phrase match
        #     score += phrase_boost
        #     print(f"🔥 PHRASE MATCH: '{text}' got +{phrase_boost:.1f} for exact phrase '{goal_phrase}'")
        
        # COMMENTED OUT: Form field specific boosting - let generic keyword matching handle this
        # FORM FIELD DETECTION: Boost elements that look like input prompts or labels
        # form_prompt_indicators = [
        #     ("enter", "name"), ("meal", "name"), ("enter", "meal"), 
        #     ("type", "name"), ("input", "name"), ("name", "field"),
        #     ("enter", "text"), ("provide", "name")
        # ]
        # 
        # text_words = text_lower.split()
        # for word1, word2 in form_prompt_indicators:
        #     if word1 in text_words and word2 in text_words:
        #         form_boost = 8.0  # MASSIVE boost for form field prompts
        #         score += form_boost
        #         print(f"📝 FORM FIELD BOOST: '{text}' got +{form_boost:.1f} for form prompt indicators '{word1}' + '{word2}'")
        #         break  # Only apply once per element
        # 
        # # INPUT CONTAINER BOOST: Elements with class "input-container" or similar
        # input_container_classes = ["input-container", "form-group", "field-container", "input-field"]
        # if any(container_class in classes for container_class in input_container_classes):
        #     container_boost = 5.0  # Big boost for input containers
        #     score += container_boost
        #     print(f"📋 INPUT CONTAINER BOOST: '{text}' got +{container_boost:.1f} for input container class")

        element.score = max(0.0, score)  # Ensure non-negative
    
    # REMOVED: Site-specific goal-aware post-processing (redundant with compound boost system)
    # The compound boost system above already extracts keywords from goals and applies
    # generic boosts to matching elements, making hardcoded food/location logic unnecessary.
    #
    # # GOAL-AWARE POST-PROCESSING: Apply additional goal-specific boosts and re-sort
    # goal_lower = goal.lower()
    # print(f"🎯 Goal-aware processing for: '{goal}'")
    # 
    # # Menu selection goals (like "Select 'Bowl'")
    # has_select_keyword = any(keyword in goal_lower for keyword in ["select", "choose", "pick"])
    # has_food_keyword = any(food_type in goal_lower for food_type in ["bowl", "burrito", "taco", "salad", "quesadilla"])
    # print(f"🎯 Has select keyword: {has_select_keyword}, Has food keyword: {has_food_keyword}")
    # 
    # if has_select_keyword and has_food_keyword:
    #     print(f"🍽️ DETECTED MENU SELECTION GOAL!")
    #     menu_boosted = 0
    #     for element in elements:
    #         text = element.text.lower()
    #         attrs = element.attrs
    #         classes = _safe_get_class_string(attrs).lower()
    #         
    #         # Extract the specific food item from goal (e.g., "bowl" from "Select 'Bowl'")
    #         goal_food_items = []
    #         for food_type in ["bowl", "burrito", "taco", "salad", "quesadilla", "chips", "drink", "kids meal"]:
    #             if food_type in goal_lower:
    #                 goal_food_items.append(food_type)
    #         
    #         print(f"🍽️ Goal food items: {goal_food_items}")
    #         
    #         # MASSIVE boost for exact menu item matches
    #         for food_item in goal_food_items:
    #             if food_item in text or f"{food_item}" in text:
    #                 original_score = element.score
    #                 element.score = original_score + 6.0  # Massive boost for menu items
    #                 menu_boosted += 1
    #                 print(f"🍽️ MENU BOOST: '{element.text}' got +6.0 for '{food_item}' match")
    #         
    #         # Additional boost for menu-related classes/attributes
    #         menu_indicators = ["menu", "top-level-menu", "meal", "item", "card"]
    #         if any(indicator in classes for indicator in menu_indicators) and any(food_item in text for food_item in goal_food_items):
    #             element.score += 2.0  # Additional boost for menu containers
    #             menu_boosted += 1
    #     
    #     if menu_boosted > 0:
    #         print(f"🍽️ Menu goal detected: Boosted {menu_boosted} menu elements")
    #         # Re-sort after boosting scores
    #         elements.sort(key=lambda x: x.score, reverse=True)
    # 
    # # Location selection goals
    # elif any(keyword in goal_lower for keyword in ["select", "choose", "pick", "nearest"]) and \
    #      any(keyword in goal_lower for keyword in ["location", "restaurant", "store"]):
    #     location_boosted = 0
    #     for element in elements:
    #         text = element.text.lower()
    #         attrs = element.attrs
    #         classes = _safe_get_class_string(attrs).lower()
    #         
    #         # PRIORITY 1: Boost location/store container elements (most clickable)
    #         location_attrs = [
    #             "data-qa-restaurant-id", "data-store-id", "data-location-id", 
    #             "data-shop-id", "data-venue-id", "data-place-id"
    #         ]
    #         
    #         has_location_attr = any(attrs.get(attr) for attr in location_attrs)
    #         has_location_class = any(container_class in classes 
    #                                for container_class in ['restaurant-address-item', 'location-item', 
    #                                                       'store-item', 'store-card', 'location-card', 'venue-item'])
    #         
    #         if has_location_attr or has_location_class:
    #             original_score = element.score
    #             element.score = original_score + 8.0  # Highest boost for containers
    #             location_boosted += 1
    #         
    #         # PRIORITY 2: Boost location/address elements (for context, but lower than containers)
    #         elif (element.attrs.get("role") == "definition" and 
    #               any(loc_word in text for loc_word in ['near', 'mile', 'mi', 'km', 'street', 'road', 'avenue', 'boulevard', 'drive', 'lane', 'way'])) or \
    #              any(loc_class in classes for loc_class in ['address', 'location', 'result', 'store', 'restaurant']) or \
    #              any(distance in text for distance in ['mile', 'mi', 'km', 'away']):
    #             
    #             original_score = element.score
    #             element.score = original_score + 4.0  # Lower boost for text elements
    #             location_boosted += 1
    #     
    #     if location_boosted > 0:
    #         #print(f"🎯 Location goal detected: Boosted {location_boosted} location elements")
    #         # Re-sort after boosting scores
    #         elements.sort(key=lambda x: x.score, reverse=True)
    
    # Sort by score (highest first) and limit to max items
    ranked = sorted(elements, key=lambda e: e.score, reverse=True)
    return ranked[:INTERACTIVE_MAX_ITEMS]


async def create_page_context(page, goal: str = "", step_number: int = 1, total_steps: int = 1, 
                            recent_events: List[Dict] = None, lattice_state: Dict = None,
                            previous_dom_signature: str = "", debug_run_folder: str = None) -> PageContext:
    """Enhanced context creation with two-pass approach: extract elements from FULL DOM, then compress."""
    
    # PASS 1: Get the FULL DOM and extract ALL interactive elements before any compression
    raw_dom = await page.content()
    
    # CRITICAL: Extract elements from FULL DOM before any compression or truncation
    if DEBUG:
        print(f"� Extracting interactive elements from full DOM ({len(raw_dom)} chars)")
    
    elements = summarize_interactive_elements(raw_dom, INTERACTIVE_MAX_ITEMS, goal)  # FIXED: Pass goal parameter
    scored_elements = score_interactive_elements(elements, goal)
    
    if DEBUG:
        print(f"🎯 Found {len(scored_elements)} interactive elements from full DOM")
        # Show top 5 elements for debugging
        for i, elem in enumerate(scored_elements[:5], 1):
            print(f"   {i}. {elem.tag} - '{elem.text}' (score: {elem.score:.1f})")
    
    # PASS 2: Now compress for skeleton/context (but we already have our elements)
    compressed = compress_dom(raw_dom, goal)
    skeleton = create_dom_skeleton(compressed)
    signature = page_signature(compressed)
    
    if DEBUG:
        print(f"📄 Compressed DOM from {len(raw_dom)} to {len(compressed)} chars")
    
    return PageContext(
        url=await page.evaluate("location.href"),
        title=await page.title(),
        raw_dom=compressed,  # Use compressed for context
        skeleton=skeleton,
        signature=signature,
        interactive=scored_elements,  # These came from FULL DOM
        goal=goal,
        step_number=step_number,
        total_steps=total_steps,
        recent_events=recent_events or [],
        lattice_state=lattice_state or {},
        previous_dom_signature=previous_dom_signature
    )


def create_page_context_sync(url: str, title: str, raw_dom: str, goal: str = "", 
                           step_number: int = 1, total_steps: int = 1, 
                           overall_goal: str = "", recent_events: List[Dict] = None,
                           previous_signature: str = "", lattice_state: Dict = None, 
                           debug_run_folder: str = None) -> PageContext:
    """
    Synchronous wrapper for create_page_context that uses two-pass approach:
    1. Extract elements from FULL DOM
    2. Compress DOM for context
    """
    
    # PASS 1: Extract elements from FULL DOM before any compression
    if DEBUG:
        print(f"🔍 Extracting interactive elements from full DOM ({len(raw_dom)} chars)")
    
    elements = summarize_interactive_elements(raw_dom, INTERACTIVE_MAX_ITEMS, goal)  # Use full DOM with goal
    scored_elements = score_interactive_elements(elements, goal)
    
    if DEBUG:
        print(f"🎯 Found {len(scored_elements)} interactive elements from full DOM")
    
    # PASS 2: Compress DOM for context and signatures
    compressed = compress_dom(raw_dom, goal)
    signature = page_signature(raw_dom)
    skeleton = create_dom_skeleton(compressed)
    
    if DEBUG:
        print(f"📄 Compressed DOM from {len(raw_dom)} to {len(compressed)} chars")
    
    # Debug all input elements found
    print(f"\n🔍 DOM DEBUG: Found {len(elements)} total interactive elements")
    input_elements = [elem for elem in elements if elem.tag in ['input', 'textarea']]
    print(f"🔍 DOM DEBUG: Found {len(input_elements)} input/textarea elements:")
    
    for i, elem in enumerate(input_elements):
        input_type = elem.attrs.get('type', 'text')
        placeholder = elem.attrs.get('placeholder', '')
        name = elem.attrs.get('name', '')
        id_val = elem.attrs.get('id', '')
        print(f"  {i+1}. <{elem.tag}> type='{input_type}' id='{id_val}' name='{name}' placeholder='{placeholder}' text='{elem.text[:50]}'")
    
    # Debug scoring results
    print(f"\n🔍 DOM DEBUG: After scoring, {len(scored_elements)} elements made the cut:")
    scored_inputs = [elem for elem in scored_elements if elem.tag in ['input', 'textarea']]
    print(f"🔍 DOM DEBUG: {len(scored_inputs)} input/textarea elements in scored results:")
    
    for i, elem in enumerate(scored_inputs):
        input_type = elem.attrs.get('type', 'text')
        placeholder = elem.attrs.get('placeholder', '')
        print(f"  {i+1}. <{elem.tag}> type='{input_type}' placeholder='{placeholder}' score={getattr(elem, 'score', 'N/A')}")
    
    # Save debug output
    if debug_run_folder:
        debug_file = os.path.join(debug_run_folder, f"dom_debug_step{step_number}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}.txt")
    else:
        debug_file = f"debug_prompts/dom_debug_step{step_number}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}.txt"
    
    os.makedirs(os.path.dirname(debug_file), exist_ok=True)
    with open(debug_file, 'w', encoding='utf-8') as f:
        f.write(f"DOM Debug Report - Step {step_number}\n")
        f.write(f"={'='*50}\n\n")
        f.write(f"URL: {url}\n")
        f.write(f"Goal: {goal}\n")
        f.write(f"Raw DOM Length: {len(raw_dom)} chars\n\n")
        
        f.write(f"All Interactive Elements ({len(scored_elements)}):\n")
        f.write("-" * 50 + "\n")
        for i, elem in enumerate(scored_elements):
            selectors = getattr(elem, 'selectors', [])
            selector_info = f" selectors={selectors[:3]}" if selectors else " selectors=[]"
            f.write(f"{i+1:3d}. <{elem.tag}> {elem.attrs}{selector_info}\n")
            f.write(f"     text: '{elem.text[:200]}'\n")
            if hasattr(elem, 'score'):
                f.write(f"     score: {elem.score}\n")
            f.write("\n")
        
        f.write(f"\nInput/Textarea Elements ({len(input_elements)}):\n")
        f.write("-" * 50 + "\n")
        for i, elem in enumerate(input_elements):
            selectors = getattr(elem, 'selectors', [])
            selector_info = f" selectors={selectors[:3]}" if selectors else " selectors=[]"
            f.write(f"{i+1:3d}. <{elem.tag}> {elem.attrs}{selector_info}\n")
            f.write(f"     text: '{elem.text[:200]}'\n")
            if hasattr(elem, 'score'):
                f.write(f"     score: {elem.score}\n")
            f.write("\n")
        
        f.write(f"\nTop 20 Scored Elements (Ranked by AI Selection Priority):\n")
        f.write("-" * 50 + "\n")
        f.write("This shows exactly what elements the AI system had to choose from,\n")
        f.write("ranked by relevance score. The progressive disclosure system starts\n")
        f.write("with top 10, then expands to 20, 30, 40, 50 if needed.\n\n")
        for i, elem in enumerate(scored_elements[:20]):
            score = getattr(elem, 'score', 'N/A')
            selectors = getattr(elem, 'selectors', [])
            primary_selector = selectors[0] if selectors else "No selector"
            f.write(f"RANK {i+1:2d}: score={score:>6} <{elem.tag}> {primary_selector}\n")
            f.write(f"        attrs: {elem.attrs}\n")
            f.write(f"        text: '{elem.text[:150]}'\n")
            if len(selectors) > 1:
                f.write(f"        alt selectors: {selectors[1:3]}\n")
            f.write("\n")
    
    print(f"🔍 DOM DEBUG: Full debug report saved: {debug_file}")
    
    ########################################################
    
    return PageContext(
        url=url,
        title=title or "Untitled",
        raw_dom=compressed,  # Store compressed version
        skeleton=skeleton,
        signature=signature,
        interactive=scored_elements,
        step_number=step_number,
        total_steps=total_steps,
        overall_goal=overall_goal or goal,
        # Enhanced context fields
        current_step=step_number,
        total_steps_planned=total_steps,
        recent_events=recent_events or [],
        previous_dom_signature=previous_signature,
        dom_signature=signature,  # Alias for consistency
        lattice_state=lattice_state
    )
