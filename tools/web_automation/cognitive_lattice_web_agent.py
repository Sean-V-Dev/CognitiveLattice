# tools/web_automation/cognitive_lattice_web_agent.py

from .simple_web_agent import SimpleWebAgent
from .browser_controller import BrowserController
from .models import ContextPacket

class WebAgentCore:
    """
    Thin wrapper to preserve the old coordinator's API,
    but internally use the refactored SimpleWebAgent.
    """

    def __init__(self, external_client=None, enable_stealth=True):
        self.external_client = external_client
        self.browser = BrowserController()
        self.agent = SimpleWebAgent(self.browser, external_client)

    def set_lattice(self, lattice):
        self.agent.logger.cognitive_lattice = lattice

    async def create_execution_plan(self, goal: str, url: str):
        # SimpleWebAgent can just start without a big plan; keep interface consistent
        return {"session_id": "sess-001", "goal": goal, "url": url, "steps": [{"goal": goal}]}

    async def execute_plan_with_monitoring(self, execution_plan: dict):
        results = {"success": True, "steps": []}

        # Minimal loop to mimic the old flow
        for idx, step in enumerate(execution_plan["steps"], start=1):
            ctx = ContextPacket(
                session_id=execution_plan["session_id"],
                goal=execution_plan["goal"],
                url=execution_plan["url"],
                step=idx,
                dom_snapshot="",   # will be filled by browser
                page_sig=""
            )
            evidence = await self.agent.execute_task(ctx)
            results["steps"].append(evidence)
            if evidence.get("status") == "paused":
                results["success"] = False
                break

        return results

    async def close_browser(self):
        await self.browser.close()
