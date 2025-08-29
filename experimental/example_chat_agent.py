#!/usr/bin/env python3
"""
Example Chat Agent using Domain-Agnostic Cognitive Lattice
==========================================================

This demonstrates how the cognitive lattice can be used for 
chat/conversation agents, not just web automation.
"""

from core.cognitive_lattice import CognitiveLattice
from datetime import datetime
from typing import Dict, Any, List


class ChatAgentCore:
    """
    Core chat functionality that reports to the cognitive lattice
    but doesn't manage lattice state directly.
    """
    
    def __init__(self, external_client=None):
        self.external_client = external_client
        self.conversation_history = []
        
        # Lattice will be injected by a coordinator
        self.lattice = None
    
    def set_lattice(self, lattice):
        """Inject lattice dependency"""
        self.lattice = lattice
    
    def process_user_message(self, message: str) -> str:
        """Process a user message and generate response"""
        # Store user message
        self.conversation_history.append({
            "role": "user",
            "content": message,
            "timestamp": datetime.now().isoformat()
        })
        
        # Generate response (simple echo for demo)
        response = f"You said: '{message}'. This is a chat agent using the cognitive lattice!"
        
        # Store assistant response
        self.conversation_history.append({
            "role": "assistant", 
            "content": response,
            "timestamp": datetime.now().isoformat()
        })
        
        # Report to lattice if available
        self._report_interaction_to_lattice(message, response)
        
        return response
    
    def _report_interaction_to_lattice(self, user_message: str, response: str):
        """Report chat interaction to lattice if available"""
        if not self.lattice:
            return
            
        try:
            # Prepare chat-specific step data
            chat_step_data = {
                "type": "chat_interaction",
                "user_message": user_message,
                "assistant_response": response,
                "conversation_length": len(self.conversation_history),
                "success": True,
                "domain": "chat"
            }
            
            # Report to lattice
            active_task = self.lattice.get_active_task()
            if active_task:
                step_number = len(active_task.get("completed_steps", [])) + 1
                self.lattice.execute_step(step_number, chat_step_data, domain="chat")
            else:
                # Log as event if no active task
                self.lattice.add_event({
                    "type": "chat_interaction_completed",
                    "domain": "chat",
                    "payload": chat_step_data
                })
        except Exception as e:
            print(f"⚠️ Failed to report to lattice: {e}")


class ChatAgentCoordinator:
    """
    Coordinates chat agent with cognitive lattice integration.
    """
    
    def __init__(self, external_client=None, cognitive_lattice=None):
        self.external_client = external_client
        self.lattice = cognitive_lattice
        
        # Create chat agent and inject lattice
        self.chat_agent = ChatAgentCore(external_client=external_client)
        self.chat_agent.set_lattice(self.lattice)
    
    def start_conversation(self, topic: str) -> str:
        """Start a new conversation task"""
        if self.lattice:
            task_data = self.lattice.create_new_task(
                query=f"Have a conversation about: {topic}",
                domain="chat",
                context={"conversation_topic": topic}
            )
            print(f"[LATTICE] Created chat task: {task_data['task_id']}")
        
        return f"Let's talk about {topic}! What would you like to know?"
    
    def chat(self, message: str) -> str:
        """Process a chat message"""
        return self.chat_agent.process_user_message(message)
    
    def end_conversation(self):
        """End the conversation and complete the task"""
        if self.lattice:
            active_task = self.lattice.get_active_task()
            if active_task:
                conversation_length = len(self.chat_agent.conversation_history)
                self.lattice.complete_task(
                    result=f"Conversation completed with {conversation_length} messages",
                    success=True
                )
                print(f"[LATTICE] Completed chat task with {conversation_length} interactions")


# Example usage demonstrating domain-agnostic lattice
if __name__ == "__main__":
    print("🧠 Cognitive Lattice - Chat Agent Example")
    print("=" * 50)
    
    # Create domain-agnostic cognitive lattice
    lattice = CognitiveLattice()
    print(f"✅ Created cognitive lattice")
    
    # Create chat coordinator with lattice integration
    chat_coordinator = ChatAgentCoordinator(cognitive_lattice=lattice)
    print("✅ Created chat agent with lattice integration")
    
    # Start conversation
    intro = chat_coordinator.start_conversation("artificial intelligence")
    print(f"🤖 {intro}")
    
    # Have a conversation
    messages = [
        "What is machine learning?",
        "How does it relate to AI?",
        "Thanks for the information!"
    ]
    
    for msg in messages:
        print(f"👤 {msg}")
        response = chat_coordinator.chat(msg)
        print(f"🤖 {response}")
    
    # End conversation
    chat_coordinator.end_conversation()
    
    # Show lattice captured the conversation
    print("\n📊 Lattice Summary:")
    active_task = lattice.get_active_task()
    if active_task:
        completed_steps = active_task.get("completed_steps", [])
        print(f"   Task: {active_task.get('query', 'Unknown')}")
        print(f"   Domain: {active_task.get('domain', 'Unknown')}")
        print(f"   Steps completed: {len(completed_steps)}")
        print(f"   Status: {active_task.get('status', 'Unknown')}")
    
    recent_events = lattice.get_recent_events(limit=5)
    print(f"   Recent events: {len(recent_events)}")
    
    print("\n🎉 Demo complete! The same cognitive lattice can handle both:")
    print("   - Web automation (via WebAgentCore + CognitiveLatticeWebCoordinator)")
    print("   - Chat conversations (via ChatAgentCore + ChatAgentCoordinator)")
    print("   - Any other domain you want to add!")
