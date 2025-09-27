import asyncio
import os
import shutil
import hashlib
from typing import Dict, Any, Optional, List
from playwright.async_api import async_playwright, Browser, BrowserContext, Page
import json
from datetime import datetime
from contextlib import suppress

# Global registry to persist BrowserEngineTool instances across run_browser_action calls
_BROWSER_TOOL_REGISTRY: Dict[str, "BrowserEngineTool"] = {}

SCHEMA_VERSION = 1

class BrowserEngineTool:
    """
    Core web automation tool using Playwright for browser control.
    Handles browser lifecycle, navigation, element interaction, and verification.
    Supports persistent browser profiles for maintaining cookies, logins, and session data.
    """
    
    def __init__(self, enable_stealth: bool = False, profile_name: str = "default"):
        # Core runtime objects
        self.playwright = None
        self.browser: Optional[Browser] = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None
        self.session_id = None

        # Profile & persistence configuration
        self.screenshots_dir = "screenshots"
        self.enable_stealth = enable_stealth  # Placeholder for future stealth features
        self.profile_name = profile_name
        self.profiles_dir = "browser_profiles"
        self.profile_path = os.path.join(self.profiles_dir, profile_name)
        self.state_file = os.path.join(self.profile_path, "browser_state.json")
        self.user_data_dir = os.path.join(self.profile_path, "user_data")

        # Auto-save and state tracking
        self.auto_save_interval = 300  # seconds
        self.last_auto_save = None
        self._auto_save_task = None
        self._last_state_signature = None
        self._closing = False

        # Ensure directories exist
        os.makedirs(self.screenshots_dir, exist_ok=True)
        os.makedirs(self.profile_path, exist_ok=True)
        os.makedirs(self.user_data_dir, exist_ok=True)

        if self.enable_stealth:
            print("⚠️ Stealth mode requested but not implemented in this version")
    
    def _state_signature(self, storage_state: Dict[str, Any], current_url: Optional[str], open_pages: List[str]) -> str:
        """Create a deterministic signature for current state to avoid redundant writes."""
        try:
            raw = json.dumps({
                'storage_state': storage_state,
                'current_url': current_url,
                'open_pages': open_pages
            }, sort_keys=True, separators=(",", ":")).encode('utf-8')
            return hashlib.sha256(raw).hexdigest()
        except Exception:
            return "unknown"

    async def save_browser_state(self, force: bool = False) -> Dict[str, Any]:
        """
        Save current browser state including cookies, local storage, and session storage.
        
        Returns:
            Dict with save status
        """
        if not self.context or not self.page:
            return {
                'status': 'error',
                'message': 'Browser not initialized. Cannot save state.'
            }
        
        try:
            # Get all storage states (cookies, local storage, session storage)
            storage_state = await self.context.storage_state()
            
            # Get current page URL for restoration
            current_url = self.page.url if self.page else None
            open_pages = [p.url for p in self.context.pages if getattr(p, 'url', None)]

            # Compute signature to prevent redundant writes
            signature = self._state_signature(storage_state, current_url, open_pages)
            if not force and signature == self._last_state_signature:
                return {
                    'status': 'skipped',
                    'reason': 'unchanged',
                    'message': 'State unchanged; save skipped.'
                }
            
            # Prepare state data
            state_data = {
                'storage_state': storage_state,
                'current_url': current_url,
                'profile_name': self.profile_name,
                'last_saved': datetime.now().isoformat(),
                'session_id': self.session_id,
                'open_pages': open_pages,
                'schema_version': SCHEMA_VERSION
            }
            
            # Save to state file
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(state_data, f, indent=2)
            self._last_state_signature = signature
            self.last_auto_save = datetime.now()
            
            return {
                'status': 'success',
                'profile_name': self.profile_name,
                'state_file': self.state_file,
                'current_url': current_url,
                'pages': open_pages,
                'message': f'Browser state saved to profile: {self.profile_name}'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Failed to save browser state: {str(e)}'
            }
    
    async def load_browser_state(self) -> Dict[str, Any]:
        """
        Load previously saved browser state if it exists.
        
        Returns:
            Dict with load status and restored data
        """
        if not os.path.exists(self.state_file):
            return {
                'status': 'info',
                'message': f'No saved state found for profile: {self.profile_name}'
            }
        
        try:
            with open(self.state_file, 'r', encoding='utf-8') as f:
                state_data = json.load(f)
            
            # Validate state data
            if 'storage_state' not in state_data:
                return {
                    'status': 'error',
                    'message': 'Invalid state file format'
                }
            # Basic schema compatibility check
            if state_data.get('schema_version', 0) > SCHEMA_VERSION:
                state_data['upgrade_warning'] = 'State file schema is newer than runtime schema version.'
            
            return {
                'status': 'success',
                'state_data': state_data,
                'profile_name': state_data.get('profile_name'),
                'last_saved': state_data.get('last_saved'),
                'current_url': state_data.get('current_url'),
                'open_pages': state_data.get('open_pages', []),
                'message': f'Browser state loaded from profile: {self.profile_name}'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Failed to load browser state: {str(e)}'
            }
    
    def list_profiles(self) -> Dict[str, Any]:
        """
        List all available browser profiles.
        
        Returns:
            Dict with profiles list
        """
        try:
            if not os.path.exists(self.profiles_dir):
                return {
                    'status': 'success',
                    'profiles': [],
                    'message': 'No profiles directory found'
                }
            
            profiles = []
            for item in os.listdir(self.profiles_dir):
                profile_path = os.path.join(self.profiles_dir, item)
                if os.path.isdir(profile_path):
                    state_file = os.path.join(profile_path, "browser_state.json")
                    has_state = os.path.exists(state_file)
                    
                    profile_info = {
                        'name': item,
                        'path': profile_path,
                        'has_saved_state': has_state
                    }
                    
                    if has_state:
                        try:
                            with open(state_file, 'r', encoding='utf-8') as f:
                                state_data = json.load(f)
                            profile_info['last_saved'] = state_data.get('last_saved')
                            profile_info['last_url'] = state_data.get('current_url')
                        except:
                            pass
                    
                    profiles.append(profile_info)
            
            return {
                'status': 'success',
                'profiles': profiles,
                'current_profile': self.profile_name,
                'message': f'Found {len(profiles)} profiles'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Failed to list profiles: {str(e)}'
            }
    
    def delete_profile(self, profile_name: str, confirm: bool = False) -> Dict[str, Any]:
        """
        Delete a browser profile and all its data.
        
        Args:
            profile_name: Name of the profile to delete
            confirm: Safety confirmation flag
        
        Returns:
            Dict with deletion status
        """
        if not confirm:
            return {
                'status': 'error',
                'message': 'Profile deletion requires confirmation. Set confirm=True to proceed.'
            }
        
        if profile_name == self.profile_name:
            return {
                'status': 'error',
                'message': 'Cannot delete currently active profile. Switch to another profile first.'
            }
        
        profile_path = os.path.join(self.profiles_dir, profile_name)
        
        if not os.path.exists(profile_path):
            return {
                'status': 'error',
                'message': f'Profile not found: {profile_name}'
            }
        
        try:
            shutil.rmtree(profile_path)
            
            return {
                'status': 'success',
                'deleted_profile': profile_name,
                'message': f'Profile deleted successfully: {profile_name}'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Failed to delete profile {profile_name}: {str(e)}'
            }
    
    async def initialize_browser(self, headless: bool = False, browser_type: str = "chromium", 
                                load_state: bool = True, restore_last_url: bool = True, 
                                use_real_chrome: bool = False, chrome_debug_port: int = 9222) -> Dict[str, Any]:
        """
        Initialize browser session with Playwright and optionally load saved state.
        
        Args:
            headless: Whether to run browser in headless mode
            browser_type: Type of browser (chromium, firefox, webkit)
            load_state: Whether to load saved state (cookies, storage, etc.)
            restore_last_url: Whether to navigate to the last saved URL
            use_real_chrome: Whether to connect to existing Chrome with debug port (BEST for bot detection bypass)
            chrome_debug_port: Port for Chrome debug connection (default 9222)
        
        Returns:
            Dict with initialization status and session info
        """
        try:
            # Check if browser is already initialized
            if self.browser and self.page:
                return {
                    'status': 'success',
                    'session_id': self.session_id,
                    'browser_type': browser_type,
                    'headless': headless,
                    'profile_name': self.profile_name,
                    'message': f'Browser already initialized with session ID: {self.session_id}'
                }
            
            # Close existing browser if partially initialized
            if self.browser:
                await self.close_browser()
            
            self.playwright = await async_playwright().start()

            # REAL CHROME CONNECTION - Best for bot detection bypass
            if use_real_chrome:
                try:
                    print(f"🔗 Connecting to real Chrome on port {chrome_debug_port}...")
                    
                    # Connect to existing Chrome instance via CDP
                    self.browser = await self.playwright.chromium.connect_over_cdp(f"http://localhost:{chrome_debug_port}")
                    
                    # Get existing context or create new one
                    contexts = self.browser.contexts
                    if contexts:
                        self.context = contexts[0]
                        print(f"✅ Connected to existing Chrome context with {len(self.context.pages)} pages")
                        
                        # Get existing page or create new one, preferring existing pages
                        pages = self.context.pages
                        if pages:
                            # Use the first existing page (don't create new)
                            self.page = pages[0]
                            print(f"🔗 Using existing page: {self.page.url}")
                        else:
                            self.page = await self.context.new_page()
                            print("📄 Created new page in existing context")
                    else:
                        self.context = await self.browser.new_context()
                        self.page = await self.context.new_page()
                        print("✅ Created new context and page in existing Chrome")
                    
                    # Generate session ID
                    import uuid
                    self.session_id = str(uuid.uuid4())[:8]
                    
                    print("🎉 Successfully connected to real Chrome - MAXIMUM bot detection bypass!")
                    
                    return {
                        'status': 'success',
                        'session_id': self.session_id,
                        'browser_type': 'real_chrome',
                        'headless': False,
                        'profile_name': self.profile_name,
                        'message': f'Connected to real Chrome on port {chrome_debug_port} - Best bot detection bypass!'
                    }
                    
                except Exception as e:
                    print(f"❌ Failed to connect to real Chrome: {e}")
                    print("� Auto-starting Chrome with working configuration...")
                    
                    # AUTO-FALLBACK: Start Chrome with working configuration
                    try:
                        print("🚀 Auto-starting Chrome with persistent profile and working bot detection flags...")
                        
                        # Import the best-of-both-worlds Chrome startup
                        from .best_of_both_worlds_chrome import start_chrome_with_persistent_profile_and_working_flags
                        success = start_chrome_with_persistent_profile_and_working_flags()
                        
                        if success:
                            import asyncio
                            await asyncio.sleep(3)  # Give Chrome time to start
                            
                            # Try connecting to the Chrome instance we just started
                            self.browser = await self.playwright.chromium.connect_over_cdp(f"http://localhost:{chrome_debug_port}")
                            
                            # Get existing contexts from the Chrome we just started
                            contexts = self.browser.contexts
                            if contexts:
                                self.context = contexts[0]
                                print(f"✅ Connected to auto-started Chrome context with {len(self.context.pages)} pages")
                                
                                # Get existing page or create new one, preferring existing pages
                                pages = self.context.pages
                                if pages:
                                    # Use the first existing page (don't create new)
                                    self.page = pages[0]
                                    print(f"🔗 Using existing page in auto-started Chrome: {self.page.url}")
                                else:
                                    self.page = await self.context.new_page()
                                    print("📄 Created new page in auto-started Chrome context")
                            else:
                                self.context = await self.browser.new_context()
                                self.page = await self.context.new_page()
                                print("✅ Created new context and page in auto-started Chrome")
                            
                            import uuid
                            self.session_id = str(uuid.uuid4())[:8]
                            
                            print("✅ Auto-started Chrome with persistent profile and connected successfully!")
                            
                            return {
                                'status': 'success',
                                'session_id': self.session_id,
                                'browser_type': 'real_chrome_auto_started_persistent',
                                'headless': False,
                                'profile_name': self.profile_name,
                                'message': f'Auto-started Chrome with persistent profile on port {chrome_debug_port}'
                            }
                        else:
                            raise Exception("Failed to auto-start Chrome with persistent profile")
                            
                    except Exception as fallback_error:
                        print(f"❌ Auto-start also failed: {fallback_error}")
                        return {
                            'status': 'error',
                            'error': str(fallback_error),
                            'message': f'Failed to connect to real Chrome and auto-start also failed. Real Chrome required but unavailable.'
                        }

            # FALLBACK: Launch new Playwright browser instance (only if NOT using real Chrome)
            if use_real_chrome:
                # If we get here with use_real_chrome=True, something went wrong above
                return {
                    'status': 'error', 
                    'message': 'Real Chrome was requested but could not be started or connected to.'
                }
                
            launch_args = [
                '--no-first-run',
                '--no-default-browser-check',
                '--disable-backgrounding-occluded-windows',
                '--disable-renderer-backgrounding',
                '--disable-features=TranslateUI',
                '--disable-background-timer-throttling'
            ]

            saved_state = None
            last_url = None
            open_pages_saved: List[str] = []
            if load_state:
                state_result = await self.load_browser_state()
                if state_result['status'] == 'success':
                    saved_state = state_result['state_data']['storage_state']
                    last_url = state_result['state_data'].get('current_url')
                    open_pages_saved = state_result['state_data'].get('open_pages', [])

            if browser_type == 'chromium':
                # Persistent context gives us real disk-backed profile (cookies, history, etc.)
                context_kwargs = {
                    'headless': headless,
                    'args': launch_args,
                }
                # storage_state param not accepted in launch_persistent_context; we manually apply cookies afterwards if needed
                self.context = await self.playwright.chromium.launch_persistent_context(self.user_data_dir, **context_kwargs)
                self.browser = self.context.browser
            elif browser_type == 'firefox':
                # Firefox lacks launch_persistent_context; fallback to legacy approach
                self.browser = await self.playwright.firefox.launch(headless=headless, args=launch_args)
                context_options = {'viewport': {'width': 1280, 'height': 720}}
                if saved_state:
                    context_options['storage_state'] = saved_state
                self.context = await self.browser.new_context(**context_options)
            elif browser_type == 'webkit':
                self.browser = await self.playwright.webkit.launch(headless=headless, args=launch_args)
                context_options = {'viewport': {'width': 1280, 'height': 720}}
                if saved_state:
                    context_options['storage_state'] = saved_state
                self.context = await self.browser.new_context(**context_options)
            else:
                raise ValueError(f"Unsupported browser type: {browser_type}")
            
            # Ensure at least one page exists
            if self.context.pages:
                self.page = self.context.pages[0]
            else:
                self.page = await self.context.new_page()
            self.session_id = f"browser_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Optionally restore last URL
            restored_url = None
            if restore_last_url and last_url:
                with suppress(Exception):
                    await self.page.goto(last_url, wait_until='domcontentloaded')
                    restored_url = last_url

            # Restore additional saved open pages (simple approach; skip first already loaded)
            if open_pages_saved and len(open_pages_saved) > 1:
                for url in open_pages_saved[1:5]:  # limit to first 4 additional tabs for safety
                    with suppress(Exception):
                        await self.context.new_page()
                        await self.context.pages[-1].goto(url, wait_until='domcontentloaded')

            # Start auto-save loop
            if not self._auto_save_task:
                self._auto_save_task = asyncio.create_task(self._auto_save_loop())
            
            return {
                'status': 'success',
                'session_id': self.session_id,
                'browser_type': browser_type,
                'headless': headless,
                'profile_name': self.profile_name,
                'state_loaded': bool(saved_state),
                'restored_url': restored_url,
                'message': f'Browser initialized successfully with session ID: {self.session_id}'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Failed to initialize browser: {str(e)}'
            }
    
    async def navigate_to_url(self, url: str, wait_for_load: bool = True) -> Dict[str, Any]:
        """
        Navigate to a specific URL.
        
        Args:
            url: Target URL to navigate to
            wait_for_load: Whether to wait for page load completion
        
        Returns:
            Dict with navigation status and page info
        """
        if not self.page:
            return {
                'status': 'error',
                'message': 'Browser not initialized. Call initialize_browser() first.'
            }
        
        try:
            # Navigate to URL
            response = await self.page.goto(url, wait_until='domcontentloaded' if wait_for_load else 'commit')
            
            # Wait a bit more for dynamic content (reduced from 2000ms to 1000ms)
            if wait_for_load:
                await self.page.wait_for_timeout(1000)
            
            # Get page info
            title = await self.page.title()
            current_url = self.page.url
            
            return {
                'status': 'success',
                'url': current_url,
                'title': title,
                'response_status': response.status if response else None,
                'message': f'Successfully navigated to {current_url}'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Failed to navigate to {url}: {str(e)}'
            }
    
    async def find_element(self, selector: str, timeout: int = 5000) -> Dict[str, Any]:
        """
        Find an element on the page using CSS selector.
        
        Args:
            selector: CSS selector for the element
            timeout: Timeout in milliseconds
        
        Returns:
            Dict with element status and info
        """
        if not self.page:
            return {
                'status': 'error',
                'message': 'Browser not initialized.'
            }
        
        try:
            # Wait for element to be visible
            element = await self.page.wait_for_selector(selector, timeout=timeout)
            
            if element:
                # Get element properties
                is_visible = await element.is_visible()
                is_enabled = await element.is_enabled()
                text_content = await element.text_content()
                
                return {
                    'status': 'success',
                    'selector': selector,
                    'found': True,
                    'visible': is_visible,
                    'enabled': is_enabled,
                    'text': text_content,
                    'message': f'Element found: {selector}'
                }
            else:
                return {
                    'status': 'error',
                    'selector': selector,
                    'found': False,
                    'message': f'Element not found: {selector}'
                }
                
        except Exception as e:
            return {
                'status': 'error',
                'selector': selector,
                'error': str(e),
                'message': f'Error finding element {selector}: {str(e)}'
            }
    
    async def click_element(self, selector: str, timeout: int = 5000) -> Dict[str, Any]:
        """
        Click an element on the page with enhanced handling for compound selectors.
        
        Args:
            selector: CSS selector for the element to click
            timeout: Timeout in milliseconds
        
        Returns:
            Dict with click status
        """
        if not self.page:
            return {
                'status': 'error',
                'message': 'Browser not initialized.'
            }
        
        try:
            # Use .first for better handling of compound selectors that may match multiple elements
            # Wait for element to be available and stable before clicking
            await self.page.wait_for_selector(selector, timeout=timeout)
            
            locator = self.page.locator(selector).first
            await locator.scroll_into_view_if_needed()
            await locator.click(timeout=timeout)
            
            # Wait a moment for any resulting page changes (reduced from 1000ms to 500ms)
            await self.page.wait_for_timeout(500)
            
            return {
                'status': 'success',
                'selector': selector,
                'message': f'Successfully clicked element: {selector}'
            }
            
        except Exception as e:
            # Try with force=True for overlay interference
            try:
                locator = self.page.locator(selector).first
                await locator.scroll_into_view_if_needed()
                await locator.click(timeout=timeout, force=True)
                
                await self.page.wait_for_timeout(500)  # Reduced from 1000ms to 500ms
                
                return {
                    'status': 'success',
                    'selector': selector,
                    'message': f'Successfully clicked element with force: {selector}'
                }
            except Exception as force_error:
                return {
                    'status': 'error',
                    'selector': selector,
                    'error': str(force_error),
                    'original_error': str(e),
                    'message': f'Failed to click element {selector}: {str(force_error)}'
                }
    
    async def type_text(self, selector: str, text: str, clear_first: bool = True, press_enter: bool = False) -> Dict[str, Any]:
        """
        Type text into an input element.
        
        Args:
            selector: CSS selector for the input element
            text: Text to type
            clear_first: Whether to clear existing text first
            press_enter: Whether to press Enter after typing (useful for dismissing autocomplete dropdowns)
        
        Returns:
            Dict with typing status
        """
        if not self.page:
            return {
                'status': 'error',
                'message': 'Browser not initialized.'
            }
        
        try:
            # Wait for element
            await self.page.wait_for_selector(selector, timeout=5000)
            
            # Clear and type
            if clear_first:
                await self.page.fill(selector, text)
            else:
                await self.page.type(selector, text)
            
            # Press Enter if requested (helps dismiss autocomplete dropdowns)
            if press_enter:
                await self.page.press(selector, 'Enter')
                print(f"🔑 Pressed Enter after typing to dismiss autocomplete dropdown")
            
            return {
                'status': 'success',
                'selector': selector,
                'text': text,
                'press_enter': press_enter,
                'message': f'Successfully typed text into {selector}' + (' and pressed Enter' if press_enter else '')
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'selector': selector,
                'error': str(e),
                'message': f'Failed to type into {selector}: {str(e)}'
            }

    async def press_key(self, key: str, selector: Optional[str] = None, delay_ms: int = 0) -> Dict[str, Any]:
        """
        Press a keyboard key, optionally focusing a selector first.
        
        Args:
            key: Key name acceptable by Playwright (e.g. 'Enter', 'Tab', 'ArrowDown')
            selector: Optional selector to focus before pressing
            delay_ms: Optional small delay before press (human-like)
        """
        if not self.page:
            return {'status': 'error', 'message': 'Browser not initialized.'}
        try:
            if selector:
                await self.page.wait_for_selector(selector, timeout=5000)
                await self.page.focus(selector)
            if delay_ms:
                await self.page.wait_for_timeout(delay_ms)
            await self.page.keyboard.press(key)
            return {
                'status': 'success',
                'key': key,
                'selector': selector,
                'message': f'Pressed key: {key}' + (f' after focusing {selector}' if selector else '')
            }
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'message': f'Failed to press key {key}: {e}'}
    
    async def take_screenshot(self, filename: Optional[str] = None, full_page: bool = False) -> Dict[str, Any]:
        """
        Take a screenshot of the current page.
        
        Args:
            filename: Optional filename for the screenshot
            full_page: Whether to capture the full page or just viewport
        
        Returns:
            Dict with screenshot status and file path
        """
        if not self.page:
            return {
                'status': 'error',
                'message': 'Browser not initialized.'
            }
        
        try:
            if not filename:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"screenshot_{timestamp}.png"
            
            filepath = os.path.join(self.screenshots_dir, filename)
            
            await self.page.screenshot(path=filepath, full_page=full_page)
            
            return {
                'status': 'success',
                'filepath': filepath,
                'filename': filename,
                'full_page': full_page,
                'message': f'Screenshot saved to {filepath}'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Failed to take screenshot: {str(e)}'
            }
    
    async def get_page_info(self) -> Dict[str, Any]:
        """
        Get current page information.
        
        Returns:
            Dict with page details
        """
        if not self.page:
            return {
                'status': 'error',
                'message': 'Browser not initialized.'
            }
        
        try:
            title = await self.page.title()
            url = self.page.url
            
            return {
                'status': 'success',
                'title': title,
                'url': url,
                'session_id': self.session_id
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Failed to get page info: {str(e)}'
            }
    
    async def close_browser(self, save_state: bool = True) -> Dict[str, Any]:
        """
        Close the browser session and cleanup resources.
        Optionally saves browser state before closing.
        
        Args:
            save_state: Whether to save browser state before closing
        
        Returns:
            Dict with cleanup status
        """
        try:
            self._closing = True
            # Cancel auto-save loop first
            if self._auto_save_task and not self._auto_save_task.cancelled():
                self._auto_save_task.cancel()
                try:
                    await self._auto_save_task
                except asyncio.CancelledError:
                    pass  # Expected when cancelling
                except Exception as e:
                    print(f"Warning: Auto-save task cleanup error: {e}")
                self._auto_save_task = None
            # Save state before closing if requested and possible
            state_saved = False
            if save_state and self.context and self.page:
                try:
                    save_result = await self.save_browser_state(force=True)
                    state_saved = save_result['status'] == 'success'
                except Exception as e:
                    print(f"Warning: Could not save browser state: {e}")
            
            if self.page:
                await self.page.close()
            if self.context:
                await self.context.close()
            if self.browser:
                await self.browser.close()
            if self.playwright:
                await self.playwright.stop()
            
            # Reset instance variables
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            self._last_state_signature = None
            self._closing = False
            
            return {
                'status': 'success',
                'state_saved': state_saved,
                'profile_name': self.profile_name,
                'message': f'Browser session closed successfully{"" if not save_state else " with state saved" if state_saved else " (state save failed)"}'
            }
            
        except Exception as e:
            return {
                'status': 'error',
                'error': str(e),
                'message': f'Error closing browser: {str(e)}'
            }

    async def clear_cookies(self) -> Dict[str, Any]:
        if not self.context:
            return {'status': 'error', 'message': 'Browser not initialized.'}
        try:
            await self.context.clear_cookies()
            return {'status': 'success', 'message': 'Cookies cleared.'}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'message': f'Failed to clear cookies: {e}'}

    async def clear_storage(self, scopes: Optional[List[str]] = None) -> Dict[str, Any]:
        if not self.context:
            return {'status': 'error', 'message': 'Browser not initialized.'}
        if scopes is None:
            scopes = ['local', 'session']
        try:
            for p in self.context.pages:
                with suppress(Exception):
                    await p.evaluate(
                        "(scopes) => { if (scopes.includes('local')) localStorage.clear(); if (scopes.includes('session')) sessionStorage.clear(); }",
                        scopes
                    )
            return {'status': 'success', 'scopes': scopes, 'message': 'Storage cleared.'}
        except Exception as e:
            return {'status': 'error', 'error': str(e), 'message': f'Failed to clear storage: {e}'}

    def is_active(self) -> bool:
        return self.context is not None and not self._closing

    async def _auto_save_loop(self):
        """Periodic auto-save of browser state (debounced)."""
        try:
            while True:
                await asyncio.sleep(self.auto_save_interval)
                if self.context and self.page:
                    with suppress(Exception):
                        await self.save_browser_state()
        except asyncio.CancelledError:
            return

# Async wrapper function for use with ToolManager
async def run_browser_action(action: str, profile_name: str = "default", **kwargs) -> Dict[str, Any]:
    """
    Wrapper function to run browser actions with persistent profile support.
    This will be called by the ToolManager.
    
    Args:
        action: The browser action to perform
        profile_name: Browser profile name for persistent state
        **kwargs: Additional arguments for the action
    """
    # Reuse existing tool instance if available
    browser_tool = _BROWSER_TOOL_REGISTRY.get(profile_name)
    if browser_tool is None or not browser_tool.is_active():
        browser_tool = BrowserEngineTool(profile_name=profile_name)
        _BROWSER_TOOL_REGISTRY[profile_name] = browser_tool
    
    try:
        if action == "initialize":
            return await browser_tool.initialize_browser(**kwargs)
        elif action == "navigate":
            return await browser_tool.navigate_to_url(**kwargs)
        elif action == "find_element":
            return await browser_tool.find_element(**kwargs)
        elif action == "click":
            return await browser_tool.click_element(**kwargs)
        elif action == "type":
            return await browser_tool.type_text(**kwargs)
        elif action == "press_key":
            return await browser_tool.press_key(**kwargs)
        elif action == "screenshot":
            return await browser_tool.take_screenshot(**kwargs)
        elif action == "page_info":
            return await browser_tool.get_page_info()
        elif action == "close":
            return await browser_tool.close_browser(**kwargs)
        elif action == "save_state":
            return await browser_tool.save_browser_state(force=kwargs.get('force', False))
        elif action == "load_state":
            return await browser_tool.load_browser_state()
        elif action == "list_profiles":
            return browser_tool.list_profiles()
        elif action == "delete_profile":
            return browser_tool.delete_profile(**kwargs)
        elif action == "clear_cookies":
            return await browser_tool.clear_cookies()
        elif action == "clear_storage":
            return await browser_tool.clear_storage(**kwargs)
        else:
            return {
                'status': 'error',
                'message': f'Unknown action: {action}'
            }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'message': f'Error executing browser action {action}: {str(e)}'
        }