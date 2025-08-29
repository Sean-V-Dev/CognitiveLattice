import json
import os
import re
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from pathlib import Path

# Import the new DOM skeleton utility
from utils.dom_skeleton import create_dom_skeleton, extract_clickable_elements, get_skeleton_stats

# Placeholder: integrate your existing LLM client (e.g., diagnose_user_intent or new function)
try:
    from core.llama_client import diagnose_user_intent  # Fallback for when external API not available
except ImportError:
    diagnose_user_intent = None

# Config knobs (env-overridable)
DOM_MAX_CHARS = int(os.getenv("WEB_AGENT_DOM_MAX_CHARS", "1500"))
INTERACTIVE_MAX_ITEMS = int(os.getenv("WEB_AGENT_INTERACTIVE_MAX_ITEMS", "100"))  # Increased from 60
INTERACTIVE_INCLUDE_TEXT_MAX = int(os.getenv("WEB_AGENT_INTERACTIVE_INCLUDE_TEXT_MAX", "80"))

KEYWORD_BOOST = [
    "order", "buy", "shop", "start", "begin", "find", "location", "search", "submit",
    "accept", "agree", "continue", "next", "add", "cart", "checkout", "zip", "address",
]

INTERACTIVE_TAGS = {"a", "button", "input", "select"}
INTERACTIVE_ROLES = {"button", "link", "dialog", "combobox", "textbox", "menuitem", "definition"}

MAX_DOM_CHARS = 18000
MAX_DOM_CHARS_LOCATION = 35000  # Higher limit for location selection steps

def _safe_get_class_string(attrs: Dict[str, Any]) -> str:
    """Safely get class attribute as string, handling AttributeValueList objects"""
    class_value = attrs.get('class', '')
    if hasattr(class_value, '__iter__') and not isinstance(class_value, str):
        # Handle AttributeValueList or other iterable types
        return ' '.join(str(cls) for cls in class_value)
    return str(class_value)

def compress_dom(raw_dom: str, goal: str = "") -> str:
    # Use higher limit for location selection steps
    goal_lower = goal.lower()
    if any(keyword in goal_lower for keyword in ['select', 'choose', 'pick', 'nearest']) and \
       any(keyword in goal_lower for keyword in ['location', 'restaurant', 'store']):
        max_chars = MAX_DOM_CHARS_LOCATION
        print(f"🎯 Using extended DOM limit ({max_chars}) for location selection")
    else:
        max_chars = MAX_DOM_CHARS
    
    # Strip scripts/styles and collapse whitespace
    cleaned = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", raw_dom, flags=re.DOTALL|re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned)
    return cleaned[:max_chars]

def hash_dom(dom: str) -> str:
    return hashlib.sha256(dom.encode("utf-8")).hexdigest()[:16]

def _norm_text(t: str) -> str:
    t = re.sub(r"\s+", " ", (t or "")).strip()
    return t[:INTERACTIVE_INCLUDE_TEXT_MAX]

def _extract_attrs(attr_str: str) -> Dict[str, str]:
    # Simple attribute parser; resilient to odd markup
    attrs = {}
    for m in re.finditer(r'(\w[\w:-]*)\s*=\s*"([^"]*)"', attr_str or ""):
        attrs[m.group(1).lower()] = m.group(2)
    for m in re.finditer(r"(\w[\w:-]*)\s*=\s*'([^']*)'", attr_str or ""):
        attrs[m.group(1).lower()] = m.group(2)
    return attrs

def _candidate_selectors(tag: str, attrs: Dict[str, str], text: str) -> List[str]:
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
        sels.append(f"[role='{role}']")
        if text:
            sels.append(f"[role='{role}']:has-text('{text}')")
    aria = attrs.get("aria-label")
    if aria:
        sels.append(f"[aria-label*='{aria[:24]}']")
    name = attrs.get("name")
    if name:
        sels.append(f"{tag}[name*='{name[:24]}']")
    placeholder = attrs.get("placeholder")
    if placeholder:
        sels.append(f"{tag}[placeholder*='{placeholder[:24]}']")
    href = attrs.get("href")
    if href and tag == "a":
        sels.append(f"a[href*='{href[:32]}']")
    if text:
        sels.append(f"{tag}:has-text('{text}')")
    # de-dupe while preserving order
    seen = set(); uniq = []
    for s in sels:
        if s not in seen:
            seen.add(s); uniq.append(s)
    return uniq[:5]

def summarize_interactive_elements(html: str, max_items: int = INTERACTIVE_MAX_ITEMS) -> List[Dict[str, Any]]:
    # Enhanced extraction: BOTH traditional interactive elements AND clickable divs
    
    # 1) Traditional interactive elements (a, button, input, select)
    pattern = re.compile(r"<\s*(a|button|input|select)\b([^>]*)>(.*?)</\s*\1\s*>", re.I | re.S)
    self_closing = re.compile(r"<\s*(input|select)\b([^>]*)/?>", re.I)
    
    # 2) NEW: Interactive DIVs and SPANs with click handlers, roles, or navigation keywords
    interactive_div_pattern = re.compile(r"<\s*(div|span)\b([^>]*)>(.*?)</\s*\1\s*>", re.I | re.S)
    
    items: List[Dict[str, Any]] = []

    def is_clickable_div(attrs: Dict[str, str], text: str) -> bool:
        """Determine if a div/span is likely clickable based on attributes and content"""
        # Priority 1: Location/store containers with identifying attributes
        location_attrs = [
            "data-qa-restaurant-id",  # Restaurant chains
            "data-store-id",          # Common pattern
            "data-location-id",       # Common pattern  
            "data-shop-id",           # Common pattern
            "data-venue-id",          # Common pattern
            "data-place-id"           # Common pattern
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

    def score_item(tag: str, attrs: Dict[str, str], text: str) -> float:
        s = 0.0
        t = (text or "").lower()
        roles = (attrs.get("role") or "").lower()
        ph = (attrs.get("placeholder") or "").lower()
        aria = (attrs.get("aria-label") or "").lower()
        nm = (attrs.get("name") or "").lower()
        href = (attrs.get("href") or "").lower()
        classes = _safe_get_class_string(attrs).lower()
        input_type = (attrs.get("type") or "").lower()

        # base for interactive tag/role
        if tag in INTERACTIVE_TAGS: s += 1.0
        if roles in INTERACTIVE_ROLES: s += 0.5

        # HUGE boost for location finder elements
        location_finder_phrases = ["find location", "find store", "store locator", "find a store", "find locations"]
        for phrase in location_finder_phrases:
            if phrase in t or phrase in classes:
                s += 3.0  # MASSIVE boost for location finder
                
        # Extra boost for generic location finder patterns
        if ("find" in t and ("store" in t or "location" in t or "restaurant" in t or "shop" in t)):
            s += 2.5  # High boost for "find [location type]" patterns
                
        # Enhanced keyword boosts for web automation
        blk = " ".join([t, ph, aria, nm, href, classes])
        for kw in KEYWORD_BOOST:
            if kw in blk: s += 0.8  # Increased from 0.6
        
        # Extra boost for primary action indicators
        primary_actions = ["order now", "buy now", "get started", "begin", "add to cart", "checkout", "start", "shop now"]
        for action in primary_actions:
            if action in blk: s += 1.2
        
        # Modal dismissal keywords
        modal_keywords = ["accept", "agree", "continue", "close", "got it", "dismiss", "ok"]
        for mk in modal_keywords:
            if mk in blk: s += 0.7

        # ENHANCED: Strongly prioritize input fields for location/ZIP entry
        if tag == "input":
            s += 0.5  # Base boost for inputs
            
            # Big boost for location/ZIP input fields
            location_input_keywords = ["zip", "postal", "address", "location", "city", "state"]
            for lk in location_input_keywords:
                if lk in ph or lk in aria or lk in nm:
                    s += 2.0  # MAJOR boost for location inputs
                    
            # Boost for text inputs (where you can type)
            if input_type in ["text", "search", "tel", ""]:
                s += 0.8
                
        # Enhanced scoring for interactive divs/spans
        if tag in ["div", "span"]:
            if is_clickable_div(attrs, text):
                s += 1.2  # Good boost for clickable divs
                
        # Location-related keywords for buttons/links
        location_keywords = ["find location", "store locator", "enter zip"]
        for lk in location_keywords:
            if lk in blk: s += 1.5  # Good boost but less than input fields

        # PENALTY: Reduce score for "all locations" type links 
        if "all" in t and "location" in t:
            s -= 1.0  # Penalty for "all locations" links
            
        # PENALTY: Reduce score for "view all" type links
        if "view" in t and ("all" in t or "more" in t):
            s -= 0.8

        # Penalty for generic or problematic elements
        if "javascript:" in href: s -= 0.5
        if tag == "a" and not href: s -= 0.3
        if len(t) > 100: s -= 0.2  # Very long text might be noisy

        # Boost for meaningful text
        if 3 <= len(t) <= 50: s += 0.3
        elif len(t) > 50: s += 0.1

        # Boost for specific attributes that indicate interactivity
        if attrs.get("onclick"): s += 0.4
        if attrs.get("data-testid"): s += 0.3
        if "btn" in classes or "button" in classes: s += 0.5

        return max(0.0, s)  # Ensure non-negative

    # 1) Capture traditional interactive elements (paired tags with inner text)
    for m in pattern.finditer(html or ""):
        tag = m.group(1).lower()
        attrs = _extract_attrs(m.group(2))
        text = _norm_text(re.sub(r"<[^>]+>", " ", m.group(3)))
        items.append({
            "tag": tag,
            "text": text,
            "attrs": {k: attrs.get(k, "") for k in ["id","class","name","role","aria-label","placeholder","href","onclick","data-testid","tabindex"]},
        })

    # 2) NEW: Capture interactive divs and spans
    
    # Special handling for location/store containers first (they need special regex due to nesting)
    location_attr_patterns = [
        "data-qa-restaurant-id",  # Restaurant chains
        "data-store-id",          # Common pattern
        "data-location-id",       # Common pattern  
        "data-shop-id",           # Common pattern
        "data-venue-id",          # Common pattern
        "data-place-id"           # Common pattern
    ]
    
    for attr_pattern in location_attr_patterns:
        location_pattern = re.compile(rf"<\s*div\b([^>]*{attr_pattern}[^>]*)>(.*?(?=<div[^>]*{attr_pattern}|$))", re.I | re.S)
        for m in location_pattern.finditer(html or ""):
            attrs = _extract_attrs(m.group(1))
            if attrs.get(attr_pattern):  # Only include if it actually has the ID
                text = _norm_text(re.sub(r"<[^>]+>", " ", m.group(2)))
                items.append({
                    "tag": "div",
                    "text": text,
                    "attrs": {k: attrs.get(k, "") for k in ["id","class","name","role","aria-label","onclick","data-testid","tabindex","data-v-*"] + location_attr_patterns},
                })

    # General interactive divs and spans (non-location containers)
    for m in interactive_div_pattern.finditer(html or ""):
        tag = m.group(1).lower()
        attrs = _extract_attrs(m.group(2))
        
        # Skip if this is a location container (already handled above)
        if any(attrs.get(attr) for attr in location_attr_patterns):
            continue
            
        text = _norm_text(re.sub(r"<[^>]+>", " ", m.group(3)))
        
        # Only include if it looks clickable
        if is_clickable_div(attrs, text):
            items.append({
                "tag": tag,
                "text": text,
                "attrs": {k: attrs.get(k, "") for k in ["id","class","name","role","aria-label","onclick","data-testid","tabindex","data-v-*"] + location_attr_patterns},
            })

    # capture self-closing or input without closing tags
    for m in self_closing.finditer(html or ""):
        tag = m.group(1).lower()
        attrs = _extract_attrs(m.group(2))
        items.append({
            "tag": tag,
            "text": "",
            "attrs": {k: attrs.get(k, "") for k in ["id","class","name","role","aria-label","placeholder","href","type"]},
        })

    # rank and decorate
    for it in items:
        it["score"] = score_item(it["tag"], it["attrs"], it.get("text",""))
        it["selectors"] = _candidate_selectors(it["tag"], it["attrs"], it.get("text",""))

    # Sort by score (highest first) and take top items
    items.sort(key=lambda x: x["score"], reverse=True)
    return items[:max_items]

def build_reasoning_prompt(goal: str, context: Dict[str, Any]) -> str:
    compressed = context.get("compressed_dom", "")
    interactive = context.get("interactive_summary", [])
    
    # DEBUG: Save the actual skeleton being sent to API with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save DOM skeleton to text file
    skeleton_file = f"debug_skeleton_sent_to_api_{timestamp}.txt"
    with open(skeleton_file, "w", encoding="utf-8") as f:
        f.write(f"DOM SKELETON SENT TO API at {datetime.now()}\n")
        f.write(f"Goal: {goal}\n")
        f.write(f"Skeleton length: {len(compressed)} characters\n")
        f.write("=" * 80 + "\n")
        f.write(compressed)
    
    # Save interactive elements to text file
    interactive_file = f"debug_interactive_sent_to_api_{timestamp}.txt"
    with open(interactive_file, "w", encoding="utf-8") as f:
        f.write(f"INTERACTIVE ELEMENTS SENT TO API at {datetime.now()}\n")
        f.write(f"Goal: {goal}\n")
        f.write(f"Number of interactive elements: {len(interactive)}\n")
        f.write("=" * 80 + "\n")
        for i, elem in enumerate(interactive, 1):
            f.write(f"{i}. {elem}\n")
    
    print(f"🔍 DEBUG: Saved skeleton ({len(compressed)} chars) to {skeleton_file}")
    print(f"🔍 DEBUG: Saved {len(interactive)} interactive elements to {interactive_file}")
    
    # GOAL-AWARE SCORING: Boost location elements for selection goals
    if any(keyword in goal.lower() for keyword in ["select", "choose", "nearest", "location"]):
        location_boosted = 0
        for elem in interactive:
            text = elem.get('text', '').lower()
            role = elem.get('attrs', {}).get('role', '').lower()
            attrs = elem.get('attrs', {})
            
            # PRIORITY 1: Boost location/store container elements (most clickable)
            location_attrs = [
                "data-qa-restaurant-id",  # Restaurant chains
                "data-store-id",          # Common pattern
                "data-location-id",       # Common pattern  
                "data-shop-id",           # Common pattern
                "data-venue-id",          # Common pattern
                "data-place-id"           # Common pattern
            ]
            
            has_location_attr = any(attrs.get(attr) for attr in location_attrs)
            has_location_class = any(container_class in _safe_get_class_string(attrs).lower() 
                                   for container_class in ['restaurant-address-item', 'location-item', 'store-item', 'store-card', 'location-card', 'venue-item'])
            
            if has_location_attr or has_location_class:
                original_score = elem.get('score', 0)
                elem['score'] = original_score + 8.0  # Highest boost for containers
                location_boosted += 1
                location_id = next((attrs.get(attr) for attr in location_attrs if attrs.get(attr)), 'class-based')
                print(f"🎯 Boosted location container: {location_id}")
            
            # PRIORITY 2: Boost location/address elements (for context, but lower than containers)
            elif (role == 'definition' and any(loc_word in text for loc_word in ['near', 'mile', 'mi', 'km', 'street', 'road', 'avenue', 'boulevard', 'drive', 'lane', 'way'])) or \
                 any(loc_class in _safe_get_class_string(attrs).lower() for loc_class in ['address', 'location', 'result', 'store', 'restaurant']) or \
                 any(distance in text for distance in ['mile', 'mi', 'km', 'away']):
                
                original_score = elem.get('score', 0)
                elem['score'] = original_score + 4.0  # Lower boost for text elements
                location_boosted += 1
        
        if location_boosted > 0:
            print(f"🎯 Goal-aware scoring: Boosted {location_boosted} location elements for selection goal")
            # Re-sort after boosting scores
            interactive.sort(key=lambda x: x.get('score', 0), reverse=True)
    
    url = context.get('url', '')
    title = context.get('title', '')
    raw_dom = context.get('raw_dom', '') or context.get('dom', '')
    dom_change_info = context.get('dom_change_history', '')

    # Create DOM skeleton from raw HTML
    if raw_dom:
        print("🏗️ Creating DOM skeleton from raw HTML...")
        dom_skeleton = create_dom_skeleton(raw_dom, max_depth=12)
        skeleton_stats = get_skeleton_stats(dom_skeleton)
        interactive_elements = extract_clickable_elements(dom_skeleton)
        
        print(f"📊 DOM Skeleton Stats: {skeleton_stats['estimated_tokens']} tokens, {len(interactive_elements)} interactive elements")
        
        # Apply goal-aware scoring to the final interactive elements (moved from above)
        if any(keyword in goal.lower() for keyword in ["select", "choose", "nearest", "location"]):
            location_boosted = 0
            for elem in interactive_elements:
                text = elem.get('text', '').lower()
                role = elem.get('attrs', {}).get('role', '').lower()
                attrs = elem.get('attrs', {})
                
                # PRIORITY 1: Boost location/store container elements (most clickable)
                location_attrs = [
                    "data-qa-restaurant-id",  # Restaurant chains
                    "data-store-id",          # Common pattern
                    "data-location-id",       # Common pattern  
                    "data-shop-id",           # Common pattern
                    "data-venue-id",          # Common pattern
                    "data-place-id"           # Common pattern
                ]
                
                has_location_attr = any(attrs.get(attr) for attr in location_attrs)
                has_location_class = any(container_class in _safe_get_class_string(attrs).lower() 
                                       for container_class in ['restaurant-address-item', 'location-item', 'store-item', 'store-card', 'location-card', 'venue-item'])
                
                if has_location_attr or has_location_class:
                    original_score = elem.get('score', 0)
                    elem['score'] = original_score + 8.0  # Highest boost for containers
                    location_boosted += 1
                    location_id = next((attrs.get(attr) for attr in location_attrs if attrs.get(attr)), 'class-based')
                    print(f"🎯 Final boost applied to location container: {location_id}")
                
                # PRIORITY 2: Boost location/address elements (for context, but lower than containers)
                elif (role == 'definition' and any(loc_word in text for loc_word in ['near', 'mile', 'mi', 'km', 'street', 'road', 'avenue', 'boulevard', 'drive', 'lane', 'way'])) or \
                     any(loc_class in _safe_get_class_string(attrs).lower() for loc_class in ['address', 'location', 'result', 'store', 'restaurant']) or \
                     any(distance in text for distance in ['mile', 'mi', 'km', 'away']):
                    
                    original_score = elem.get('score', 0)
                    elem['score'] = original_score + 4.0  # Lower boost for text elements
                    location_boosted += 1
            
            if location_boosted > 0:
                print(f"🎯 Final goal-aware scoring: Boosted {location_boosted} location elements for selection goal")
                # Re-sort after boosting scores
                interactive_elements.sort(key=lambda x: x.get('score', 0), reverse=True)
        
    else:
        # Fallback to old method if no raw DOM available
        print("⚠️ No raw DOM available, using fallback method...")
        compressed = context.get('compressed_dom', '') or ''
        dom_skeleton = compressed[:DOM_MAX_CHARS]
        interactive_elements = context.get('interactive_summary', [])
        if not interactive_elements and compressed:
            interactive_elements = summarize_interactive_elements(compressed)

    # Enhanced semantic memory integration
    semantic_memory = context.get('semantic_memory', {})
    domain_memory = context.get('domain_memory', {})
    
    # Build the enhanced prompt with DOM skeleton
    prompt_parts = [
        "You are an AI web automation agent. Your task is to analyze the current page and choose the best action to achieve the goal.",
        "",
        f"🎯 GOAL: {goal}",
        f"🌐 URL: {url}",
        f"📄 Page Title: {title}",
        ""
    ]

    # Extract ZIP code from goal if present for type actions
    zip_code_match = re.search(r"ZIP code '(\d{5})'|zip code (\d{5})|ZIP (\d{5})", goal, re.IGNORECASE)
    
    # Also check execution plan context for ZIP code
    execution_context = context.get('execution_plan_context', {})
    plan_zip_code = execution_context.get('extracted_zip_code')
    
    # Use ZIP code from context if not found in goal text
    zip_code = None
    if zip_code_match:
        zip_code = zip_code_match.group(1) or zip_code_match.group(2) or zip_code_match.group(3)
    elif plan_zip_code:
        zip_code = plan_zip_code
    
    if zip_code:
        prompt_parts.extend([
            f"🔑 SPECIFIC DATA TO ENTER: {zip_code}",
            f"⚠️  IMPORTANT: If you need to type into an input field for this goal, type '{zip_code}' NOT placeholder text.",
            ""
        ])
    
    # Add execution plan context if available
    if execution_context:
        prompt_parts.extend([
            f"📋 EXECUTION CONTEXT:",
            f"   Overall Goal: {execution_context.get('overall_goal', 'N/A')}",
            f"   Current Step: {execution_context.get('current_step', 'N/A')} of {execution_context.get('total_steps', 'N/A')}",
            f"   Step Goal: {execution_context.get('step_goal', 'N/A')}",
            ""
        ])

    # Add cognitive lattice context for epistemic self-awareness
    lattice_context = context.get('lattice_context', {})
    if lattice_context:
        prompt_parts.extend([
            "🧠 YOUR COGNITIVE LATTICE (Epistemic History):",
            "This is your memory of actions taken and progress made toward this goal:",
            ""
        ])
        
        # Show recent action history with outcomes
        recent_actions = lattice_context.get('recent_actions', [])
        if recent_actions:
            prompt_parts.append("📚 Recent Actions & Outcomes:")
            for action in recent_actions[-5:]:  # Last 5 actions
                step_desc = action.get('step_description', 'Unknown step')
                achieved = action.get('action_result', {}).get('achieved', False)
                reason = action.get('action_result', {}).get('reason', 'No reason provided')
                status = "✅ SUCCESS" if achieved else "❌ FAILED"
                prompt_parts.append(f"   • {step_desc}: {status} - {reason}")
            prompt_parts.append("")
        
        # Show current progress state
        session_context = lattice_context.get('session_context', {})
        if session_context:
            prompt_parts.extend([
                "📊 Current Progress State:",
                f"   • Overall Goal: {session_context.get('goal', 'N/A')}",
                f"   • Task Status: {session_context.get('status', 'N/A')}",
                f"   • Total Planned Steps: {session_context.get('total_steps', 'N/A')}",
                f"   • Steps Completed: {session_context.get('completed_steps', 'N/A')}",
                f"   • Total Actions Taken: {len(recent_actions)}",
                f"   • Success Rate: {lattice_context.get('success_rate', 'N/A')}",
                ""
            ])
        
        # Show learning patterns and insights
        insights = lattice_context.get('insights', [])
        if insights:
            prompt_parts.extend([
                "💡 Learning Insights from Your History:",
                *[f"   • {insight}" for insight in insights[-3:]],  # Last 3 insights
                ""
            ])
        
        prompt_parts.extend([
            "🎯 IMPORTANT: Use this lattice history to inform your decisions:",
            "   • Learn from previous failures to avoid repeating mistakes",
            "   • Build on successful patterns you've established",
            "   • Consider the broader context of your goal progression",
            "   • ASSESS IF CURRENT STEP IS ALREADY DONE: Check if your lattice shows this step's goal has already been accomplished",
            "   • If the current step goal appears completed in your history, you may be able to proceed with a minimal action or skip to the next logical action",
            "   • SMART STEP ASSESSMENT: Compare your current step goal with your recent successful actions to avoid redundant work",
            ""
        ])
        
        # Add explicit current step context if available from execution plan
        if execution_context:
            current_step_goal = execution_context.get('step_goal', '')
            current_step_num = execution_context.get('current_step', 'N/A')
            
            if current_step_goal:
                prompt_parts.extend([
                    f"🔍 CURRENT STEP ANALYSIS:",
                    f"   • You are working on step {current_step_num}: '{current_step_goal}'",
                    f"   • Review your lattice above - has this specific goal already been achieved?",
                    f"   • If yes, consider what minimal action might complete this step or move forward",
                    f"   • If no, proceed with the necessary actions to accomplish this step goal",
                    ""
                ])
        

    # Add DOM change context if available
    if dom_change_info:
        prompt_parts.extend([
            "📈 Recent DOM Changes:",
            dom_change_info,
            ""
        ])

    # Add semantic memory insights
    if domain_memory:
        memory_insights = []
        fingerprints = domain_memory.get('element_fingerprints', [])
        if fingerprints:
            # Show recent successful interactions for this domain
            recent_successes = fingerprints[-3:]  # Last 3 successful interactions
            memory_insights.append("🧠 Recent successful interactions on this domain:")
            for fp in recent_successes:
                goal_context = fp.get('goal_context', 'unknown')[:50]
                semantic_label = fp.get('semantic_label', 'unknown')
                confidence = fp.get('confidence', 0)
                memory_insights.append(f"  • {semantic_label} (confidence: {confidence:.1f}) - Goal: '{goal_context}'")
            memory_insights.append("")
        
        if memory_insights:
            prompt_parts.extend(memory_insights)

    # Add the clean DOM skeleton
    if dom_skeleton:
        prompt_parts.extend([
            "🏗️ PAGE STRUCTURE (DOM Skeleton):",
            "The following is a cleaned view of the page structure with all scripts, styles, and noise removed:",
            "",
            dom_skeleton,
            "",
        ])

    # Format ALL interactive elements - NO FILTERING OR RANKING
    if interactive_elements:
        prompt_parts.extend([
            "🖱️ ALL INTERACTIVE ELEMENTS:",
            f"Found {len(interactive_elements)} interactive elements on the page:",
            ""
        ])
        
        for i, elem in enumerate(interactive_elements, 1):
            tag = elem.get('tag', 'unknown')
            selector = elem.get('selector', 'unknown')
            text = elem.get('text', '').strip()
            attrs = elem.get('attrs', {})
            
            # Build a rich description of each element
            desc_parts = [f"{i}. {tag.upper()}: {selector}"]
            
            if text:
                desc_parts.append(f"Text: '{text[:60]}{'...' if len(text) > 60 else ''}'")
            
            # Show key attributes that help with decision making
            attr_descriptions = []
            if attrs.get('placeholder'):
                attr_descriptions.append(f"placeholder='{attrs['placeholder']}'")
            if attrs.get('aria-label'):
                attr_descriptions.append(f"aria-label='{attrs['aria-label']}'")
            if attrs.get('type'):
                attr_descriptions.append(f"type='{attrs['type']}'")
            if attrs.get('id'):
                attr_descriptions.append(f"id='{attrs['id']}'")
            if attrs.get('class'):
                # Show first few classes
                classes = _safe_get_class_string(attrs)[:100]
                attr_descriptions.append(f"class='{classes}'")
            
            if attr_descriptions:
                desc_parts.append(f"Attributes: {', '.join(attr_descriptions)}")
            
            prompt_parts.append(" | ".join(desc_parts))
        
        prompt_parts.append("")

    # Add decision guidance
    guidance_parts = [
        "🤖 INSTRUCTIONS:",
        "1. Analyze the goal and current page state carefully",
        "2. Look for elements that match the goal's intent (buttons, links, inputs, etc.)",
        "3. Consider element text, classes, IDs, and attributes to find the most relevant match",
        "4. For location/store finder goals, look for elements with 'find', 'location', 'store' text or classes",
        "5. For form inputs, match the input type and placeholder to the data needed",
        "6. Choose the single best element that will progress toward the goal",
    ]
    
    # Add location-specific guidance
    if any(keyword in goal.lower() for keyword in ["select", "choose", "nearest", "location"]):
        guidance_parts.extend([
            "",
            "📍 LOCATION SELECTION GUIDANCE:",
            "• If you see store addresses, location names, or 'Near [street names]' - CLICK them to select",
            "• Look for elements with role='definition' that contain address information",
            "• Distance indicators like 'miles', 'mi', 'km' often indicate clickable locations",
            "• When selecting 'nearest' location: Choose the FIRST address in the list (usually sorted by distance)",
            "• Location lists are typically ordered by proximity - first = closest",
            "• Your job is to actively SELECT a location, not just enter search terms",
            "• Prioritize clicking actual address/location elements over search inputs"
        ])
    
    # Add specific ZIP code instruction if detected
    if zip_code:
        guidance_parts.extend([
            "",
            f"🚨 CRITICAL: For this goal, you must type '{zip_code}' into the input field.",
            f"🚨 DO NOT type placeholder text like 'Enter your address' or 'ZIP code'.",
            f"🚨 Type the actual ZIP code: '{zip_code}'"
        ])
    
    guidance_parts.extend([
        "",
        "Respond with JSON in this format:",
        '{"reasoning": "why you chose this element", "actions": [{"type": "click|type|select", "selector": "css_selector", "text": "text_to_enter"}], "confidence": 0.8}',
        "",
        "The 'selector' must exactly match one of the selectors listed above.",
        "For 'type' actions, include the 'text' field with what to enter.",
        "The 'actions' array should contain exactly one action.",
        "Set 'confidence' between 0.0 and 1.0 based on how certain you are.",
        "Focus on progressing toward the goal efficiently."
    ])
    
    prompt_parts.extend(guidance_parts)

    return "\n".join(prompt_parts)
    
    memory_guidance = ""
    if domain_memory.get('element_fingerprints'):
        memory_guidance = f"""
💾 PREVIOUS SUCCESSFUL INTERACTIONS on this domain:
"""
        for fp in domain_memory['element_fingerprints'][-3:]:  # Last 3 successful patterns
            memory_guidance += f"- Goal: '{fp.get('goal_context', '')}' → Used: {fp.get('selectors', ['unknown'])[0]}\n"
    
    # Add navigation detection
    navigation_guidance = ""
    if url in ["about:blank", ""] and ("navigate to" in goal.lower() or "load" in goal.lower()):
        navigation_guidance = """
🚨 NAVIGATION REQUIRED: Current page is blank. For navigation goals, use:
{"type": "navigate", "url": "https://full-url-here"}
DO NOT use click actions for initial navigation from blank pages.
"""

    return f"""You are an expert web automation agent. Analyze ALL available elements and choose the best action for the goal.

GOAL: {goal}
Current URL: {url}
Current Title: {title}

{navigation_guidance}

ALL INTERACTIVE ELEMENTS (complete list - choose the most appropriate):
{chr(10).join(inter_lines) if inter_lines else '(no interactive elements found)'}

{memory_guidance}

{dom_change_info}

ELEMENT SELECTION GUIDANCE:
- For e-commerce/ordering: Look for buttons like "Order Now", "Buy Now", "Add to Cart", "Checkout"
- For location entry: Prioritize INPUT fields with placeholders like "ZIP", "Address", "Location" over buttons
- For modal dismissal: Look for "Accept", "Close", "Continue", "OK" buttons  
- Ignore elements that don't relate to your goal (ads, footers, unrelated navigation)
- Consider element context - INPUT fields are better for entering data than buttons
- If multiple similar elements exist, choose the most specific one

COMPRESSED DOM CONTEXT (for additional reference):
{truncated}

Respond with JSON containing your reasoning and chosen action:
{{
    "reasoning": "Detailed explanation of why you chose this element over others",
    "confidence": 0.0-1.0,
    "actions": [
        {{"type": "navigate|click|type", "selector": "exact-css-selector", "url": "https://...", "text": "input-text"}}
    ]
}}"""

def llm_reason(goal: str, obs: Dict[str, Any], external_client=None) -> Dict[str, Any]:
    prompt = build_reasoning_prompt(goal, obs)
    
    # Debug: Save full prompt sent to external API
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    debug_filename = f"debug_full_prompt_sent_to_api_{timestamp}.txt"
    with open(debug_filename, 'w', encoding='utf-8') as f:
        f.write(f"FULL PROMPT SENT TO EXTERNAL API at {datetime.now()}\n")
        f.write(f"Goal: {goal}\n")
        f.write("=" * 80 + "\n")
        f.write(prompt)
        f.write("\n" + "=" * 80 + "\n")
        f.write(f"Prompt length: {len(prompt)} characters\n")
    print(f"🔍 DEBUG: Saved full prompt ({len(prompt)} chars) to {debug_filename}")
    
    try:
        if external_client:
            # Use external API (preferred for web automation)
            print(f"🌐 Using external API for web reasoning...")
            raw = external_client.query_external_api(prompt)
        else:
            # Fallback to internal LLM (for testing when external API not available)
            if diagnose_user_intent:
                print(f"🔧 Using internal LLM for web reasoning...")
                raw = diagnose_user_intent(prompt)
            else:
                raise ValueError("No LLM available - external client required or internal LLM not imported")
        
        # Handle case where internal LLM returns dict instead of string
        if isinstance(raw, dict):
            print(f"🔧 Internal LLM returned dict, converting to expected format...")
            # Convert internal LLM response to expected web automation format
            return {
                "reasoning": "Using internal LLM fallback for web automation",
                "confidence": 0.7,
                "actions": [{"type": "click", "selector": ".btn-primary", "expected_result_hint": "internal_llm_fallback"}]
            }
        
        print(f"🔍 Raw LLM response: {str(raw)[:200]}...")
        
        # Try to extract JSON from response
        start = raw.find("{")
        end = raw.rfind("}")
        if start == -1 or end == -1:
            print("⚠️ No JSON braces found in response")
            raise ValueError("No JSON found in response")
        
        json_text = raw[start:end+1]
        print(f"🔍 Extracted JSON: {str(json_text)[:100]}...")
        parsed = json.loads(json_text)
        
        # Validate required fields
        if "actions" not in parsed:
            print("⚠️ No 'actions' field, adding empty list")
            parsed["actions"] = []
        if "confidence" not in parsed:
            print("⚠️ No 'confidence' field, setting default")
            parsed["confidence"] = 0.5
        if "reasoning" not in parsed:
            print("⚠️ No 'reasoning' field, setting default")
            parsed["reasoning"] = "Analysis completed"
            
        print(f"✅ Successfully parsed reasoning response")
        return parsed
        
    except json.JSONDecodeError as e:
        print(f"❌ JSON parsing error: {e}")
        return {
            "reasoning": f"JSON parsing failed: {str(e)}",
            "confidence": 0.0,
            "actions": [{"type":"noop","selector":"","selector_strategy":"none","expected_result_hint":"json_parse_failed"}]
        }
    except Exception as e:
        print(f"❌ LLM reasoning error: {e}")
        return {
            "reasoning": f"Failed to get reasoning from LLM: {str(e)}",
            "confidence": 0.0,
            "actions": [{"type":"noop","selector":"","selector_strategy":"none","expected_result_hint":"llm_failed"}]
        }

def build_verification_prompt(goal: str, pre_actions: List[Dict[str,Any]], post_dom_snippet: str) -> str:
    return f"""
Verify whether the goal segment is achieved.
Goal: {goal}
Actions executed: {json.dumps(pre_actions)[:1000]}
Post DOM snippet: {post_dom_snippet[:1500]}
Respond JSON:
{{"achieved": true|false, "confidence": 0.0-1.0, "evidence": "short citation"}}
"""

def load_semantic_memory(domain: str) -> Dict[str, Any]:
    """Load domain-specific semantic memory from persistent storage"""
    try:
        memory_path = "memory/web_semantic_cache.json"
        if os.path.exists(memory_path):
            with open(memory_path, 'r') as f:
                memory = json.load(f)
                return memory.get(domain, {})
    except Exception as e:
        print(f"⚠️ Failed to load semantic memory: {e}")
    return {}

def save_semantic_memory(domain: str, element_data: Dict[str, Any]):
    """Save successful element interactions to persistent memory"""
    try:
        os.makedirs("memory", exist_ok=True)
        memory_path = "memory/web_semantic_cache.json"
        
        memory = {}
        if os.path.exists(memory_path):
            with open(memory_path, 'r') as f:
                memory = json.load(f)
        
        if domain not in memory:
            memory[domain] = {"element_fingerprints": [], "successful_patterns": []}
        
        # Add element fingerprint
        fingerprint = {
            "semantic_label": element_data.get("semantic_label", ""),
            "text_patterns": element_data.get("text_patterns", []),
            "selectors": element_data.get("selectors", []),
            "confidence": element_data.get("confidence", 0.5),
            "timestamp": datetime.now().isoformat(),
            "goal_context": element_data.get("goal_context", "")
        }
        
        memory[domain]["element_fingerprints"].append(fingerprint)
        
        # Keep only last 20 fingerprints per domain to avoid bloat
        if len(memory[domain]["element_fingerprints"]) > 20:
            memory[domain]["element_fingerprints"] = memory[domain]["element_fingerprints"][-20:]
        
        with open(memory_path, 'w') as f:
            json.dump(memory, f, indent=2)
            
        print(f"💾 Saved semantic memory for domain: {domain}")
    except Exception as e:
        print(f"❌ Failed to save semantic memory: {e}")

def extract_domain_from_url(url: str) -> str:
    """Extract domain from URL for memory purposes"""
    if not url:
        return "unknown"
    try:
        if '//' in url:
            return url.split('//')[1].split('/')[0]
        return url.split('/')[0]
    except:
        return "unknown"

def llm_verify(goal: str, actions: List[Dict[str,Any]], dom: str, external_client=None) -> Dict[str, Any]:
    prompt = build_verification_prompt(goal, actions, dom)
    
    try:
        if external_client:
            # Use external API (preferred)
            print(f"🌐 Using external API for verification...")
            raw = external_client.query_external_api(prompt)
        else:
            # Fallback to internal LLM
            if diagnose_user_intent:
                print(f"🔧 Using internal LLM for verification...")
                raw = diagnose_user_intent(prompt)
            else:
                raise ValueError("No LLM available for verification")
        
        # Handle case where internal LLM returns dict instead of string
        if isinstance(raw, dict):
            print(f"🔧 Internal LLM returned dict, creating verification response...")
            # Analyze the goal and DOM to make a simple verification
            achieved = (
                "success" in dom.lower() or "complete" in dom.lower() and any(keyword in goal.lower() for keyword in ["navigate", "open", "load"])
            ) or (
                len(actions) > 0 and actions[0].get("exec_status") == "ok"
            )
            return {
                "achieved": achieved,
                "confidence": 0.7,
                "evidence": "Internal LLM fallback verification"
            }
        
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start:end+1])
        else:
            raise ValueError("No JSON found in verification response")
    except Exception as e:
        print(f"❌ Verification failed: {e}")
        return {"achieved": False, "confidence": 0.0, "evidence": f"verification_error: {str(e)}"}
