from typing import List, Tuple
from .models import CommandBatch, Evidence
from . import dom_processor as _dp
from .browser_engine_tool import BrowserEngineTool
from datetime import datetime

class BrowserController:
    def __init__(self, profile_name: str = "default", headless: bool = False, browser_type: str = "chromium"):
        self._engine = BrowserEngineTool(profile_name=profile_name)
        self._profile_name = profile_name
        self._headless = headless
        self._browser_type = browser_type

    async def initialize(self) -> None:
        res = await self._engine.initialize_browser(headless=self._headless, browser_type=self._browser_type)
        if res.get("status") != "success":
            raise RuntimeError(f"Browser init failed: {res}")

    async def navigate(self, url: str) -> None:
        res = await self._engine.navigate_to_url(url)
        if res.get("status") != "success":
            raise RuntimeError(f"Navigate failed: {res}")

    async def get_current_dom(self) -> Tuple[str, str]:
        if not self._engine.page:
            raise RuntimeError("Browser not initialized")
        
        # Wait for dynamic content to load (3 seconds max)
        try:
            await self._engine.page.wait_for_selector('[data-qa-group-name]', timeout=3000)  # 3s for bowl elements
        except:
            # If selector not found, continue anyway (don't fail the whole operation)
            pass
        
        # Wait for network to be idle (3 seconds max)
        try:
            await self._engine.page.wait_for_load_state('networkidle', timeout=3000)  # 3s for AJAX completion
        except:
            # If network doesn't settle, continue anyway
            pass
        
        html = await self._engine.page.content()
        title = await self._engine.page.title()
        return html, title

    async def execute_action_batch(self, batch: CommandBatch) -> Evidence:
        # Capture before signature for reference
        before_html, _ = await self.get_current_dom()
        before_sig = _dp.page_signature(_dp.compress_dom(before_html))
        errors: List[str] = []
        used_selector = None
        fallback_used = False

        start = datetime.now()
        executed_commands = 0  # Track actually executed commands
        
        for i, cmd in enumerate(batch.commands):
            try:
                if cmd.type == "navigate" and cmd.url:
                    await self._engine.navigate_to_url(cmd.url)
                    executed_commands += 1
                elif cmd.type == "click" and cmd.selector:
                    if used_selector is None:
                        used_selector = cmd.selector
                    # Execute click and check result
                    result = await self._engine.click_element(cmd.selector)
                    if result.get('status') == 'success':
                        executed_commands += 1
                    else:
                        errors.append(f"Click failed on '{cmd.selector}': {result.get('message', 'Unknown error')}")
                elif cmd.type == "type" and cmd.selector is not None:
                    # Execute type and check result
                    result = await self._engine.type_text(cmd.selector, cmd.text or "", clear_first=True, press_enter=False)
                    if result.get('status') == 'success':
                        executed_commands += 1
                    else:
                        errors.append(f"Type failed on '{cmd.selector}': {result.get('message', 'Unknown error')}")
                elif cmd.type == "press" and cmd.key:
                    result = await self._engine.press_key(cmd.key, cmd.selector)
                    if result.get('status') == 'success':
                        executed_commands += 1
                    else:
                        errors.append(f"Press key failed: {result.get('message', 'Unknown error')}")
                else:
                    errors.append(f"Unsupported or malformed command: {cmd}")
            except Exception as e:
                errors.append(str(e))
        # small debounce for DOM to settle
        if self._engine.page:
            await self._engine.page.wait_for_timeout(400)
        duration_ms = int((datetime.now() - start).total_seconds() * 1000)

        after_html, _ = await self.get_current_dom()
        after_sig = _dp.page_signature(_dp.compress_dom(after_html))
        
        # Enhanced success logic: DOM must change OR commands must execute successfully
        dom_changed = after_sig != before_sig
        commands_executed_successfully = executed_commands > 0 and len(errors) == 0
        
        # Success requires either DOM change OR successful command execution
        # But if DOM doesn't change and we tried to interact with elements, that's likely a failure
        if dom_changed:
            success = True  # DOM changed, something worked
        elif executed_commands > 0 and len(errors) == 0:
            # Commands executed without errors, but DOM didn't change
            # This might be OK for some actions (like pressing keys), but suspicious for clicks/types
            has_interaction_commands = any(cmd.type in ['click', 'type'] for cmd in batch.commands)
            if has_interaction_commands:
                # Interaction commands should usually change DOM
                success = False
                errors.append("Interaction commands executed but DOM unchanged - likely failed to find elements")
            else:
                success = True  # Non-interaction commands (navigate, press keys)
        else:
            success = False  # Either no commands executed or there were errors

        evidence = Evidence(
            success=success,
            dom_after_sig=after_sig,
            regions_after=[],
            findings={},
            used_selector=used_selector,
            fallback_used=fallback_used,
            timing_ms=duration_ms,
            errors=errors,
        )
        return evidence

    async def close(self, save_state: bool = True) -> None:
        await self._engine.close_browser(save_state=save_state)
