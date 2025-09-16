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
DOM_TRUNCATE_CHARS = int(os.getenv("WEB_AGENT_DOM_TRUNCATE_CHARS", "18000"))
DOM_TRUNCATE_CHARS_LOCATION = int(os.getenv("WEB_AGENT_DOM_TRUNCATE_CHARS_LOCATION", "70000"))

# Interactive element processing limits
INTERACTIVE_MAX_ITEMS = int(os.getenv("WEB_AGENT_INTERACTIVE_MAX_ITEMS", "100"))
INTERACTIVE_INCLUDE_TEXT_MAX = int(os.getenv("WEB_AGENT_INTERACTIVE_INCLUDE_TEXT_MAX", "80"))

# Keyword boosts for scoring
KEYWORD_BOOST = [
    "order", "buy", "shop", "start", "begin", "find", "location", "search", "submit",
    "accept", "agree", "continue", "next", "add", "cart", "checkout", "zip", "address",
    "pickup", "delivery", "login", "sign in", "apply", "continue as guest",
]

INTERACTIVE_TAGS = {"a", "button", "input", "select"}
INTERACTIVE_ROLES = {
    "button", "link", "dialog", "combobox", "textbox", "menuitem", "option", 
    "tab", "switch", "checkbox", "radio", "menu", "menuitemcheckbox", 
    "menuitemradio", "treeitem"
}


def _safe_get_class_string(attrs: Dict[str, Any]) -> str:
    """Safely get class attribute as string, handling AttributeValueList objects"""
    class_value = attrs.get('class', '')
    if hasattr(class_value, '__iter__') and not isinstance(class_value, str):
        # Handle AttributeValueList or other iterable types
        return ' '.join(str(cls) for cls in class_value)
    return str(class_value)


def compress_dom(raw_dom: str, goal: str = "") -> str:
    """Compress DOM by removing scripts/styles and applying goal-aware size limits."""
    # Use higher limit for location selection steps
    goal_lower = goal.lower()
    if any(keyword in goal_lower for keyword in ['select', 'choose', 'pick', 'nearest']) and \
       any(keyword in goal_lower for keyword in ['location', 'restaurant', 'store']):
        max_chars = DOM_TRUNCATE_CHARS_LOCATION
        if DEBUG:
            print(f"🎯 Using extended DOM limit ({max_chars}) for location selection")
    else:
        max_chars = DOM_TRUNCATE_CHARS
    
    # Strip scripts/styles and collapse whitespace
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw_dom, flags=re.DOTALL|re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:max_chars]


def page_signature(raw_dom: str) -> str:
    """Create a hash signature for the DOM to detect changes."""
    return hashlib.sha256(raw_dom.encode("utf-8")).hexdigest()[:16]


def _extract_meaningful_text(raw_text: str, attrs: Dict[str, Any]) -> str:
    """Extract meaningful text from element, prioritizing data attributes over comprehensive text."""
    
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
    
    # PRIORITY 1: Chipotle/QA-specific data attributes (most unique)
    if attrs.get("data-qa-item-name"):
        sels.append(f"{tag}[data-qa-item-name=\"{esc(attrs['data-qa-item-name'])}\"]")
    elif attrs.get("data-qa-group-name"):
        sels.append(f"{tag}[data-qa-group-name=\"{esc(attrs['data-qa-group-name'])}\"]")
    elif attrs.get("data-testid"):
        sels.append(f"{tag}[data-testid=\"{esc(attrs['data-testid'])}\"]")
    elif attrs.get("data-qa-name"):
        sels.append(f"{tag}[data-qa-name=\"{esc(attrs['data-qa-name'])}\"]")
    
    # PRIORITY 2: ID (highly unique)
    if attrs.get("id"):
        sels.append(f"#{attrs['id']}")
    
    # PRIORITY 3: Classes
    classes = _safe_get_class_string(attrs).strip()
    if classes:
        # take up to first two classes to keep selectors short
        cls = ".".join(c for c in classes.split()[:2])
        if cls:
            sels.append(f"{tag}.{cls}")
    
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


def is_clickable_div(attrs: Dict[str, str], text: str) -> bool:
    """Determine if a div/span is likely clickable based on attributes and content."""
    # Priority 1: QA test attributes (highest priority - these are explicit markers)
    qa_attrs = [
        "data-qa-item-name", "data-qa-group-name", "data-qa-name",
        "data-testid", "data-test-id"
    ]
    if any(attrs.get(attr) for attr in qa_attrs):
        return True
    
    # Priority 2: Menu items with data attributes (e.g., Chipotle menu categories)
    menu_attrs = [
        "data-menu-item", "data-menu-category", "data-item-name", 
        "data-category", "data-meal-type"
    ]
    if any(attrs.get(attr) for attr in menu_attrs):
        return True
        
    # Priority 3: Location/store containers with identifying attributes
    location_attrs = [
        "data-qa-restaurant-id", "data-store-id", "data-location-id", 
        "data-shop-id", "data-venue-id", "data-place-id"
    ]
    if any(attrs.get(attr) for attr in location_attrs):
        return True
        
    # Priority 3: Check for explicit click indicators
    if attrs.get("onclick"): return True
    if attrs.get("role") in ["button", "link", "tab", "menuitem"]: return True
    if "tabindex" in attrs and attrs["tabindex"] != "-1": return True
    
    # Check for navigation/location keywords in text or classes
    combined_text = " ".join([
        text.lower(),
        _safe_get_class_string(attrs).lower(),
        attrs.get("data-testid", "").lower(),
        attrs.get("aria-label", "").lower()
    ])
    
    # Strong indicators this is a navigation/location element OR menu item
    navigation_keywords = [
        "find", "locate", "location", "store", "shop", "order", 
        "menu", "navigation", "nav", "click", "button", "link",
        "bowl", "burrito", "taco", "salad", "quesadilla", "food",
        "meal", "item", "build", "custom", "lifestyle"
    ]
    
    # Special boost for obvious location finder elements
    location_phrases = [
        "find location", "find store", "store locator", 
        "location finder", "enter location", "location search",
        "find a store", "store finder", "find locations"
    ]
    
    for phrase in location_phrases:
        if phrase in combined_text:
            return True
            
    # Check if multiple navigation keywords are present
    keyword_count = sum(1 for kw in navigation_keywords if kw in combined_text)
    if keyword_count >= 2:
        return True
        
    # Check for button-like classes
    button_classes = ["btn", "button", "clickable", "interactive", "link"]
    for btn_class in button_classes:
        if btn_class in _safe_get_class_string(attrs).lower():
            return True
            
    return False


def summarize_interactive_elements(html_content: str, max_items: int = INTERACTIVE_MAX_ITEMS) -> List[Element]:
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
                    text = _extract_meaningful_text(raw_text, attrs)
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
                text = _extract_meaningful_text(raw_text, attrs_dict)

                if is_clickable_div(attrs_dict, text):
                    selectors = _candidate_selectors(elem.tag, attrs_dict, text)

                    # Try to make the first selector unique; safe aria refinement + XPath fallback
                    if selectors and len(tree.cssselect(selectors[0])) > 1:
                        unique_selector_found = False
                        if attrs.get('role'):
                            s = f"{selectors[0]}[role='{attrs['role']}']"
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
                            selectors.insert(0, tree.getpath(elem))  # unique XPath fallback

                    relevant_attrs = [
                        "id", "class", "name", "role", "aria-label", "onclick", "data-testid", "tabindex"
                    ] + [k for k in attrs.keys() if k.startswith("data-")]

                    elements.append(Element(
                        tag=elem.tag,
                        text=text,
                        attrs={k: attrs.get(k, "") for k in relevant_attrs},
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
        text = _extract_meaningful_text(raw_text, attrs)
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

    # 3) Capture interactive divs and spans
    for m in interactive_div_pattern.finditer(html_content or ""):
        tag = m.group(1).lower()
        attrs = _extract_attrs(m.group(2))
        raw_text = re.sub(r"<[^>]+>", " ", m.group(3))
        text = _extract_meaningful_text(raw_text, attrs)
        
        if is_clickable_div(attrs, text):
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
        
        # Base score for interactive tag/role
        if element.tag in INTERACTIVE_TAGS: 
            score += 1.0
        if roles in INTERACTIVE_ROLES: 
            score += 0.5

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
                    score += 2.0  # MAJOR boost for location inputs
                    
            # Boost for text inputs (where you can type)
            input_type = (attrs.get("type") or "").lower()
            if input_type in ["text", "search", "tel", ""]:
                score += 0.8
                
        # Enhanced scoring for interactive divs/spans - conditional on clickability
        if element.tag in ["div", "span"]:
            # Use the same is_clickable_div logic from element extraction
            attrs_dict = {k: v for k, v in element.attrs.items()}  # Convert to dict if needed
            if is_clickable_div(attrs_dict, element.text):
                score += 1.2  # Good boost for clickable divs ONLY
                
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

        # COMPOUND SCORING: Extract goal keywords and apply massive boosts
        goal_keywords = []
        goal_words = goal_lower.split()
        
        # Extract meaningful words from goal (skip common words)
        skip_words = {'the', 'a', 'an', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'over', 'under', 'between', 'among', 'through', 'during', 'before', 'after', 'above', 'below', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall', 'and', 'or', 'but', 'nor', 'so', 'yet', 'as', 'if', 'then', 'than', 'when', 'where', 'while', 'how', 'why', 'what', 'which', 'who', 'whom', 'whose', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'his', 'hers', 'ours', 'theirs', 'myself', 'yourself', 'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves'}
        
        # ALSO skip action/instruction words that shouldn't match menu items
        action_words = {'select', 'choose', 'pick', 'click', 'build', 'your', 'own', 'option', 'as', 'type', 'order', 'get', 'go', 'find', 'then', 'me'}
        
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
        text_lower = text.lower()
        target_matches = sum(1 for kw in target_keywords if kw in text_lower)
        general_matches = sum(1 for kw in general_keywords if kw in text_lower)
        
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
        goal_phrase = goal_lower.replace("add", "").replace("'", "").replace('"', "").replace("as a topping", "").replace("as", "").strip()
        if len(goal_phrase.split()) >= 2 and goal_phrase in text.lower():
            phrase_boost = 5.0  # MASSIVE boost for exact phrase match
            score += phrase_boost
            print(f"🔥 PHRASE MATCH: '{text}' got +{phrase_boost:.1f} for exact phrase '{goal_phrase}'")

        element.score = max(0.0, score)  # Ensure non-negative
    
    # GOAL-AWARE POST-PROCESSING: Apply additional goal-specific boosts and re-sort
    goal_lower = goal.lower()
    print(f"🎯 Goal-aware processing for: '{goal}'")
    
    # Menu selection goals (like "Select 'Bowl'")
    has_select_keyword = any(keyword in goal_lower for keyword in ["select", "choose", "pick"])
    has_food_keyword = any(food_type in goal_lower for food_type in ["bowl", "burrito", "taco", "salad", "quesadilla"])
    print(f"🎯 Has select keyword: {has_select_keyword}, Has food keyword: {has_food_keyword}")
    
    if has_select_keyword and has_food_keyword:
        print(f"🍽️ DETECTED MENU SELECTION GOAL!")
        menu_boosted = 0
        for element in elements:
            text = element.text.lower()
            attrs = element.attrs
            classes = _safe_get_class_string(attrs).lower()
            
            # Extract the specific food item from goal (e.g., "bowl" from "Select 'Bowl'")
            goal_food_items = []
            for food_type in ["bowl", "burrito", "taco", "salad", "quesadilla", "chips", "drink", "kids meal"]:
                if food_type in goal_lower:
                    goal_food_items.append(food_type)
            
            print(f"🍽️ Goal food items: {goal_food_items}")
            
            # MASSIVE boost for exact menu item matches
            for food_item in goal_food_items:
                if food_item in text or f"{food_item}" in text:
                    original_score = element.score
                    element.score = original_score + 6.0  # Massive boost for menu items
                    menu_boosted += 1
                    print(f"🍽️ MENU BOOST: '{element.text}' got +6.0 for '{food_item}' match")
            
            # Additional boost for menu-related classes/attributes
            menu_indicators = ["menu", "top-level-menu", "meal", "item", "card"]
            if any(indicator in classes for indicator in menu_indicators) and any(food_item in text for food_item in goal_food_items):
                element.score += 2.0  # Additional boost for menu containers
                menu_boosted += 1
        
        if menu_boosted > 0:
            print(f"🍽️ Menu goal detected: Boosted {menu_boosted} menu elements")
            # Re-sort after boosting scores
            elements.sort(key=lambda x: x.score, reverse=True)
    
    # Location selection goals
    elif any(keyword in goal_lower for keyword in ["select", "choose", "pick", "nearest"]) and \
         any(keyword in goal_lower for keyword in ["location", "restaurant", "store"]):
        location_boosted = 0
        for element in elements:
            text = element.text.lower()
            attrs = element.attrs
            classes = _safe_get_class_string(attrs).lower()
            
            # PRIORITY 1: Boost location/store container elements (most clickable)
            location_attrs = [
                "data-qa-restaurant-id", "data-store-id", "data-location-id", 
                "data-shop-id", "data-venue-id", "data-place-id"
            ]
            
            has_location_attr = any(attrs.get(attr) for attr in location_attrs)
            has_location_class = any(container_class in classes 
                                   for container_class in ['restaurant-address-item', 'location-item', 
                                                          'store-item', 'store-card', 'location-card', 'venue-item'])
            
            if has_location_attr or has_location_class:
                original_score = element.score
                element.score = original_score + 8.0  # Highest boost for containers
                location_boosted += 1
            
            # PRIORITY 2: Boost location/address elements (for context, but lower than containers)
            elif (element.attrs.get("role") == "definition" and 
                  any(loc_word in text for loc_word in ['near', 'mile', 'mi', 'km', 'street', 'road', 'avenue', 'boulevard', 'drive', 'lane', 'way'])) or \
                 any(loc_class in classes for loc_class in ['address', 'location', 'result', 'store', 'restaurant']) or \
                 any(distance in text for distance in ['mile', 'mi', 'km', 'away']):
                
                original_score = element.score
                element.score = original_score + 4.0  # Lower boost for text elements
                location_boosted += 1
        
        if location_boosted > 0:
            #print(f"🎯 Location goal detected: Boosted {location_boosted} location elements")
            # Re-sort after boosting scores
            elements.sort(key=lambda x: x.score, reverse=True)
    
    # Sort by score (highest first) and limit to max items
    ranked = sorted(elements, key=lambda e: e.score, reverse=True)
    return ranked[:INTERACTIVE_MAX_ITEMS]


async def create_page_context(page, goal: str = "", step_number: int = 1, total_steps: int = 1, 
                            recent_events: List[Dict] = None, lattice_state: Dict = None,
                            previous_dom_signature: str = "") -> PageContext:
    """Enhanced context creation with comprehensive element debugging."""
    
    ########################################################
    # TODO: REMOVE DEBUG LOGGING BEFORE PRODUCTION
    ########################################################
    
    # Take page screenshot for manual verification
    screenshot_path = f"debug_prompts/page_screenshot_step{step_number}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}.png"
    await page.screenshot(path=screenshot_path)
    print(f"🖼️ Page screenshot saved: {screenshot_path}")
    
    # Get ALL input elements on the page
    all_inputs = await page.query_selector_all('input')
    input_debug_path = f"debug_prompts/input_debug_step{step_number}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}.txt"
    
    with open(input_debug_path, 'w', encoding='utf-8') as f:
        f.write(f"INPUT ELEMENT DEBUG - Step {step_number}\n")
        f.write("=" * 50 + "\n")
        f.write(f"Total input elements found: {len(all_inputs)}\n\n")
        
        for i, input_elem in enumerate(all_inputs):
            try:
                # Get all attributes
                tag_name = await input_elem.evaluate('el => el.tagName')
                input_type = await input_elem.get_attribute('type') or 'text'
                name = await input_elem.get_attribute('name') or ''
                placeholder = await input_elem.get_attribute('placeholder') or ''
                class_name = await input_elem.get_attribute('class') or ''
                id_attr = await input_elem.get_attribute('id') or ''
                is_visible = await input_elem.is_visible()
                is_enabled = await input_elem.is_enabled()
                
                f.write(f"Input #{i+1}:\n")
                f.write(f"  Tag: {tag_name}\n")
                f.write(f"  Type: {input_type}\n") 
                f.write(f"  Name: {name}\n")
                f.write(f"  Placeholder: {placeholder}\n")
                f.write(f"  Class: {class_name}\n")
                f.write(f"  ID: {id_attr}\n")
                f.write(f"  Visible: {is_visible}\n")
                f.write(f"  Enabled: {is_enabled}\n")
                f.write("-" * 30 + "\n")
            except Exception as e:
                f.write(f"Input #{i+1}: Error getting details - {e}\n")
    
    print(f"🔍 Input debug saved: {input_debug_path}")
    
    ########################################################
    # END DEBUG LOGGING
    ########################################################

    compressed = compress_dom(await page.content(), goal)
    skeleton = create_dom_skeleton(compressed)
    signature = page_signature(compressed)  # Use compressed DOM for signature
    elements = summarize_interactive_elements(compressed)
    scored_elements = score_interactive_elements(elements, goal)
    
    return PageContext(
        url=await page.evaluate("location.href"),
        title=await page.title(),
        raw_dom=compressed,  # Store compressed version
        skeleton=skeleton,
        signature=signature,
        interactive=scored_elements,
        step_number=step_number,
        total_steps=total_steps,
        overall_goal=goal,
        # Enhanced context fields
        current_step=step_number,
        total_steps_planned=total_steps,
        recent_events=recent_events or [],
        previous_dom_signature=previous_dom_signature,
        dom_signature=signature,  # Alias for consistency
        lattice_state=lattice_state
    )


def create_page_context_sync(url: str, title: str, raw_dom: str, goal: str = "", 
                           step_number: int = 1, total_steps: int = 1, 
                           overall_goal: str = "", recent_events: List[Dict] = None,
                           previous_signature: str = "", lattice_state: Dict = None) -> PageContext:
    """
    Synchronous wrapper for create_page_context that matches the old calling signature.
    This processes raw DOM text instead of requiring a page object.
    """
    from datetime import datetime
    
    ########################################################
    # TODO: REMOVE DEBUG LOGGING BEFORE PRODUCTION
    ########################################################
    
    print(f"🔍 DOM DEBUG: Starting page context creation for URL: {url[:100]}...")
    print(f"🔍 DOM DEBUG: Goal: {goal}")
    print(f"🔍 DOM DEBUG: Raw DOM length: {len(raw_dom)} characters")
    
    # Process DOM to find interactive elements
    compressed = compress_dom(raw_dom, goal)
    signature = page_signature(raw_dom)
    skeleton = create_dom_skeleton(compressed)
    elements = summarize_interactive_elements(raw_dom)
    scored_elements = score_interactive_elements(elements, goal)
    
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
    debug_file = f"debug_prompts/dom_debug_step{step_number}_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')[:-3]}.txt"
    with open(debug_file, 'w', encoding='utf-8') as f:
        f.write(f"DOM Debug Report - Step {step_number}\n")
        f.write(f"={'='*50}\n\n")
        f.write(f"URL: {url}\n")
        f.write(f"Goal: {goal}\n")
        f.write(f"Raw DOM Length: {len(raw_dom)} chars\n\n")
        
        f.write(f"All Interactive Elements ({len(scored_elements)}):\n")
        f.write("-" * 30 + "\n")
        for i, elem in enumerate(scored_elements):
            f.write(f"{i+1:3d}. <{elem.tag}> {elem.attrs} text='{elem.text[:100]}'\n")
        
        f.write(f"\nInput/Textarea Elements ({len(input_elements)}):\n")
        f.write("-" * 30 + "\n")
        for i, elem in enumerate(input_elements):
            f.write(f"{i+1:3d}. <{elem.tag}> {elem.attrs} text='{elem.text[:100]}'\n")
        
        f.write(f"\nScored Elements ({len(scored_elements)}):\n")
        f.write("-" * 30 + "\n")
        for i, elem in enumerate(scored_elements):
            score = getattr(elem, 'score', 'N/A')
            f.write(f"{i+1:3d}. <{elem.tag}> score={score} {elem.attrs} text='{elem.text[:100]}'\n")
    
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
