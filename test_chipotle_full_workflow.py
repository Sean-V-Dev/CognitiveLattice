#!/usr/bin/env python3
"""
Full Chipotle test with unfiltered AI decision making
Goal: Navigate to Chipotle, dismiss popups, enter ZIP 45305, select nearest location
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.cognitive_lattice_web_agent import CognitiveLatticeWebAgent
from core.cognitive_lattice import CognitiveLattice
from core.external_api_client import ExternalAPIClient

async def test_chipotle_location_workflow():
    """Full test: Navigate, dismiss popups, enter location, select store"""
    
    print("🌯 Chipotle Location Selection Test (AI Chooses Everything)")
    print("="*65)
    
    # Initialize components
    try:
        external_client = ExternalAPIClient()
        print("✅ Using external API client for smart decisions")
    except:
        external_client = None
        print("⚠️ Using internal LLM fallback")
    
    lattice = CognitiveLattice()
    agent = CognitiveLatticeWebAgent(
        external_client=external_client,
        cognitive_lattice=lattice
    )
    
    try:
        print("\n📍 STEP 1: Navigate to Chipotle.com")
        print("-" * 40)
        
        # Create execution plan and run it using the enhanced agent
        high_level_goal = "Navigate to chipotle.com, find a way to enter location ZIP code 45305, and select the nearest Chipotle location"
        target_url = "https://www.chipotle.com"
        
        print(f"🧠 Creating execution plan...")
        execution_plan = await agent.create_execution_plan(high_level_goal, target_url)
        
        print(f"📋 Plan created with {len(execution_plan.get('steps', []))} steps")
        for i, step in enumerate(execution_plan.get('steps', []), 1):
            print(f"  {i}. {step.get('description', 'Unknown step')}")
        
        print(f"\n⚡ Executing plan with monitoring...")
        result = await agent.execute_plan_with_monitoring(execution_plan)
        
        print(f"\n🎯 WORKFLOW RESULT:")
        print(f"Success: {result.get('success', False)}")
        print(f"Final URL: {result.get('final_url', 'Unknown')}")
        print(f"Steps completed: {len(result.get('step_results', []))}")
        
        # Show each step taken by the AI
        print(f"\n📋 DETAILED STEP BREAKDOWN:")
        print("=" * 50)
        
        step_results = result.get('step_results', [])
        for i, step in enumerate(step_results, 1):
            step_goal = step.get('step_goal', 'Unknown goal')
            success = step.get('success', False)
            actions = step.get('actions_executed', [])
            verification = step.get('verification', {})
            
            status_icon = "✅" if success else "❌"
            print(f"\n{status_icon} STEP {i}: {step_goal}")
            
            # Show what actions were taken
            for action in actions:
                action_type = action.get('type', 'unknown')
                selector = action.get('selector', 'none')
                text = action.get('text', '')
                status = action.get('exec_status', 'unknown')
                
                print(f"   → {action_type.upper()}: {selector}")
                if text:
                    print(f"     Text entered: '{text}'")
                print(f"     Status: {status}")
            
            # Show verification results
            achieved = verification.get('achieved', False)
            confidence = verification.get('confidence', 0)
            evidence = verification.get('evidence', '')
            
            print(f"   Verification: {achieved} (confidence: {confidence:.2f})")
            if evidence:
                print(f"   Evidence: {evidence}")
        
        # Check final state to see if we successfully got location selection
        print(f"\n🔍 FINAL STATE ANALYSIS:")
        print("-" * 30)
        
        final_obs = await agent.observe()
        final_url = final_obs.get('url', '')
        final_title = final_obs.get('title', '')
        interactive_elements = final_obs.get('interactive_summary', [])
        
        print(f"Final URL: {final_url}")
        print(f"Final Title: {final_title}")
        print(f"Interactive elements available: {len(interactive_elements)}")
        
        # Look for location-related elements
        location_elements = []
        zip_inputs = []
        store_results = []
        
        for elem in interactive_elements:
            text = elem.get('text', '').lower()
            tag = elem.get('tag', '')
            attrs = elem.get('attrs', {})
            placeholder = attrs.get('placeholder', '').lower()
            
            # Check for ZIP input fields
            if tag == 'input' and ('zip' in placeholder or 'location' in placeholder or 'address' in placeholder):
                zip_inputs.append(elem)
            
            # Check for store/location results
            if any(keyword in text for keyword in ['store', 'location', 'chipotle', 'select', 'mile']):
                store_results.append(elem)
            
            # Check for general location elements
            if any(keyword in text or keyword in placeholder for keyword in ['location', 'find', 'store']):
                location_elements.append(elem)
        
        print(f"\nFOUND ELEMENTS:")
        print(f"  ZIP input fields: {len(zip_inputs)}")
        print(f"  Store result options: {len(store_results)}")
        print(f"  Other location elements: {len(location_elements)}")
        
        # Show ZIP inputs found
        if zip_inputs:
            print(f"\n📍 ZIP INPUT FIELDS:")
            for i, elem in enumerate(zip_inputs):
                placeholder = elem.get('attrs', {}).get('placeholder', '')
                selectors = elem.get('selectors', [])
                selector = selectors[0] if selectors else 'unknown'
                print(f"  {i+1}. {selector} - placeholder: '{placeholder}'")
        
        # Show store results found  
        if store_results:
            print(f"\n🏪 STORE RESULTS:")
            for i, elem in enumerate(store_results[:5]):  # Show top 5
                text = elem.get('text', '')[:80]
                selectors = elem.get('selectors', [])
                selector = selectors[0] if selectors else 'unknown'
                print(f"  {i+1}. {selector}: '{text}'")
        
        # Check if we successfully entered ZIP 45305
        zip_entered = False
        location_selected = False
        
        for step in step_results:
            actions = step.get('actions_executed', [])
            for action in actions:
                if action.get('type') == 'type' and '45305' in str(action.get('text', '')):
                    zip_entered = True
                if 'select' in str(action.get('selector', '')).lower() or 'location' in step.get('step_goal', '').lower():
                    location_selected = True
        
        print(f"\n🎯 WORKFLOW ANALYSIS:")
        print(f"  ZIP code 45305 entered: {'✅' if zip_entered else '❌'}")
        print(f"  Location selection attempted: {'✅' if location_selected else '❌'}")
        print(f"  Final URL suggests success: {'✅' if 'order' in final_url or 'location' in final_url else '❌'}")
        
        # Show semantic memory accumulation
        memory_path = "memory/web_semantic_cache.json"
        if os.path.exists(memory_path):
            print(f"\n💾 SEMANTIC MEMORY LEARNING:")
            with open(memory_path, 'r') as f:
                import json
                memory = json.load(f)
                chipotle_memory = memory.get('www.chipotle.com', {})
                fingerprints = chipotle_memory.get('element_fingerprints', [])
                print(f"  Stored {len(fingerprints)} successful interactions")
                
                # Show what was learned
                for i, fp in enumerate(fingerprints[-3:], 1):  # Last 3 interactions
                    label = fp.get('semantic_label', 'unknown')
                    goal = fp.get('goal_context', '')
                    confidence = fp.get('confidence', 0)
                    print(f"  {i}. {label} (confidence: {confidence:.1f}) - Goal: '{goal}'")
        
        return result
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return None
    finally:
        print(f"\n🧹 Closing browser...")
        await agent.close_browser()

if __name__ == "__main__":
    print("Starting Chipotle location selection test...")
    result = asyncio.run(test_chipotle_location_workflow())
    
    success = result is not None and result.get('success', False)
    print(f"\n🎉 TEST COMPLETED: {'✅ SUCCESS' if success else '❌ FAILED'}")
