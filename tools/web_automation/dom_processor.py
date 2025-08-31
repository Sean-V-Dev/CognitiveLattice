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


def _norm_text(t: str) -> str:
    """Normalize text for processing."""
    t = re.sub(r"\s+", " ", (t or "")).strip()
    return t[:INTERACTIVE_INCLUDE_TEXT_MAX]


def _extract_attrs(attr_str: str) -> Dict[str, str]:
    """Simple attribute parser; resilient to odd markup."""
    attrs = {}
    for m in re.finditer(r'(\w[\w:-]*)\s*=\s*"([^"]*)"', attr_str or ""):
        attrs[m.group(1).lower()] = m.group(2)
    for m in re.finditer(r"(\w[\w:-]*)\s*=\s*'([^']*)'", attr_str or ""):
        attrs[m.group(1).lower()] = m.group(2)
    return attrs


def _candidate_selectors(tag: str, attrs: Dict[str, str], text: str) -> List[str]:
    """Generate candidate selectors for an element, with primary selector first."""
    
    def esc(v: str, lim: int = 24) -> str:
        """Escape and limit text for safe selector usage."""
        v = (v or "")[:lim].replace('"', r'\"')
        return v
    
    sels = []
    if attrs.get("id"):
        sels.append(f"#{attrs['id']}")
    classes = _safe_get_class_string(attrs).strip()
    if classes:
        # take up to first two classes to keep selectors short
        cls = ".".join(c for c in classes.split()[:2])
        if cls:
            sels.append(f"{tag}.{cls}")
    role = attrs.get("role")
    if role:
        sels.append(f"[role=\"{esc(role, 32)}\"]")
        if text:
            sels.append(f"[role=\"{esc(role, 32)}\"]:has-text(\"{esc(text, 48)}\")")
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
    # Priority 1: Location/store containers with identifying attributes
    location_attrs = [
        "data-qa-restaurant-id", "data-store-id", "data-location-id", 
        "data-shop-id", "data-venue-id", "data-place-id"
    ]
    if any(attrs.get(attr) for attr in location_attrs):
        return True
        
    # Priority 2: Check for explicit click indicators
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
    
    # Strong indicators this is a navigation/location element
    navigation_keywords = [
        "find", "locate", "location", "store", "shop", "order", 
        "menu", "navigation", "nav", "click", "button", "link"
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


def summarize_interactive_elements(html: str, max_items: int = INTERACTIVE_MAX_ITEMS) -> List[Element]:
    """Extract interactive elements from HTML."""
    # Traditional interactive elements (a, button, input, select)
    pattern = re.compile(r"<\s*(a|button|input|select)\b([^>]*)>(.*?)</\s*\1\s*>", re.I | re.S)
    self_closing = re.compile(r"<\s*(input)\b([^>]*)/?>", re.I)  # Only input is self-closing
    
    # Interactive DIVs and SPANs with click handlers, roles, or navigation keywords
    interactive_div_pattern = re.compile(r"<\s*(div|span)\b([^>]*)>(.*?)</\s*\1\s*>", re.I | re.S)
    
    elements: List[Element] = []

    # 1) Capture traditional interactive elements
    for m in pattern.finditer(html or ""):
        tag = m.group(1).lower()
        attrs = _extract_attrs(m.group(2))
        text = _norm_text(re.sub(r"<[^>]+>", " ", m.group(3)))
        selectors = _candidate_selectors(tag, attrs, text)
        
        elements.append(Element(
            tag=tag,
            text=text,
            attrs={k: attrs.get(k, "") for k in ["id","class","name","role","aria-label","placeholder","href","onclick","data-testid","tabindex"]},
            selectors=selectors
        ))

    # 2) Capture self-closing elements
    for m in self_closing.finditer(html or ""):
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
    for m in interactive_div_pattern.finditer(html or ""):
        tag = m.group(1).lower()
        attrs = _extract_attrs(m.group(2))
        text = _norm_text(re.sub(r"<[^>]+>", " ", m.group(3)))
        
        if is_clickable_div(attrs, text):
            selectors = _candidate_selectors(tag, attrs, text)
            elements.append(Element(
                tag=tag,
                text=text,
                attrs={k: attrs.get(k, "") for k in ["id","class","name","role","aria-label","onclick","data-testid","tabindex"]},
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
                score += 0.8
        
        # Extra boost for primary action indicators
        primary_actions = ["order now", "buy now", "get started", "begin", "add to cart", "checkout", "start", "shop now"]
        for action in primary_actions:
            if action in all_text: 
                score += 1.2
        
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

        element.score = max(0.0, score)  # Ensure non-negative
    
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
        
        f.write(f"All Interactive Elements ({len(elements)}):\n")
        f.write("-" * 30 + "\n")
        for i, elem in enumerate(elements):
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
