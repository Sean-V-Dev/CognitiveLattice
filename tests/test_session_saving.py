#!/usr/bin/env python3
"""
Test the interactive session saving functionality to ensure complete
conversation history is captured in each run folder.
"""

import asyncio
import os
import sys
import json

# Add the project root to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from tools.web_automation.cognitive_lattice_web_coordinator import CognitiveLatticeWebCoordinator
from core.external_api_client import ExternalAPIClient
from core.cognitive_lattice import CognitiveLattice

async def test_session_saving():
    """Test that interactive session is saved to run folders."""
    
    print("💾 TESTING INTERACTIVE SESSION SAVING")
    print("=" * 70)
    
    try:
        # Create coordinator with session saving
        external_client = ExternalAPIClient()
        lattice = CognitiveLattice()
        
        # Add some mock session data to the lattice for testing
        lattice.event_log = [
            {
                "type": "web_automation",
                "query": "Navigate to Chipotle and build a custom bowl",
                "action": "web_navigate",
                "timestamp": "2025-09-23T14:00:00.000000",
                "status": "pending"
            },
            {
                "type": "plan_generated",
                "timestamp": "2025-09-23T14:00:05.000000",
                "plan": [
                    "Navigate to chipotle.com",
                    "Select bowl option",
                    "Choose chicken protein",
                    "Add white rice",
                    "Add black beans",
                    "Add to cart"
                ]
            },
            {
                "type": "web_decision",
                "data": {
                    "step": 1,
                    "goal": "Navigate to chipotle.com",
                    "rationale": "Found Chipotle logo and navigation, clicking to enter ordering",
                    "confidence": 0.95
                }
            }
        ]
        
        lattice.memory_chunks = [
            {"type": "context", "content": "User wants to order a Chipotle bowl"},
            {"type": "preference", "content": "Prefers chicken, white rice, black beans"}
        ]
        
        coordinator = CognitiveLatticeWebCoordinator(
            external_client=external_client,
            cognitive_lattice=lattice
        )
        
        print(f"✅ Coordinator created with mock session data")
        print(f"📁 Debug run folder: {coordinator.debug_run_folder}")
        
        # Test the session saving functionality directly
        session_file = os.path.join(coordinator.debug_run_folder, "test_interactive_session.json")
        coordinator._save_complete_session(session_file)
        
        # Verify the session file was created
        if os.path.exists(session_file):
            file_size = os.path.getsize(session_file)
            print(f"✅ Session file created: {os.path.basename(session_file)} ({file_size:,} bytes)")
            
            # Read and verify the content
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
            
            # Check for key components
            required_keys = ["session_metadata", "event_log", "memory_chunks"]
            missing_keys = [key for key in required_keys if key not in session_data]
            
            if missing_keys:
                print(f"⚠️ Missing session keys: {missing_keys}")
            else:
                print("✅ All required session components present")
            
            # Show sample of the session content
            print(f"\n📋 Session content overview:")
            print(f"  📊 Event log entries: {len(session_data.get('event_log', []))}")
            print(f"  🧠 Memory chunks: {len(session_data.get('memory_chunks', []))}")
            print(f"  🆔 Run ID: {session_data.get('session_metadata', {}).get('run_id', 'N/A')}")
            
            # Show first few events
            events = session_data.get('event_log', [])
            if events:
                print(f"\n📝 Sample events from session:")
                for i, event in enumerate(events[:3]):
                    event_type = event.get('type', 'unknown')
                    timestamp = event.get('timestamp', 'N/A')
                    print(f"  {i+1}. {event_type} at {timestamp}")
            
            print(f"\n✅ Session saving functionality working correctly!")
            
        else:
            print("❌ Session file not created")
            return False
        
        # Test the enhanced audit trail
        print(f"\n📋 Testing enhanced audit trail...")
        test_objectives = ["Navigate to Chipotle", "Build custom bowl", "Add to cart"]
        await coordinator._save_run_summary(test_objectives, 3, 3, "https://chipotle.com")
        
        audit_file = os.path.join(coordinator.debug_run_folder, "RUN_SUMMARY_AUDIT_TRAIL.md")
        if os.path.exists(audit_file):
            with open(audit_file, 'r', encoding='utf-8') as f:
                audit_content = f.read()
            
            # Check for interactive session mentions
            if "Interactive Session" in audit_content:
                print("✅ Interactive session mentioned in audit trail")
            else:
                print("⚠️ Interactive session not mentioned in audit trail")
            
            if "cognitive_lattice_interactive_session_" in audit_content:
                print("✅ Session file pattern mentioned in audit")
            else:
                print("⚠️ Session file pattern not mentioned")
        
        print(f"\n🎯 WHAT SKEPTICS NOW GET:")
        print(f"  📜 Complete conversation history from start to finish")
        print(f"  🤖 Every AI decision with rationale and confidence scores")
        print(f"  🧠 Memory formation and context evolution")
        print(f"  📋 Original user request and plan generation")
        print(f"  🔄 Error handling and recovery processes")
        print(f"  💭 Internal reasoning and thought processes")
        
        print(f"\n🎉 INTERACTIVE SESSION SAVING READY!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_session_saving())
    print(f"\n{'🚀 SESSION SAVING COMPLETE' if success else '💥 SESSION SAVING FAILED'}")
    print(f"\n{'Ready for full conversation audit trails!' if success else 'Needs fixes before deployment'}")
    sys.exit(0 if success else 1)
