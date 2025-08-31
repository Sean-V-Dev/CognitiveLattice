"""
Cognitive Lattice - Core session and task management system for CognitiveLattice
Extracted from main.py for better modularity and testability
"""

import os
import json
from datetime import datetime
from typing import Dict, Any, Optional, List


# === Cognitive Lattice and Session Manager === #
class CognitiveLattice:
    """
    Hybrid lattice with active task state + event log for audit trail.
    Maintains single source of truth for current state while preserving full history.
    """
    def __init__(self, session_id=None):
        if session_id:
            self.session_id = session_id
        else:
            # Generate a unique session ID if not provided
            self.session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # New hybrid structure
        self.active_task_state = None  # Single current task state
        self.event_log = []  # Historical events
        self.nodes = []  # Legacy compatibility
        self.session_file = f"cognitive_lattice_{self.session_id}.json"
        self.load()

    def add_node(self, node):
        """Legacy compatibility - adds to event log instead"""
        self.add_event(node)

    def add_event(self, event):
        """Add an event to the audit trail"""
        event["timestamp"] = event.get("timestamp", datetime.now().isoformat())
        self.event_log.append(event)

    def update_active_task(self, task_data):
        """Update the active task state (single source of truth)"""
        task_data["last_updated"] = datetime.now().isoformat()
        self.active_task_state = task_data
        
        # Log this update as an event
        self.add_event({
            "type": "task_state_updated",
            "timestamp": datetime.now().isoformat(),
            "action": task_data.get("action", "update"),
            "step_number": len(task_data.get("completed_steps", [])),
            "user_input": task_data.get("query", "")
        })

    def create_new_task(self, query, task_plan=None):
        """Create a new active task and log the creation event"""
        self.active_task_state = {
            "task_title": f"Structured Task: {query[:50]}...",
            "status": "in_progress",
            "query": query,
            "task_plan": task_plan or [],
            "completed_steps": [],
            "created": datetime.now().isoformat(),
            "last_updated": datetime.now().isoformat()
        }
        
        # Log task creation event
        self.add_event({
            "type": "task_creation",
            "timestamp": datetime.now().isoformat(),
            "query": query
        })
        
        if task_plan:
            self.add_event({
                "type": "plan_generated",
                "timestamp": datetime.now().isoformat(),
                "plan": task_plan
            })
        
        return self.active_task_state

    def complete_current_task(self):
        """Mark the current task as completed"""
        if self.active_task_state:
            self.active_task_state["status"] = "completed"
            self.active_task_state["completed_at"] = datetime.now().isoformat()
            
            # Log completion event
            self.add_event({
                "type": "task_completed",
                "timestamp": datetime.now().isoformat(),
                "task_title": self.active_task_state.get("task_title", "Unknown"),
                "total_steps": len(self.active_task_state.get("task_plan", [])),
                "completed_steps": len(self.active_task_state.get("completed_steps", []))
            })
            
            # Move to event log and clear active state
            completed_task_event = {
                "type": "archived_task",
                "timestamp": datetime.now().isoformat(),
                "task_data": self.active_task_state.copy()
            }
            self.add_event(completed_task_event)
            self.active_task_state = None

    def execute_step(self, step_number, user_input, result):
        """Execute a step and update the active task state"""
        if not self.active_task_state:
            return False
            
        # Update the completed_steps in active state
        completed_steps = self.active_task_state.get("completed_steps", [])
        
        # Find if we're updating an existing step or creating a new one
        step_index = step_number - 1
        if step_index < len(completed_steps):
            # Update existing step
            completed_steps[step_index].update({
                "user_input": user_input,
                "result": result,
                "last_updated": datetime.now().isoformat(),
                "status": "in_progress"
            })
        else:
            # Create new step
            task_plan = self.active_task_state.get("task_plan", [])
            step_description = task_plan[step_index] if step_index < len(task_plan) else f"Step {step_number}"
            
            new_step = {
                "step_number": step_number,
                "description": step_description,
                "user_input": user_input,
                "result": result,
                "timestamp": datetime.now().isoformat(),
                "status": "in_progress"
            }
            completed_steps.append(new_step)
        
        self.active_task_state["completed_steps"] = completed_steps
        self.active_task_state["last_updated"] = datetime.now().isoformat()
        
        # Log the step execution event
        self.add_event({
            "type": "step_execution",
            "timestamp": datetime.now().isoformat(),
            "step_number": step_number,
            "user_input": user_input,
            "result": result[:100] + "..." if len(result) > 100 else result
        })
        
        return True

    def mark_step_completed(self, step_number):
        """Mark a specific step as completed"""
        if not self.active_task_state:
            return False
            
        completed_steps = self.active_task_state.get("completed_steps", [])
        step_index = step_number - 1
        
        if step_index < len(completed_steps):
            completed_steps[step_index]["status"] = "completed"
            self.active_task_state["last_updated"] = datetime.now().isoformat()
            
            # Log step completion
            self.add_event({
                "type": "step_completed",
                "timestamp": datetime.now().isoformat(),
                "step_number": step_number,
                "description": completed_steps[step_index].get("description", f"Step {step_number}")
            })
            return True
        return False

    def get_nodes(self, node_type=None):
        """Legacy compatibility - returns relevant events from event log"""
        if node_type == "task":
            # Return the active task as a node if it exists
            if self.active_task_state:
                return [self.active_task_state]
            else:
                return []
        else:
            # Return matching events from event log
            if node_type:
                return [event for event in self.event_log if event.get("type") == node_type]
            return self.event_log

    def cleanup_malformed_tasks(self):
        """Clean up malformed active task"""
        if self.active_task_state:
            task = self.active_task_state
            # Check for tasks without proper structure
            if not task.get("task_plan") or not isinstance(task.get("task_plan"), list) or len(task.get("task_plan", [])) == 0:
                print(f"🧹 Cleaning up malformed active task: {task.get('task_title', 'Untitled')[:30]}...")
                self.complete_current_task()  # Archive it
                self.add_event({
                    "type": "task_cleanup",
                    "timestamp": datetime.now().isoformat(),
                    "reason": "No valid task plan"
                })
                print(f"🧹 Malformed task archived")

    def get_active_task(self):
        """Returns the current active task (single source of truth)"""
        if self.active_task_state and self.active_task_state.get("status") in ["pending", "in_progress"]:
            return self.active_task_state
        return None

    def update_node(self, node_index, updates):
        """Updates a specific node in the lattice."""
        if 0 <= node_index < len(self.nodes):
            self.nodes[node_index].update(updates)
            return True
        return False

    def get_task_progress(self, task_node):
        """Calculates and returns the progress of a given task."""
        if not task_node or "task_plan" not in task_node:
            return {"total_steps": 0, "completed_steps": 0, "progress_percent": 0}
        
        total_steps = len(task_node["task_plan"])
        completed_steps = len(task_node.get("completed_steps", []))
        progress_percent = (completed_steps / total_steps) * 100 if total_steps > 0 else 0
        
        return {
            "total_steps": total_steps,
            "completed_steps": completed_steps,
            "progress_percent": progress_percent
        }

    def save(self, path=None):
        """Saves the hybrid lattice structure to JSON file."""
        file_path = path if path else self.session_file
        
        # Create the hybrid structure
        lattice_data = {
            "active_task_state": self.active_task_state,
            "event_log": self.event_log
        }
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(lattice_data, f, indent=2, ensure_ascii=False)

    def load(self, path=None):
        """Loads the hybrid lattice structure from JSON file."""
        file_path = path if path else self.session_file
        if os.path.exists(file_path):
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    if os.path.getsize(file_path) > 0:
                        data = json.load(f)
                        
                        # Check if it's the new hybrid format
                        if isinstance(data, dict) and "active_task_state" in data:
                            self.active_task_state = data.get("active_task_state")
                            self.event_log = data.get("event_log", [])
                            self.nodes = []  # Legacy compatibility
                        else:
                            # Legacy format - convert to new format
                            print("🔄 Converting legacy lattice format to hybrid format...")
                            self.nodes = data if isinstance(data, list) else []
                            self.active_task_state = None
                            self.event_log = []
                            
                            # Find the most recent active task and convert
                            for node in reversed(self.nodes):
                                if node.get("type") == "task" and node.get("status") in ["pending", "in_progress"]:
                                    self.active_task_state = {
                                        "task_title": node.get("task_title", "Converted Task"),
                                        "status": node.get("status", "in_progress"),
                                        "query": node.get("query", ""),
                                        "task_plan": node.get("task_plan", []),
                                        "completed_steps": node.get("completed_steps", []),
                                        "created": node.get("timestamp", datetime.now().isoformat()),
                                        "last_updated": datetime.now().isoformat()
                                    }
                                    break
                            
                            # Convert all nodes to events
                            for node in self.nodes:
                                event_type = node.get("type", "unknown")
                                if event_type == "task":
                                    event_type = "task_interaction"
                                
                                self.event_log.append({
                                    "type": event_type,
                                    "timestamp": node.get("timestamp", datetime.now().isoformat()),
                                    "legacy_data": node
                                })
                            
                            # Save in new format
                            self.save()
                            print(f"✅ Converted {len(self.nodes)} legacy nodes to hybrid format")
                            
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️ Could not load or parse lattice file '{file_path}': {e}")
                self.active_task_state = None
                self.event_log = []
                self.nodes = []
        else:
            self.active_task_state = None
            self.event_log = []
            self.nodes = []

class SessionManager:
    """
    Manages session-wide state, including the cognitive lattice and session file.
    """
    def __init__(self, session_file=None):
        if session_file:
            self.session_file = session_file
        else:
            self.session_file = f"cognitive_lattice_interactive_session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        # Extract just the timestamp portion to avoid filename duplication
        # From "cognitive_lattice_interactive_session_20250830_121848" extract "interactive_session_20250830_121848"
        full_session_id = os.path.splitext(os.path.basename(self.session_file))[0]
        if full_session_id.startswith("cognitive_lattice_"):
            clean_session_id = full_session_id[len("cognitive_lattice_"):]
        else:
            clean_session_id = full_session_id
        
        self.lattice = CognitiveLattice(session_id=clean_session_id)
        self.session_data = {"queries": []}
        if os.path.exists(self.session_file):
            try:
                with open(self.session_file, 'r', encoding='utf-8') as f:
                    if os.path.getsize(self.session_file) > 0:
                        self.session_data = json.load(f)
            except (json.JSONDecodeError, KeyError) as e:
                print(f"⚠️ Could not load or parse session file '{self.session_file}': {e}")
                self.session_data = {"queries": []}

    def add_query(self, query_node):
        self.session_data["queries"].append(query_node)
        self.save()

    def add_lattice_node(self, node):
        """Legacy compatibility - converts to event and updates active task if needed"""
        if node.get("type") == "task":
            # This is a task update - update the active task state
            self.lattice.update_active_task(node)
        else:
            # This is a regular event - add to event log
            self.lattice.add_event(node)
        self.lattice.save()

    def save(self):
        with open(self.session_file, 'w', encoding='utf-8') as f:
            json.dump(self.session_data, f, indent=2, ensure_ascii=False)

    def get_lattice(self):
        return self.lattice
