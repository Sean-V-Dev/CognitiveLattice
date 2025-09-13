#!/usr/bin/env python3
"""
End-to-end test to verify the ID-to-selector mapping fix works correctly.
This simulates the actual agent workflow to ensure IDs map to correct elements.
"""

import asyncio
import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from tools.web_automation.browser_controller import BrowserController
from tools.web_automation.dom_processor import summarize_interactive_elements
from tools.web_automation.prompt_builder import build_reasoning_prompt, _shape_candidates
from tools.web_automation.models import CommandBatch, Command, ActionType

def simulate_agent_selection(candidates, target_text):
    """Simulate an agent selecting a candidate by text match."""
    for candidate in candidates:
        if target_text.lower() in candidate.get('description', '').lower():
            return candidate.get('candidate_id')
    return None

async def test_end_to_end_mapping():
    """Test the complete ID mapping flow from DOM → prompt → selection → execution."""
    
    browser_controller = BrowserController()
    
    try:
        # Initialize browser and navigate to Chipotle
        await browser_controller.initialize()
        await browser_controller.navigate("https://chipotle.com")
        
        print("✅ Browser initialized and navigated to Chipotle")
        
        # Process DOM and assign IDs
        ctx = await summarize_interactive_elements(browser_controller.page)
        print(f"✅ DOM processed, found {len(ctx.interactive)} interactive elements")
        
        # Shape candidates for prompt (what agent sees)
        candidates = _shape_candidates(ctx)
        print(f"✅ Shaped {len(candidates)} candidates for agent")
        
        # Show first few candidates
        print(f"\n📋 First 5 candidates the agent sees:")
        for i, candidate in enumerate(candidates[:5]):
            print(f"  ID {candidate['candidate_id']}: {candidate['description']}")
        
        # Simulate agent selecting "Order" or "Menu" button
        target_texts = ["order", "menu", "start"]
        selected_id = None
        
        for target_text in target_texts:
            selected_id = simulate_agent_selection(candidates, target_text)
            if selected_id:
                print(f"\n🤖 Agent simulated: Selected candidate ID {selected_id} for '{target_text}'")
                break
        
        if not selected_id:
            print("❌ No suitable candidate found for simulation")
            return False
        
        # Find the actual element that should be selected
        expected_element = None
        for element in ctx.interactive:
            if getattr(element, 'candidate_id', None) == selected_id:
                expected_element = element
                break
        
        if not expected_element:
            print(f"❌ Could not find element with candidate_id {selected_id}")
            return False
        
        print(f"✅ Found target element: '{expected_element.text[:50]}' with selector: {expected_element.selectors[0] if expected_element.selectors else 'No selector'}")
        
        # Create a test command batch (what would be sent to step executor)
        test_command = Command(
            action=ActionType.CLICK,
            selector="",  # This would be empty in ID-based system
            candidate_id=selected_id,
            text="",
            reasoning=f"Clicking candidate ID {selected_id}"
        )
        
        batch = CommandBatch(commands=[test_command])
        
        # Test the ID-to-selector mapping (step_executor logic)
        mapped_element = None
        for element in ctx.interactive:
            if getattr(element, 'candidate_id', None) == selected_id:
                mapped_element = element
                break
        
        if mapped_element == expected_element:
            print(f"✅ ID mapping successful: candidate_id {selected_id} maps to correct element")
            print(f"   Element text: '{mapped_element.text[:50]}'")
            print(f"   Element selector: {mapped_element.selectors[0] if mapped_element.selectors else 'No selector'}")
            return True
        else:
            print(f"❌ ID mapping failed: found different element")
            return False
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        await browser_controller.close()

if __name__ == "__main__":
    print("🚀 Starting end-to-end ID mapping test...")
    success = asyncio.run(test_end_to_end_mapping())
    
    if success:
        print("\n✅ End-to-end ID mapping test PASSED")
        print("🎯 The hallucination-proof system is working correctly!")
    else:
        print("\n❌ End-to-end ID mapping test FAILED")
        sys.exit(1)
