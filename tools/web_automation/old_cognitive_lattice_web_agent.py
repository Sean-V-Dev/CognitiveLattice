#!/usr/bin/env python3
"""
Decoupled Web Agent Core
========================

Pure web automation functionality that reports to the cognitive lattice
but doesn't manage it directly.
"""

import asyncio
import json
import re
import time
from datetime import datetime
from typing import Dict, Any, List, Optional
from .browser_engine_tool import BrowserEngineTool
from tools.web_automation.old_vision_dom_reasoner import (
    compress_dom, summarize_interactive_elements, hash_dom, 
    llm_verify, llm_reason, build_reasoning_prompt,
    load_semantic_memory, save_semantic_memory, extract_domain_from_url
)
from utils.dom_diff import analyze_dom_changes, should_use_dom_diff


def _classify_change_type(change_analysis: Dict[str, Any], action_results: List[Dict[str, Any]]) -> str:
    """Classify the type of DOM change that occurred"""
    if not change_analysis.get("has_changes"):
        return "no_change"
    
    patterns = change_analysis.get("content_patterns", [])
    
    # Check for navigation actions
    if any(r.get("type") == "navigate" for r in action_results):
        return "navigation"
    
    # Check for specific content patterns
    if "location_results" in patterns:
        return "location_search_results"
    elif "menu_items" in patterns:
        return "menu_loaded"
    elif "modal_popup" in patterns:
        return "modal_opened"
    elif "form_elements" in patterns:
        return "form_updated"
    
    # Check for new interactive elements
    new_interactive_count = len(change_analysis.get("new_interactive_elements", []))
    if new_interactive_count > 5:
        return "major_content_change"
    elif new_interactive_count > 0:
        return "minor_content_change"
    
    return "unknown_change"


def extract_selection_signals(html: str) -> list[dict]:
    """Extract selection signals from HTML"""
    signals = []
    for m in re.finditer(r"<([a-zA-Z0-9]+)\b([^>]*)>", html or ""):
        tag = m.group(1).lower()
        attrs_raw = m.group(2) or ""
        attrs = {}
        for a in re.finditer(r'(\w[\w:-]*)\s*=\s*"([^"]*)"', attrs_raw):
            attrs[a.group(1)] = a.group(2)
        
        # Look for selection indicators
        classes = attrs.get('class', '').lower()
        if any(token in classes for token in ['selected', 'active', 'chosen', 'checked']):
            signals.append({
                'tag': tag,
                'classes': classes,
                'selected': True
            })
    
    return signals


class WebAgentCore:
    """
    Core web automation functionality - reports progress to lattice
    but doesn't manage lattice state directly.
    """
    
    def __init__(self, external_client=None, cognitive_lattice=None, enable_stealth=True):
        self.external_client = external_client
        self.lattice = cognitive_lattice  # Direct assignment like old system
        self.browser = BrowserEngineTool(enable_stealth=enable_stealth)
        self.memory = {}
        self.session_log = []
        self.dom_history = []
        self.current_web_task = None  # Track current task like old system
    
    async def ensure_browser(self, headless: bool = False):
        """Ensure browser is initialized"""
        if not self.browser.page:
            await self.browser.initialize_browser(headless=headless)
    
    def set_lattice(self, lattice):
        """Set the cognitive lattice reference"""
        self.lattice = lattice
    
    async def close_browser(self):
        """Clean up browser resources"""
        if self.browser:
            await self.browser.close_browser()
    
    def _report_step_to_lattice(self, step_description: str, step_data: Dict[str, Any]) -> None:
        """Report step completion to cognitive lattice using SAME format as stepwise"""
        if not self.lattice or not self.current_web_task:
            return
        
        try:
            # Get current step number (same as stepwise system)
            active_task = self.lattice.get_active_task()
            if active_task:
                completed_steps = active_task.get("completed_steps", [])
                current_step_number = len(completed_steps) + 1
                
                # Use SAME method call as stepwise system
                self.lattice.execute_step(
                    step_number=current_step_number,
                    user_input=step_description,
                    result=f"Web step: {step_data.get('success', False)}"
                )
                
                # If step was successful, mark it completed (same as stepwise)
                if step_data.get('success', False):
                    self.lattice.mark_step_completed(current_step_number)
                
                print(f"✅ Web step {current_step_number} reported to lattice")
            
        except Exception as e:
            print(f"⚠️ Failed to report to lattice: {e}")
    
    async def observe(self, goal: str = "") -> Dict[str, Any]:
        """Enhanced observation with interactive elements and semantic memory"""
        await self.ensure_browser()
        page = self.browser.page

        # Ensure DOM is ready before observing, wait for network to be idle
        try:
            # Wait for network to be idle, which is a better signal for SPAs
            await page.wait_for_load_state('networkidle', timeout=7000)
        except Exception as e:
            print(f"⏳ Timeout waiting for network idle, falling back to load state. Error: {e}")
            try:
                await page.wait_for_load_state('load', timeout=5000)
            except Exception as e2:
                print(f"⏳ Timeout waiting for load state, proceeding anyway. Error: {e2}")
        
        # A small extra delay for any final rendering scripts to finish.
        await asyncio.sleep(1.5)

        url = page.url if page else "about:blank"
        title = await page.title() if page else ""
        raw_dom = await page.content() if page else ""
        compressed = compress_dom(raw_dom, goal)  # Pass goal for location-aware compression

        # Interactive-only summary and selection signals
        interactive = summarize_interactive_elements(raw_dom, max_items=100)
        selection = extract_selection_signals(raw_dom)
        screenshot_resp = await self.browser.take_screenshot()

        # Load semantic memory for this domain
        domain = extract_domain_from_url(url)
        domain_memory = load_semantic_memory(domain)

        # Build cognitive lattice context for comprehensive AI epistemic awareness
        lattice_context = {}
        if self.lattice:
            lattice_context = self._build_comprehensive_lattice_context()

        return {
            "url": url,
            "title": title,
            "screenshot": screenshot_resp.get("filepath") if screenshot_resp else None,
            "raw_dom": raw_dom,
            "compressed_dom": compressed,
            "interactive_summary": interactive,
            "semantic_memory": self.memory.get("semantic_labels", {}),
            "domain_memory": domain_memory,
            "lattice_context": lattice_context,  # ADD THIS - the missing piece!
        }
    
    def _clean_selector(self, selector: str) -> str:
        """Clean up selector by removing invalid format like 'div[role='button'] | Text: 'Button Text''"""
        if not selector:
            return selector
        
        # Remove the descriptive text part (everything after |)
        if " | " in selector:
            selector = selector.split(" | ")[0].strip()
        
        # Remove any Text: parts that might remain
        if " Text: " in selector:
            selector = selector.split(" Text: ")[0].strip()
            
        return selector

    async def execute_actions(self, actions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Enhanced action execution with DOM change detection"""
        results = []
        for act in actions:
            a_type = act.get("type")
            raw_sel = act.get("selector", "")
            sel = self._clean_selector(raw_sel)
            url = act.get("url")
            
            # Debug logging for selector cleaning
            if raw_sel != sel:
                print(f"🔧 Cleaned selector: '{raw_sel}' → '{sel}'")
            
            # CAPTURE DOM BEFORE ACTION
            dom_before = await self.browser.page.content()
            dom_hash_before = hash_dom(compress_dom(dom_before))
            
            try:
                if a_type == "navigate":
                    target_url = url or sel
                    await self.browser.navigate_to_url(target_url)
                    try:
                        await self.browser.page.wait_for_load_state('domcontentloaded', timeout=8000)
                    except Exception:
                        pass
                    await asyncio.sleep(0.5)
                elif a_type == "click":
                    # Robust click: ensure visible, scroll into view, then click. Retry with fallbacks if no change.
                    try:
                        locator = self.browser.page.locator(sel)
                        await locator.scroll_into_view_if_needed()
                        await locator.click(timeout=5000)
                    except Exception as click_error:
                        # If we get a strict mode violation, try to find a more specific selector
                        if "strict mode violation" in str(click_error):
                            # Extract suggestions from Playwright's error message for more specific selectors
                            error_msg = str(click_error)
                            suggested_selectors = []
                            
                            # Parse Playwright's suggestions from error message
                            if "get_by_role(" in error_msg:
                                import re
                                role_matches = re.findall(r'get_by_role\("([^"]+)",\s*name="([^"]+)"\)', error_msg)
                                for role, name in role_matches[:3]:  # Try up to 3 suggestions
                                    suggested_selectors.append((f"get_by_role('{role}', name='{name}')", role, name))
                            
                            if suggested_selectors:
                                print(f"🔧 Strict mode violation detected, trying {len(suggested_selectors)} suggested selectors...")
                                for i, (selector_desc, role, name) in enumerate(suggested_selectors):
                                    try:
                                        print(f"🔄 Attempt {i+1}: Trying {selector_desc}")
                                        specific_locator = self.browser.page.get_by_role(role, name=name)
                                        await specific_locator.scroll_into_view_if_needed()
                                        await specific_locator.click(timeout=5000)
                                        print(f"✅ Successfully clicked using suggested selector: {selector_desc}")
                                        break  # Success, exit the retry loop
                                    except Exception as specific_error:
                                        print(f"❌ Suggested selector {i+1} failed: {specific_error}")
                                        if i == len(suggested_selectors) - 1:  # Last attempt
                                            raise click_error  # Re-raise original error
                                        continue
                            else:
                                # Fallback for common patterns without specific suggestions
                                print(f"🔧 Strict mode violation detected, trying generic fallbacks...")
                                fallback_attempts = [
                                    ("first matching element", lambda: self.browser.page.locator(sel).first),
                                    ("last matching element", lambda: self.browser.page.locator(sel).last),
                                ]
                                
                                for attempt_name, locator_func in fallback_attempts:
                                    try:
                                        print(f"🔄 Trying {attempt_name}...")
                                        fallback_locator = locator_func()
                                        await fallback_locator.scroll_into_view_if_needed()
                                        await fallback_locator.click(timeout=5000)
                                        print(f"✅ Successfully clicked using {attempt_name}")
                                        break
                                    except Exception as fallback_error:
                                        print(f"❌ {attempt_name} also failed: {fallback_error}")
                                        continue
                                else:
                                    raise click_error  # Re-raise original error if all fallbacks fail
                        else:
                            raise click_error  # Re-raise original error
                elif a_type == "press_key":
                    key = act.get("key", "Enter")
                    focus_selector = sel
                    try:
                        if focus_selector:
                            await self.browser.page.wait_for_selector(focus_selector, timeout=3000)
                            await self.browser.page.focus(focus_selector)
                        await self.browser.page.keyboard.press(key)
                        await asyncio.sleep(0.5)
                    except Exception as e:
                        raise RuntimeError(f"Failed to press key {key}: {e}")
                elif a_type == "type":
                    text = act.get("text", "")
                    print(f"🔤 Typing '{text}' into {sel}")

                    # Clear field first, then type
                    await self.browser.page.fill(sel, "")
                    await asyncio.sleep(0.4)
                    await self.browser.page.fill(sel, text)

                    # Analyze context to determine appropriate post-typing behavior
                    elem = await self.browser.page.query_selector(sel)
                    should_auto_submit = await self._should_auto_submit_after_typing(elem, text, act)
                    
                    if should_auto_submit == "submit":
                        print("🎯 Auto-submitting search/single-input field...")
                        await asyncio.sleep(0.5)
                        await self.browser.page.keyboard.press("Enter")
                    elif should_auto_submit == "select_suggestion":
                        try:
                            role = await elem.get_attribute("role") if elem else None
                            if role in ("searchbox", "combobox", "textbox"):
                                print(f"🔍 Auto-selecting from {role} suggestions...")
                                aria_controls = await elem.get_attribute("aria-controls") if elem else None
                                listbox_selector = f"#{aria_controls} [role='option']" if aria_controls else "[role='option']"
                                try:
                                    await self.browser.page.wait_for_selector(listbox_selector, timeout=3000)
                                    options = await self.browser.page.query_selector_all(listbox_selector)
                                    if options:
                                        print(f"✅ Found {len(options)} options, clicking first one")
                                        await options[0].click()
                                except Exception as e:
                                    print(f"❌ Suggestion selection failed, falling back to Enter: {e}")
                                    await self.browser.page.keyboard.press("Enter")
                        except Exception as e:
                            print(f"⚠️ Suggestion handling failed: {e}")
                    else:
                        print("⏭️ Continuing to next field (multi-input form detected)")
                        # Just ensure field stays focused for potential next action
                        try:
                            await self.browser.page.focus(sel)
                        except Exception:
                            pass
                elif a_type == "wait":
                    await asyncio.sleep(float(act.get("seconds",1)))
                elif a_type == "noop":
                    pass
                status = "ok"
            except Exception as e:
                print(f"❌ Action {a_type} failed: {e}")
                status = f"error:{e}"
            
            # CAPTURE DOM AFTER ACTION & ANALYZE CHANGES
            try:
                await asyncio.sleep(3.5)  # Increased wait for search results and dynamic content
                dom_after = await self.browser.page.content()
                dom_hash_after = hash_dom(compress_dom(dom_after))
            except Exception as e:
                print(f"❌ Failed to capture DOM after action - browser may be closed: {e}")
                results.append({
                    "action": act,
                    "status": f"browser_error:{e}",
                    "dom_changed": False,
                    "change_analysis": {"error": "Browser closed or inaccessible"}
                })
                break  # Exit the action loop if browser is gone
            
            # DOM DIFF ANALYSIS - Surgical precision change detection
            change_analysis = analyze_dom_changes(dom_before, dom_after)
            
            # For clicks, also check if only URL fragment changed (fake success)
            url_before = getattr(self, '_last_url', '')
            url_after = self.browser.page.url
            self._last_url = url_after
            
            # URL fragment change without DOM change indicates intercepted click
            url_fragment_only = (url_before.split('#')[0] == url_after.split('#')[0] and 
                               url_before != url_after)
            
            dom_changed = dom_hash_before != dom_hash_after
            
            # Debug logging for click analysis
            if a_type == "click":
                print(f"🔍 Click Debug - URL before: {url_before}")
                print(f"🔍 Click Debug - URL after: {url_after}")
                print(f"🔍 Click Debug - url_fragment_only: {url_fragment_only}")
                print(f"🔍 Click Debug - dom_changed: {dom_changed}")
                print(f"🔍 Click Debug - status: {status}")
            
            # Log DOM diff analysis for debugging
            if change_analysis['has_changes']:
                print(f"🔍 DOM Changes Detected: {change_analysis['change_summary']}")
                if change_analysis['new_interactive_count'] > 0:
                    print(f"   📍 {change_analysis['new_interactive_count']} new interactive elements")
                if 'location_results' in change_analysis['content_patterns']:
                    print(f"   🏪 Location search results appeared!")
            else:
                print(f"🔍 No DOM changes detected after {a_type} action")
                
            # Merge DOM diff analysis with legacy change_analysis for backward compatibility
            change_analysis.update({
                "dom_changed": dom_changed,
                "url_fragment_only": url_fragment_only,
                "analysis_timestamp": time.time()
            })

            # For click actions, retry if no DOM changes occurred (regardless of URL behavior)
            # This catches both intercepted clicks and clicks that should trigger changes but don't
            if a_type == "click" and status == "ok" and not dom_changed:
                print(f"🔄 Click produced no DOM changes - attempting retries (URL fragment change: {url_fragment_only}, DOM change: {dom_changed})")
                
                # Retry with stronger fallbacks - these are now async functions
                async def force_click_retry():
                    await locator.click(force=True, timeout=3000)
                
                async def js_click_retry():
                    await self.browser.page.evaluate("(s)=>{const el=document.querySelector(s); if(el) el.click();}", sel)
                
                async def focus_enter_retry():
                    await locator.focus()
                    await self.browser.page.keyboard.press("Enter")
                
                retry_attempts = [
                    ("force click", force_click_retry),
                    ("JS click", js_click_retry),
                    ("focus + enter", focus_enter_retry)
                ]
                
                for attempt_name, attempt_func in retry_attempts:
                    try:
                        print(f"🔄 Retrying with {attempt_name}...")
                        locator = self.browser.page.locator(sel)
                        await attempt_func()
                        await asyncio.sleep(1.5)
                        
                        dom_after_retry = await self.browser.page.content()
                        url_after_retry = self.browser.page.url
                        
                        # Check for real changes (not just URL fragment)
                        real_dom_change = hash_dom(compress_dom(dom_after_retry)) != dom_hash_before
                        real_url_change = url_after_retry.split('#')[0] != url_before.split('#')[0]
                        
                        if real_dom_change or real_url_change:
                            print(f"✅ {attempt_name} succeeded! DOM changed: {real_dom_change}, Real URL change: {real_url_change}")
                            dom_changed = True
                            dom_after = dom_after_retry
                            dom_hash_after = hash_dom(compress_dom(dom_after_retry))
                            self._last_url = url_after_retry
                            break
                        else:
                            print(f"❌ {attempt_name} also failed to produce real changes")
                    except Exception as e:
                        print(f"❌ {attempt_name} threw exception: {e}")
                        continue

            # For click actions, check if the element is gone
            if a_type == "click" and status == "ok":
                try:
                    await self.browser.page.query_selector(sel, state='hidden', timeout=1000)
                    change_analysis["clicked_element_disappeared"] = True
                    print(f"✅ Verification: Clicked element '{sel}' is now hidden.")
                except Exception:
                    change_analysis["clicked_element_disappeared"] = False
                    print(f"ℹ️ Verification: Clicked element '{sel}' is still visible.")
            
            if dom_changed:
                print(f"✅ DOM changed after {a_type} action!")
                
                try:
                    modal_selectors = [
                        "[role='dialog']", ".modal", ".popup", ".overlay",
                        "*[class*='modal']", "*[class*='popup']", "*[class*='dialog']",
                        "input[placeholder*='address']", "input[placeholder*='zip']", 
                        "input[placeholder*='location']", "input[type='search']",
                        "*[class*='search-container']", "*[class*='text-input-container']",
                        "*[class*='input-container']", "input[role='combobox']",
                        "input[aria-label*='search location']", "input[name*='Search']",
                        "input[autocomplete='on']", "input[aria-autocomplete='list']"
                    ]
                    
                    new_elements = []
                    for selector in modal_selectors:
                        try:
                            elements = await self.browser.page.query_selector_all(selector)
                            if elements:
                                for elem in elements[:2]:
                                    text = await elem.inner_text()
                                    tag = await elem.evaluate('el => el.tagName')
                                    placeholder = await elem.get_attribute("placeholder")
                                    new_elements.append({
                                        "selector": selector,
                                        "tag": tag,
                                        "text": text.strip()[:50],
                                        "placeholder": placeholder
                                    })
                        except:
                            pass
                    
                    change_analysis["dom_changed"] = True
                    change_analysis["new_elements"] = new_elements
                    change_analysis["analysis_timestamp"] = time.time()
                    
                    # Store changes in memory
                    if new_elements:
                        dom_changes = self.memory.setdefault("dom_changes", [])
                        dom_changes.append({
                            "action": act,
                            "changes": new_elements,
                            "timestamp": time.time()
                        })
                        
                except Exception as e:
                    change_analysis["dom_changed"] = True
                    change_analysis["error"] = str(e)
            else:
                change_analysis["dom_changed"] = False
            
            results.append({
                **act, 
                "exec_status": status, 
                "timestamp": time.time(),
                "dom_before_hash": dom_hash_before,
                "dom_after_hash": dom_hash_after,
                "change_analysis": change_analysis
            })
            
            # Store successful selectors in semantic memory
            if status == "ok" and sel:
                sem = self.memory.setdefault("semantic_labels", {})
                label = act.get("expected_result_hint","")
                sem.setdefault(sel, {"uses":0,"labels":[]})
                sem[sel]["uses"] += 1
                if label and label not in sem[sel]["labels"]:
                    sem[sel]["labels"].append(label)
                    
        return results

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL for comparison"""
        if not url:
            return ""
        try:
            if '//' in url:
                return url.split('//')[1].split('/')[0]
            return url.split('/')[0]
        except:
            return url

    async def _should_auto_submit_after_typing(self, elem, text: str, action: Dict[str, Any]) -> str:
        """
        Determine if we should auto-submit after typing based on context.
        Returns: 'submit', 'select_suggestion', or 'continue'
        """
        if not elem:
            return "continue"
        
        try:
            # Get element attributes
            elem_type = await elem.get_attribute("type") or ""
            role = await elem.get_attribute("role") or ""
            placeholder = await elem.get_attribute("placeholder") or ""
            name = await elem.get_attribute("name") or ""
            aria_label = await elem.get_attribute("aria-label") or ""
            form_elem = await elem.evaluate("el => el.closest('form')")
            
            # Combine all text for analysis
            all_text = f"{elem_type} {role} {placeholder} {name} {aria_label}".lower()
            
            # Get step goal context
            step_goal = action.get("goal") or action.get("step_goal") or getattr(self, 'current_goal', '')
            context_text = f"{step_goal} {text}".lower()
            
            # Search field indicators
            search_indicators = ["search", "query", "find", "look", "google"]
            is_search_field = (
                elem_type == "search" or
                role in ["searchbox", "combobox"] or
                any(indicator in all_text for indicator in search_indicators) or
                "search" in context_text
            )
            
            # Location/address field indicators (should select from suggestions)
            location_indicators = ["zip", "postal", "location", "address", "city", "state", "country"]
            is_location_field = any(indicator in all_text for indicator in location_indicators)
            location_context = any(indicator in context_text for indicator in location_indicators)
            
            # ZIP code specific logic - ZIP codes should submit immediately to trigger search
            is_zip_code = (
                len(text) == 5 and text.isdigit() or  # 5-digit ZIP code
                any(indicator in all_text for indicator in ["zip", "postal"]) or
                ("zip" in context_text and text.isdigit())
            )
            
            # Form field counting (if in a form with multiple inputs)
            form_inputs_count = 1  # default assume single
            if form_elem:
                form_inputs_count = await form_elem.evaluate("""
                    form => form.querySelectorAll('input[type="text"], input[type="email"], input[type="password"], input[type="tel"], textarea').length
                """)
            
            # Decision logic
            if is_zip_code:
                # ZIP codes should submit immediately to dismiss autocomplete and trigger search
                print(f"🔑 Detected ZIP code '{text}' - will press Enter to trigger search")
                return "submit"
            elif is_location_field or location_context:
                # Other location fields should select from suggestions if available
                return "select_suggestion"
            elif is_search_field and form_inputs_count <= 2:  # Search box or simple search form
                # Single search fields should submit
                return "submit"
            elif form_inputs_count > 2:
                # Multi-field forms should continue to next field
                return "continue"
            elif "submit" in context_text or "search" in context_text:
                # Context suggests immediate submission
                return "submit"
            else:
                # Default for ambiguous cases
                return "continue"
                
        except Exception as e:
            print(f"⚠️ Auto-submit detection failed: {e}")
            # Safe fallback: for search-like text, submit; otherwise continue
            if any(word in text.lower() for word in ["search", "find", "pics", "images"]):
                return "submit"
            return "continue"

    def _save_successful_interaction(self, url: str, actions: List[Dict[str, Any]], goal: str):
        """Save successful element interactions to semantic memory"""
        try:
            domain = extract_domain_from_url(url)
            
            for action in actions:
                if action.get("exec_status") == "ok" and action.get("selector"):
                    element_data = {
                        "semantic_label": self._extract_semantic_label(action, goal),
                        "text_patterns": [action.get("text", "")],
                        "selectors": [action.get("selector", "")],
                        "confidence": 0.8,  # High confidence for successful interactions
                        "goal_context": goal
                    }
                    save_semantic_memory(domain, element_data)
        except Exception as e:
            print(f"⚠️ Failed to save successful interaction: {e}")

    def _extract_semantic_label(self, action: Dict[str, Any], goal: str) -> str:
        """Extract semantic label for an action based on context"""
        action_type = action.get("type", "")
        selector = action.get("selector", "")
        text = action.get("text", "")
        
        if "order" in goal.lower() and action_type == "click":
            if any(keyword in selector.lower() for keyword in ["order", "start", "begin"]):
                return "start_order_button"
        elif "location" in goal.lower():
            if action_type == "click":
                return "location_selector_button"
            elif action_type == "type":
                return "location_input_field"
        elif "cookie" in goal.lower() or "accept" in goal.lower():
            return "modal_dismiss_button"
        
        return f"{action_type}_element"
        
    def get_current_step_context(self) -> Dict[str, Any]:
        """
        Get the current step context from the lattice.
        Returns what step we're on and what's been completed.
        """
        if not self.lattice:
            return {"step": "unknown", "completed_actions": [], "next_action": "start"}
            
        # Get the active task (web automation task)
        active_task = self.lattice.get_active_task()
        if not active_task:
            return {"step": "start", "completed_actions": [], "next_action": "create_plan"}
            
        # Extract web automation progress
        completed_steps = active_task.get("completed_steps", [])
        task_plan = active_task.get("task_plan", [])
        
        # Find current step
        current_step_index = len(completed_steps)
        
        context = {
            "task_title": active_task.get("task_title", "Web Automation"),
            "original_query": active_task.get("query", ""),
            "total_steps": len(task_plan),
            "current_step_index": current_step_index,
            "completed_actions": [step.get("description", "") for step in completed_steps],
            "next_action": task_plan[current_step_index] if current_step_index < len(task_plan) else "complete"
        }
        
        return context
        
    def _normalize_step(self, step, idx: int) -> Dict[str, Any]:
        """
        Ensure every execution step is a dict with at least: step_id, goal, action.
        Accepts legacy string form and already-correct dicts.
        """
        if isinstance(step, dict):
            # Fill required keys if missing
            return {
                "step_id": step.get("step_id", idx + 1),
                "goal": step.get("goal") or step.get("description") or step.get("text") or f"Step {idx+1}",
                "action": step.get("action", "interact"),
                **{k: v for k, v in step.items() if k not in ["step_id", "goal", "action"]}
            }
        # Legacy string
        return {
            "step_id": idx + 1,
            "goal": str(step),
            "action": "interact"
        }

    async def create_execution_plan(self, high_level_goal: str, target_url: str) -> Dict[str, Any]:
        """
        Dynamically creates a multi-step plan using the LLM's reasoning capabilities.
        ALWAYS returns {'plan': {...}, 'execution_plan': [ {step dicts...} ] }
        """
        step_context = self.get_current_step_context()
        if step_context.get("original_query") == high_level_goal and step_context.get("task_title"):
            print(f"[LATTICE] Continuing existing task: {step_context['task_title']}")
            return {"plan": step_context.get("next_action", "complete"), "context": step_context, "continuing_task": True}

        # This prompt teaches the AI HOW to think, instead of WHAT to think.
        plan_prompt = f"""
You are an expert autonomous web agent. Your task is to create a concise, step-by-step plan to achieve the user's high-level goal.

**User's Goal:** "{high_level_goal}"
**Target Website:** "{target_url}"

**Your Current Progress (Cognitive Lattice):**
{self._build_lattice_context()}

**Instructions for Creating the Plan:**
1. **Review Your Progress:** First, examine your cognitive lattice to see what has already been accomplished. Don't repeat actions that have already been successfully completed.
2. **Analyze the User's Goal:** Break down the user's request into its core components.
3. **General Website Heuristics:** Always assume the first step is to navigate to the URL and handle any initial pop-ups (like cookie banners).
4. **Logical Steps:** Think step-by-step. What is the most logical sequence of actions a human would take?
5. **Avoid Redundancy:** Each step should be distinctly different. Don't create steps that would repeat the same action or accomplish something already shown as completed in your lattice.
6. **Describe Actions, Not Code:** Phrase each step as a high-level goal (e.g., "Find the search bar and enter the zip code") rather than a specific command (e.g., "Click the div with id='search'").
7. **Be Specific:** If the user mentions specific data (like ZIP codes, items, names), include them in the plan steps.

**Output Format:**
Return a JSON object with a single key "plan" containing a list of simple, actionable goal strings.

**Example for a location search goal:**
{{
    "plan": [
        "Navigate to the website and dismiss any initial pop-ups.",
        "Look for a 'Find Locations' or 'Store Locator' feature and click it.",
        "Enter the zip code {high_level_goal.split('ZIP code')[-1].split(',')[0].strip() if 'ZIP code' in high_level_goal else '45305'} to search for nearby locations.",
        "Select the first available location from the search results."
    ]
}}

**Important: Use your cognitive lattice to avoid creating redundant steps. If your lattice shows you've already entered a ZIP code successfully, don't create another step to enter it again. Let the complexity of the goal and what remains to be accomplished determine the number of steps needed.**
"""
        
        print(f"🧠 Asking LLM to create a dynamic plan for: '{high_level_goal}'")
        
        if self.external_client:
            try:
                plan_response = self.external_client.query_external_api(plan_prompt)
                json_match = re.search(r'\{.*\}', plan_response, re.DOTALL)
                if json_match:
                    plan_json_str = json_match.group(0)
                    plan_data = json.loads(plan_json_str)
                    plan_steps = plan_data.get('plan', [])

                    execution_plan = [
                        {"step_id": i + 1, "goal": goal_str, "action": "interact"}
                        for i, goal_str in enumerate(plan_steps)
                    ]
                    if execution_plan:
                        execution_plan[0]['action'] = 'navigate'

                    plan = {
                        "goal": high_level_goal,
                        "target_url": target_url,
                        "execution_plan": execution_plan
                    }
                    
                    if self.lattice:
                        # Use the SAME method as stepwise system
                        task_plan = [step.get('goal', '') for step in plan.get('execution_plan', [])]
                        task_result = self.lattice.create_new_task(
                            query=high_level_goal,
                            task_plan=task_plan  # Convert to same format as stepwise
                        )
                        self.current_web_task = task_result  # Store the result, not just ID
                        print(f"[LATTICE] Created web task using stepwise format: {task_result}")
                    
                    print(f"📋 Created dynamic execution plan with {len(plan.get('execution_plan', []))} steps")
                    for i, step in enumerate(plan.get('execution_plan', []), 1):
                        print(f"  {i}. {step.get('goal', 'Unknown step')}")
                    
                    return {
                        "plan": plan,
                        "context": {"step": "start", "completed_actions": [], "next_action": plan.get("execution_plan", [{}])[0].get("goal", "start")},
                        "continuing_task": False
                    }
            except Exception as e:
                print(f"❌ Dynamic plan creation failed: {e}")
        
        # Fallback simple plan
        print("⚠️ Using fallback plan due to LLM unavailability")
        fallback_plan_struct = [
            {"step_id": 1, "goal": f"Navigate to {target_url} and handle any pop-ups", "action": "navigate"},
            {"step_id": 2, "goal": "Analyze the page and find the main action to achieve the goal", "action": "interact"}
        ]
        fallback_plan = {"goal": high_level_goal, "target_url": target_url, "execution_plan": fallback_plan_struct}
        
        if self.lattice:
            task_id = self.lattice.create_new_task(query=high_level_goal, task_plan=fallback_plan_struct)
            self.current_web_task = task_id
        
        return {"plan": fallback_plan, "context": {"step": "start", "completed_actions": [], "next_action": "Navigate to website"}, "continuing_task": False}
    
    async def analyze_dom_changes(self, previous_dom: str, current_dom: str, action_taken: Dict[str, Any]) -> Dict[str, Any]:
        """
        Analyze what changed in the DOM after an action.
        This helps understand if modals opened, content appeared, etc.
        """
        analysis_prompt = f"""
Analyze DOM changes after web action:

Action taken: {json.dumps(action_taken, indent=2)}

Previous DOM signature: {hash_dom(previous_dom)}
Current DOM signature: {hash_dom(current_dom)}

Current DOM (truncated): {compress_dom(current_dom)[:2000]}

What changed after this action? Look for:
1. New modals, popups, or dialogs that appeared
2. New interactive elements (buttons, inputs, forms)
3. Content that appeared or disappeared
4. Navigation changes
5. Error messages or success indicators

Output JSON:
{{
    "changes_detected": true|false,
    "change_type": "modal_opened|navigation|content_update|form_appeared|error",
    "new_elements": ["list of new interactive elements found"],
    "disappeared_elements": ["elements that are no longer visible"],
    "success_indicators": ["signs that the action succeeded"],
    "next_recommended_action": "what should be done next based on changes",
    "dom_summary": "brief description of current page state"
}}
"""
        
        if self.external_client:
            try:
                analysis_response = self.external_client.query_external_api(analysis_prompt)
                start = analysis_response.find("{")
                end = analysis_response.rfind("}")
                if start != -1 and end != -1:
                    return json.loads(analysis_response[start:end+1])
            except Exception as e:
                print(f"⚠️ DOM analysis failed: {e}")
        
        # Simple fallback analysis
        changes_detected = hash_dom(previous_dom) != hash_dom(current_dom)
        return {
            "changes_detected": changes_detected,
            "change_type": "unknown" if changes_detected else "no_change",
            "new_elements": [],
            "dom_summary": "Unable to analyze changes"
        }
    
    async def execute_plan_with_monitoring(self, execution_plan: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the plan step by step with continuous DOM monitoring and lattice updates.
        """
        if not isinstance(execution_plan, dict):
            return {"success": False, "error": "Invalid execution plan (not dict)", "partial_results": []}

        raw_plan = execution_plan.get("plan")
        if isinstance(raw_plan, dict):
            overall_goal = raw_plan.get("goal", "")
        elif isinstance(raw_plan, str):
            overall_goal = raw_plan
        else:
            overall_goal = ""

        steps_raw = execution_plan.get("execution_plan", [])
        # Normalize ALL incoming steps defensively
        steps = [self._normalize_step(s, i) for i, s in enumerate(steps_raw)]

        partial_results = []
        for idx, step in enumerate(steps):
            try:
                if not isinstance(step, dict):
                    print(f"⚠️ Step {idx+1} not dict after normalization: {type(step)} => {step}")
                    continue

                step_goal_text = step.get("goal", f"Step {idx+1}")
                print(f"🛠️ Executing Step {idx+1}/{len(steps)} (type={type(step)}): {step_goal_text}")

                # === Observation phase ===
                print(f"🔍 Starting observation phase for step {idx+1}...")
                try:
                    obs = await self.observe(goal=step_goal_text)
                    print(f"✅ Observation completed successfully. URL: {obs.get('url', 'Unknown')}")
                except Exception as obs_error:
                    print(f"❌ Observation failed for step {idx+1}: {obs_error}")
                    import traceback
                    traceback.print_exc()
                    partial_results.append({
                        "step_number": idx + 1,
                        "goal": step_goal_text,
                        "success": False,
                        "error": f"Observation failed: {str(obs_error)}"
                    })
                    continue

                # === Reasoning phase ===
                print(f"🧠 Starting reasoning phase for step {idx+1}...")
                try:
                    reasoning_result = llm_reason(step_goal_text, obs, self.external_client)
                    print(f"✅ Reasoning completed. Actions planned: {len(reasoning_result.get('actions', []))}")
                except Exception as reasoning_error:
                    print(f"❌ Reasoning failed for step {idx+1}: {reasoning_error}")
                    partial_results.append({
                        "step_number": idx + 1,
                        "goal": step_goal_text,
                        "success": False,
                        "error": f"Reasoning failed: {str(reasoning_error)}"
                    })
                    continue

                if isinstance(reasoning_result, str):
                    print(f"⚠️ Reasoning returned string; wrapping as fallback. Raw: {reasoning_result[:120]}...")
                    reasoning_result = {
                        "reasoning": reasoning_result,
                        "actions": [],
                        "confidence": 0.4
                    }
                elif not isinstance(reasoning_result, dict):
                    print(f"⚠️ Unexpected reasoning result type: {type(reasoning_result)}; coercing.")
                    reasoning_result = {"reasoning": str(reasoning_result), "actions": [], "confidence": 0.3}

                actions = reasoning_result.get("actions") or []
                if isinstance(actions, str):
                    # Sometimes model might return serialized text
                    actions = []

                # Guarantee list of dict actions
                safe_actions = []
                for a in actions:
                    if isinstance(a, dict):
                        safe_actions.append(a)
                    else:
                        safe_actions.append({"type": "noop", "raw": str(a)})
                actions = safe_actions

                # === Action execution phase ===
                print(f"🎯 Starting action execution phase for step {idx+1}. Actions to execute: {len(actions)}")
                try:
                    action_results = await self.execute_actions(actions) if actions else []
                    print(f"✅ Action execution completed. Results: {len(action_results)}")
                except Exception as action_error:
                    print(f"❌ Action execution failed for step {idx+1}: {action_error}")
                    import traceback
                    traceback.print_exc()
                    partial_results.append({
                        "step_number": idx + 1,
                        "goal": step_goal_text,
                        "success": False,
                        "error": f"Action execution failed: {str(action_error)}"
                    })
                    continue

                step_record = {
                    "step_number": idx + 1,
                    "goal": step_goal_text,
                    "actions_attempted": len(actions),
                    "actions_executed": action_results,
                    "reasoning": reasoning_result.get("reasoning", ""),
                    "success": True  # We mark structural success; domain success can be refined later
                }
                partial_results.append(step_record)

                # Extract detailed DOM change information from action results
                dom_changes = {}
                successful_actions = []
                failed_actions = []
                
                for action_result in action_results:
                    if action_result.get("exec_status") == "ok":
                        successful_actions.append({
                            "type": action_result.get("type"),
                            "selector": action_result.get("selector"),
                            "text": action_result.get("text"),
                            "url": action_result.get("url"),
                            "timestamp": action_result.get("timestamp")
                        })
                    else:
                        failed_actions.append({
                            "type": action_result.get("type"),
                            "selector": action_result.get("selector"),
                            "error": action_result.get("exec_status")
                        })
                    
                    # Extract DOM change information
                    change_analysis = action_result.get("change_analysis", {})
                    if change_analysis.get("dom_changed"):
                        dom_changes.update({
                            "changes_detected": True,
                            "new_elements": change_analysis.get("new_elements", []),
                            "change_summary": change_analysis.get("change_summary", "DOM modified"),
                            "url_changed": change_analysis.get("url_fragment_only", False)
                        })

                # Report to lattice with detailed information
                self.update_lattice_step(
                    step_description=step_goal_text,
                    action_result={
                        "step_number": idx + 1,
                        "reasoning": reasoning_result.get("reasoning", ""),
                        "confidence": reasoning_result.get("confidence", 0.0),
                        "successful_actions": successful_actions,
                        "failed_actions": failed_actions,
                        "actions_total": len(action_results),
                        "success_rate": len(successful_actions) / len(action_results) if action_results else 0,
                        "current_url": obs.get("url", ""),
                        "page_title": obs.get("title", ""),
                        "achieved": len(successful_actions) > 0 and len(failed_actions) == 0
                    },
                    dom_changes=dom_changes
                )

            except Exception as e:
                print(f"❌ Error executing step {idx+1}: {e}")
                partial_results.append({
                    "step_number": idx + 1,
                    "goal": step.get("goal") if isinstance(step, dict) else str(step),
                    "success": False,
                    "error": str(e)
                })
                # Continue to next step instead of aborting entire run

        any_success = any(r.get("success") for r in partial_results)
        return {
            "success": any_success,
            "partial_results": partial_results,
            "error": None if any_success else "All steps failed"
        }

    def _build_lattice_context(self) -> str:
        """(Defensive version) Build context string without assuming dict steps."""
        if not self.lattice:
            return "No cognitive lattice available."
        try:
            active_task = self.lattice.get_active_task()
            if not active_task:
                return "No active task."
            completed = active_task.get("completed_steps", [])
            plan_steps = active_task.get("task_plan", [])
            # plan_steps may be list[str] or list[dict]
            next_step = None
            if len(completed) < len(plan_steps):
                raw = plan_steps[len(completed)]
                next_step = raw if isinstance(raw, str) else raw.get("goal", raw.get("description", "Unknown"))
            return (
                f"Task: {active_task.get('task_title','Web Automation')}\n"
                f"Progress: {len(completed)}/{len(plan_steps)}\n"
                f"Next: {next_step or 'None'}"
            )
        except Exception as e:
            return f"Error building lattice context: {e}"

    def _build_comprehensive_lattice_context(self) -> Dict[str, Any]:
        """Build comprehensive cognitive lattice context for AI epistemic self-awareness"""
        if not self.lattice:
            return {}
        
        # Get current active task
        active_task = self.lattice.get_active_task()
        
        # Get recent web step events from lattice event log
        recent_actions = []
        web_step_events = [event for event in self.lattice.event_log 
                          if event.get('type') == 'web_step_completed']
        
        for event in web_step_events[-10:]:  # Last 10 web steps
            result = event.get('result', {})
            action_details = result.get('action_details', {})
            recent_actions.append({
                'step_description': event.get('step_description', 'Unknown step'),
                'action_result': action_details,
                'timestamp': event.get('timestamp'),
                'dom_changes': {
                    'changes_detected': result.get('dom_changed', False),
                    'new_elements': result.get('new_elements', [])
                }
            })
        
        # Calculate success rate from recent actions
        successful_actions = sum(1 for action in recent_actions 
                               if action.get('action_result', {}).get('achieved', False))
        success_rate = (successful_actions / len(recent_actions) * 100) if recent_actions else 0
        
        # Extract learning insights from patterns
        insights = []
        
        # Pattern: Recent successful pattern
        if successful_actions > 0:
            insights.append(f"Recent successful pattern: {successful_actions} successful actions")
        
        # Pattern: Repeated failures on same type of elements
        failed_actions = [action for action in recent_actions 
                         if not action.get('action_result', {}).get('achieved', False)]
        if len(failed_actions) >= 2:
            insights.append(f"Warning: {len(failed_actions)} recent failed actions - review approach")
        
        # Build session context
        session_context = {}
        if active_task:
            session_context = {
                "goal": active_task.get("query", "Unknown goal"),
                "status": active_task.get("status", "unknown"),
                "total_steps": len(active_task.get("task_plan", [])),
                "completed_steps": len(active_task.get("completed_steps", []))
            }
        
        return {
            "recent_actions": recent_actions,
            "session_context": session_context,
            "success_rate": f"{success_rate:.1f}%",
            "insights": insights
        }
        
        return {
            "recent_actions": recent_actions,
            "session_context": session_context,
            "success_rate": f"{success_rate:.1f}%",
            "insights": insights
        }
    
    def update_lattice_step(self, step_description: str, action_result: Dict[str, Any], dom_changes: Dict[str, Any]) -> None:
        """
        Update the lattice with the completed step and prepare for next step.
        Only advances the lattice when success is True (verification gated).
        """
        if not self.lattice:
            return
        
        step_success = action_result.get("achieved", False)
        
        # Create comprehensive step result for lattice (similar to stepwise tool execution format)
        step_result = {
            "step_description": step_description,
            "dom_changed": dom_changes.get("changes_detected", dom_changes.get("dom_changed", False)),
            "new_elements": dom_changes.get("new_elements", dom_changes.get("new_interactives", [])),
            "action_details": action_result,
            "success": step_success,
            "current_url": action_result.get("current_url", ""),
            "timestamp": datetime.now().isoformat()
        }
        
        # Add event to lattice (basic web step completed event)
        self.lattice.add_event({
            "type": "web_step_completed",
            "step_description": step_description,
            "result": step_result,
            "timestamp": datetime.now().isoformat()
        })
        
        # Add detailed tool-style execution event (similar to stepwise mode)
        if action_result.get("successful_actions") or action_result.get("failed_actions"):
            tool_results = []
            
            # Process successful actions as tool results
            for action in action_result.get("successful_actions", []):
                tool_results.append({
                    "status": "success",
                    "tool_name": f"web_automation_{action.get('type', 'unknown')}", 
                    "parameters": {
                        "action_type": action.get("type"),
                        "selector": action.get("selector"),
                        "text": action.get("text"),
                        "target_url": action.get("url"),
                        "current_page": action_result.get("current_url", ""),
                        "page_title": action_result.get("page_title", "")
                    },
                    "result": {
                        "status": "success",
                        "action_executed": True,
                        "dom_changes": dom_changes.get("changes_detected", False),
                        "new_interactive_elements": len(dom_changes.get("new_elements", [])),
                        "url_after_action": action_result.get("current_url", ""),
                        "execution_timestamp": action.get("timestamp")
                    },
                    "timestamp": action.get("timestamp", datetime.now().isoformat())
                })
            
            # Process failed actions as tool results  
            for action in action_result.get("failed_actions", []):
                tool_results.append({
                    "status": "error",
                    "tool_name": f"web_automation_{action.get('type', 'unknown')}", 
                    "parameters": {
                        "action_type": action.get("type"),
                        "selector": action.get("selector"),
                        "attempted_target": action.get("selector")
                    },
                    "result": {
                        "status": "error", 
                        "error_message": action.get("error", "Unknown error"),
                        "action_executed": False
                    },
                    "timestamp": datetime.now().isoformat()
                })
            
            # Add tools_executed event (matching stepwise format)
            if tool_results:
                step_number = action_result.get("step_number", 1)
                tools_used = [result["tool_name"] for result in tool_results]
                
                self.lattice.add_event({
                    "type": "tools_executed",
                    "timestamp": datetime.now().isoformat(),
                    "step_number": step_number,
                    "tools_used": tools_used,
                    "tool_results": tool_results
                })
        
        # If there's an active task, update it (only if verified/success)
        active_task = self.lattice.get_active_task()
        if active_task and step_success:
            completed_steps = active_task.get("completed_steps", [])
            current_step_number = len(completed_steps) + 1
            
            # Use lattice's execute_step method to properly track progress
            self.lattice.execute_step(
                step_number=current_step_number,
                user_input=step_description,
                result=f"Web automation step completed successfully. Actions: {len(action_result.get('successful_actions', []))} successful, {len(action_result.get('failed_actions', []))} failed. DOM changed: {dom_changes.get('changes_detected', False)}"
            )
        
        # Save lattice state
        self.lattice.save()

# Test script
if __name__ == "__main__":
    import asyncio
    from core.external_api_client import ExternalAPIClient
    from cognitive_lattice_web_coordinator import CognitiveLatticeWebCoordinator
    
    async def main():
        external_client = ExternalAPIClient()
        coordinator = CognitiveLatticeWebCoordinator(external_api_client=external_client)
        
        # Navigate to any test website 
        success = await coordinator.execute_web_task(
            url="https://example.com",
            objectives=["Navigate to the homepage", "Find contact information"],
            max_iterations=5
        )
        
        print(f"Task completed: {success}")
    
    asyncio.run(main())


async def execute_cognitive_web_task(goal: str, url: str, external_client=None, cognitive_lattice=None) -> Dict[str, Any]:
    agent = WebAgentCore(external_client=external_client, cognitive_lattice=cognitive_lattice)
    try:
        # 1. Create normalized execution plan
        print(f"📋 Creating execution plan for goal: {goal}")
        plan = await agent.create_execution_plan(goal, url)
        
        # 2. Ensure browser is initialized (but don't navigate yet - let the plan handle navigation)
        print(f"🌐 Initializing browser...")
        await agent.ensure_browser()
        
        # 3. Execute plan (which will include navigation as the first step)
        print(f"🚀 Executing plan with {len(plan.get('plan', {}).get('execution_plan', []))} steps...")
        result = await agent.execute_plan_with_monitoring(plan)
        return result
    except Exception as e:
        print(f"❌ Web task execution failed: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e), "partial_results": []}
    finally:
        try:
            await agent.close_browser()
        except Exception:
            pass
