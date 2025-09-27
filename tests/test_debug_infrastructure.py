#!/usr/bin/env python3
"""
Quick test to verify our enhanced debug infrastructure for observation steps.
This should create a run folder and save debug data for both action and observation steps.
"""

import asyncio
import sys
import os

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.cognitive_lattice_web_coordinator import CognitiveLatticeWebCoordinator
from core.external_api_client import ExternalAPIClient
from core.cognitive_lattice import CognitiveLattice

async def test_debug_infrastructure():
    """Test that our debug infrastructure works for both action and observation steps."""
    
    print("🔬 Testing Enhanced Debug Infrastructure")
    print("=" * 60)
    
    try:
        # Create external client and lattice
        external_client = ExternalAPIClient()
        lattice = CognitiveLattice()
        
        # Create coordinator with our enhanced debug system
        coordinator = CognitiveLatticeWebCoordinator(
            external_client=external_client,
            cognitive_lattice=lattice
        )
        
        print(f"✅ Coordinator created successfully")
        print(f"📁 Debug run folder: {coordinator.debug_run_folder}")
        
        # Check that debug folder was created
        if os.path.exists(coordinator.debug_run_folder):
            print(f"✅ Debug run folder exists: {coordinator.debug_run_folder}")
        else:
            print(f"❌ Debug run folder not found: {coordinator.debug_run_folder}")
            return False
            
        # Test a simple goal that would trigger both action and observation steps
        goal = "Test ordering a burrito bowl from Chipotle"
        url = "https://chipotle.com"
        
        print(f"\n🎯 Testing goal: '{goal}'")
        print(f"🌐 Target URL: {url}")
        
        # Execute just the planning phase to avoid full execution
        print("\n📋 Creating automation plan...")
        try:
            plan = await coordinator.create_web_automation_plan(goal, url)
            print(f"✅ Plan created with {len(plan)} steps:")
            for i, step in enumerate(plan, 1):
                print(f"  {i}. {step}")
                
            # Check if we have observation steps in the plan
            observation_steps = [step for step in plan if any(word in step.lower() for word in ['verify', 'confirm', 'check', 'observe', 'review'])]
            print(f"\n📊 Found {len(observation_steps)} observation-type steps:")
            for step in observation_steps:
                print(f"  - {step}")
                
            print(f"\n✅ Debug infrastructure test completed successfully!")
            print(f"📁 Debug data will be saved to: {coordinator.debug_run_folder}")
            
            return True
            
        except Exception as e:
            print(f"❌ Plan creation failed: {e}")
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_debug_infrastructure())
    print(f"\n{'🎉 TEST PASSED' if success else '💥 TEST FAILED'}")
    sys.exit(0 if success else 1)
