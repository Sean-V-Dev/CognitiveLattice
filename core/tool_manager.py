"""
Tool Manager for CognitiveLattice Framework
Detects when tools should be used and executes them automatically.
"""

import re
import json
import importlib.util
import os
from datetime import datetime
from typing import Dict, Any, List, Optional

class ToolManager:
    """
    Manages tool detection, loading, and execution for the CognitiveLattice framework.
    """
    
    def __init__(self, tools_directory="tools"):
        self.tools_directory = tools_directory
        self.available_tools = {}
        self.recent_tool_results = {}
        self.persistent_objects = {}  # NEW: Store complex objects like RAG systems
        self.load_tools()
    
    def load_tools(self):
        """Load all available tools from the tools directory"""
        if not os.path.exists(self.tools_directory):
            print(f"⚠️ Tools directory '{self.tools_directory}' not found")
            return
        
        tool_count = 0
        for filename in os.listdir(self.tools_directory):
            if filename.endswith('_tool.py'):
                tool_name = filename[:-8]  # Remove '_tool.py'
                tool_path = os.path.join(self.tools_directory, filename)
                
                try:
                    # Load the module dynamically
                    spec = importlib.util.spec_from_file_location(tool_name, tool_path)
                    module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(module)
                    
                    # Look for functions in the module
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if callable(attr) and not attr_name.startswith('_'):
                            self.available_tools[attr_name] = {
                                'function': attr,
                                'module': tool_name,
                                'file': filename
                            }
                            tool_count += 1
                            print(f"🔧 Loaded tool: {attr_name} from {filename}")
                
                except Exception as e:
                    print(f"⚠️ Failed to load tool {filename}: {e}")
        
        print(f"✅ Tool Manager initialized with {tool_count} tools")
    
    def detect_tool_needs(self, llm_response: str, context: Dict[str, Any] = None) -> List[Dict[str, Any]]:
        """
        LLM-DRIVEN tool detection: Let the LLM decide which tools to use based on context.
        This is the core challenge - getting LLMs to choose tools intelligently.
        """
        tool_calls = []
        
        # Get task context if provided
        step_description = context.get('step_description', '') if context else ''
        task_context = context.get('task_context', {}) if context else {}
        
        # First check for explicit tool selection (option numbers, etc.)
        tool_calls.extend(self._detect_selection_patterns(llm_response))
        if tool_calls:
            return tool_calls  # Selection takes priority
        
        # LLM-DRIVEN TOOL SELECTION: Ask the LLM to choose tools
        available_tool_names = list(self.available_tools.keys())
        needed_tool = self._llm_tool_selection(llm_response, step_description, available_tool_names, context)
        
        if needed_tool and needed_tool != 'none':
            tool_params = self._extract_tool_parameters(llm_response, needed_tool, step_description)
            if tool_params:
                tool_calls.append({
                    'tool_name': needed_tool,
                    'parameters': tool_params,
                    'reason': f"LLM-selected tool: {needed_tool} for task context"
                })
        
        return tool_calls
    
    def _llm_tool_selection(self, user_input: str, step_description: str, available_tools: List[str], context: Dict[str, Any] = None) -> Optional[str]:
        """
        Use external LLM to intelligently select tools based on context.
        This is the real challenge - contextual tool selection by LLM reasoning.
        """
        # Build context about recent tool results and document state
        recent_tools_context = ""
        if hasattr(self, 'recent_tool_results') and self.recent_tool_results:
            recent_tools_context = "\n\nRECENT TOOL RESULTS:\n"
            for tool_name, result in self.recent_tool_results.items():
                if tool_name == 'document_processor':
                    recent_tools_context += f"- {tool_name}: Document has been processed and is ready for queries\n"
                else:
                    recent_tools_context += f"- {tool_name}: Available for follow-up actions\n"
        
        # Add lattice/session context if available
        lattice_context = ""
        if context and context.get('session_manager'):
            session_manager = context['session_manager']
            try:
                # Check if there are any document processing events in the lattice
                all_events = session_manager.lattice.events
                doc_events = [e for e in all_events if e.get("type") == "document_processed"]
                if doc_events:
                    latest_doc = doc_events[-1]
                    source_file = latest_doc.get("source_file", "unknown")
                    lattice_context = f"\n\nDOCUMENT STATE: A document ({source_file}) has been processed and content is available in memory.\n"
            except Exception:
                pass  # Ignore lattice access errors
        
        # Create LLM prompt for tool selection
        tool_selection_prompt = f"""You are an intelligent tool selection agent. Analyze the context and determine if any tools should be used.

CURRENT TASK STEP: "{step_description}"
USER INPUT: "{user_input}"

AVAILABLE TOOLS:
{self._format_available_tools(available_tools)}

{recent_tools_context}{lattice_context}

DECISION FRAMEWORK:
1. What is the user trying to accomplish?
2. Is this a request to process/load a new document, or query existing document content?
3. Do they need search/planning functionality (flights, hotels, restaurants)?
4. Are they selecting from previous results (option numbers)?

IMPORTANT GUIDELINES:
- Use "document_processor" for NEW document processing requests
- Use "document_query" for questions about ALREADY PROCESSED documents
- Use planners for initial searches, selectors for choosing options
- Trust your judgment - you understand context better than rigid rules

Respond with ONLY the tool name (e.g., "document_query") or "none" if no tool is needed."""

        try:
            # Try to get LLM decision from external API
            if context and context.get('external_client'):
                print(f"🧠 Asking LLM to select tools for: '{user_input}'")
                llm_decision = context['external_client'].query_external_api(tool_selection_prompt)
                
                # Clean and validate the LLM response
                selected_tool = llm_decision.strip().lower()
                if selected_tool in available_tools:
                    print(f"🎯 LLM selected tool: {selected_tool}")
                    return selected_tool
                elif selected_tool == 'none':
                    print(f"🎯 LLM decided no tools needed")
                    return None
                else:
                    print(f"⚠️ LLM suggested invalid tool '{selected_tool}', falling back to contextual reasoning")
                    return self._contextual_tool_reasoning(user_input, step_description, available_tools)
            else:
                # No external client available, use contextual reasoning
                print(f"🔧 No external LLM available, using contextual reasoning")
                return self._contextual_tool_reasoning(user_input, step_description, available_tools)
            
        except Exception as e:
            print(f"🔧 LLM tool selection failed, falling back to contextual reasoning: {e}")
            return self._contextual_tool_reasoning(user_input, step_description, available_tools)
    
    def _detect_selection_patterns(self, llm_response: str) -> List[Dict[str, Any]]:
        """Detect explicit selection patterns (option numbers, etc.)"""
        tool_calls = []
        
        # Debug output
        print(f"🔍 Checking selection patterns for: '{llm_response}'")
        print(f"🔍 Recent tool results available: {list(self.recent_tool_results.keys())}")
        
        # Generic selection patterns (not tool-specific)
        selection_patterns = [
            r"(?:choose|select|pick|want|take|book).*(?:option|choice)\s*(\d+)",
            r"(?:go with|decide on).*(?:option)\s*(\d+)",
            r"(?:option)\s*(\d+).*(?:please|thanks|sounds good)",
            r"i\s+want\s+option\s+(\d+)",
            r"(?:choose|select|pick)\s+(?:the\s+)?(\d+)",
            r"option\s+(\d+)",
            r"^option\s+(\d+)$",
            r"^(\d+)$"
        ]
        
        for pattern in selection_patterns:
            match = re.search(pattern, llm_response, re.IGNORECASE)
            if match:
                option_number = int(match.group(1))
                print(f"🎯 Selection pattern matched: {pattern} -> option {option_number}")
                
                # Smart selector detection based on most recent tool results
                selector_tool = None
                previous_results = None
                
                # Priority order: check most recent tool results first
                if 'restaurant_planner' in self.recent_tool_results and 'restaurant_selector' in self.available_tools:
                    selector_tool = 'restaurant_selector'
                    previous_results = self.recent_tool_results['restaurant_planner']
                    print(f"✅ Using restaurant_selector (most recent: restaurant_planner)")
                    
                elif 'hotel_planner' in self.recent_tool_results and 'hotel_selector' in self.available_tools:
                    selector_tool = 'hotel_selector'
                    previous_results = self.recent_tool_results['hotel_planner']
                    print(f"✅ Using hotel_selector (most recent: hotel_planner)")
                    
                elif 'flight_planner' in self.recent_tool_results and 'flight_selector' in self.available_tools:
                    selector_tool = 'flight_selector'
                    previous_results = self.recent_tool_results['flight_planner']
                    print(f"✅ Using flight_selector (most recent: flight_planner)")
                    
                if selector_tool and previous_results:
                    # Create the appropriate parameter structure for each selector
                    if selector_tool == 'flight_selector':
                        parameters = {
                            'option_number': option_number,
                            'previous_flight_results': previous_results
                        }
                    elif selector_tool == 'hotel_selector':
                        parameters = {
                            'option_number': option_number,
                            'previous_hotel_results': previous_results
                        }
                    elif selector_tool == 'restaurant_selector':
                        parameters = {
                            'option_number': option_number,
                            'previous_restaurant_results': previous_results
                        }
                    else:
                        parameters = {
                            'option_number': option_number,
                            'previous_results': previous_results
                        }
                    
                    tool_calls.append({
                        'tool_name': selector_tool,
                        'parameters': parameters,
                        'reason': f"User selected {selector_tool.replace('_selector', '')} option {option_number}"
                    })
                    break  # Only use the first matching pattern
                else:
                    print(f"❌ No recent planner results found for selection")
        
        if tool_calls:
            print(f"🔧 Selection detection found {len(tool_calls)} tool calls")
        else:
            print(f"🔧 No selection patterns detected")
            
        return tool_calls
    
    def _intelligent_tool_detection(self, llm_response: str, step_description: str, available_tools: List[str]) -> Optional[str]:
        """
        Use LLM reasoning to intelligently determine which tool is needed.
        This is the core challenge - getting LLMs to choose tools contextually.
        """
        # Create a tool selection prompt for the LLM
        tool_selection_prompt = f"""You are a tool selection agent. Your job is to analyze the current task context and user input to determine if any tools should be used.

CURRENT TASK STEP: "{step_description}"
USER INPUT: "{llm_response}"

AVAILABLE TOOLS:
{self._format_available_tools(available_tools)}

TOOL SELECTION RULES:
1. Consider the task context and what the user is trying to accomplish
2. Look for specific requests that match tool capabilities
3. Consider implicit needs (e.g., if step asks for flight research and user mentions cities)
4. Only suggest tools that are actually needed and available

REASONING PROCESS:
- What is the user trying to accomplish in this step?
- Does their input suggest they need a specific tool's functionality?
- Are there implicit tool needs based on the task context?

Respond with ONLY the tool name (e.g., "flight_planner") or "none" if no tool is needed.
Do not explain your reasoning, just provide the tool name or "none"."""

        # This would ideally call a lightweight local LLM or reasoning engine
        # For now, we'll implement a simplified contextual analysis that mimics LLM reasoning
        return self._contextual_tool_reasoning(llm_response, step_description, available_tools)
    
    def _format_available_tools(self, available_tools: List[str]) -> str:
        """Format available tools with descriptions for LLM"""
        tool_descriptions = {
            'document_processor': 'Processes/loads a document for the first time (use when user wants to "process", "load", or "analyze" a document)',
            'document_query': 'Queries content from a previously processed document (use when user asks "what is in", "summarize", or questions about document content)',
            'flight_planner': 'Searches for flight options between cities with dates and pricing',
            'flight_selector': 'Selects a specific flight option from previous search results',
            'hotel_planner': 'Finds accommodation options in a specific location',
            'hotel_selector': 'Selects a specific hotel from previous search results',
            'restaurant_planner': 'Searches for dining options and makes reservations',
            'restaurant_selector': 'Selects a specific restaurant from previous search results'
        }
        
        formatted = []
        for tool in available_tools:
            desc = tool_descriptions.get(tool, 'No description available')
            formatted.append(f"- {tool}: {desc}")
        
        return "\n".join(formatted)
    
    def _contextual_tool_reasoning(self, user_input: str, step_description: str, available_tools: List[str]) -> Optional[str]:
        """Enhanced contextual reasoning that includes document processing."""
        combined_context = f"{step_description} {user_input}".lower()
        
        # Enhanced reasoning patterns including document processing
        reasoning_patterns = {
            'document_processor': [
                # Direct document processing requests
                lambda ctx: any(phrase in ctx for phrase in ['process document', 'analyze document', 'load document']),
                # File-based processing requests
                lambda ctx: any(ext in ctx for ext in ['.pdf', '.txt', '.docx']) and 
                           any(action in ctx for action in ['process', 'analyze', 'load']),
                # Document analysis context
                lambda ctx: any(phrase in ctx for phrase in ['document analysis', 'text analysis', 'file analysis']),
            ],
            'document_query': [
                # Query requests when RAG system is available
                lambda ctx: any(phrase in ctx for phrase in ['search document', 'find in document', 'query document']) and
                           'advanced_rag_system' in str(self.persistent_objects.keys()),
                # Analysis questions when document is loaded
                lambda ctx: any(phrase in ctx for phrase in ['what does', 'who is', 'where is', 'how does']) and
                           'advanced_rag_system' in str(self.persistent_objects.keys()),
            ],
            'flight_planner': [
                # Direct flight requests
                lambda ctx: any(phrase in ctx for phrase in ['flight', 'fly', 'airline']) and 
                           any(loc_pattern in ctx for loc_pattern in ['from', 'to', 'between']),
                # Implicit flight needs from step context
                lambda ctx: 'flight' in step_description.lower() and 
                           any(city_indicator in ctx for city_indicator in ['cincinnati', 'myrtle beach', 'airport', 'travel']),
            ],
            'flight_selector': [
                # Explicit option selection
                lambda ctx: any(pattern in ctx for pattern in ['option', 'choice', 'select', 'choose']) and 
                           any(num in ctx for num in ['1', '2', '3', 'one', 'two', 'three']),
                # Airline-specific selection
                lambda ctx: any(airline in ctx for airline in ['delta', 'spirit', 'american', 'united']) and
                           'flight_planner' in str(self.recent_tool_results.keys())
            ],
            'hotel_planner': [
                # Hotel/accommodation context
                lambda ctx: 'accommodation' in step_description.lower() and 
                           any(term in ctx for term in ['hotel', 'stay', 'room', 'lodging']),
                # Location-based accommodation search
                lambda ctx: any(term in ctx for term in ['hotel', 'accommodation', 'stay']) and
                           any(loc in ctx for loc in ['in', 'at', 'near'])
            ],
            'restaurant_planner': [
                # Food/dining context
                lambda ctx: any(term in step_description.lower() for term in ['dining', 'food', 'restaurant']) and
                           any(term in ctx for term in ['eat', 'restaurant', 'dinner', 'lunch']),
            ]
        }
        
        # Apply contextual reasoning for each available tool
        for tool_name in available_tools:
            if tool_name in reasoning_patterns:
                patterns = reasoning_patterns[tool_name]
                
                # Check if any reasoning pattern matches
                for pattern_func in patterns:
                    try:
                        if pattern_func(combined_context):
                            # Additional validation - ensure we have necessary context
                            if self._validate_tool_context(tool_name, combined_context):
                                return tool_name
                    except Exception:
                        continue  # Skip failed pattern checks
        
        return None
    
    def _validate_tool_context(self, tool_name: str, context: str) -> bool:
        """Validate that we have sufficient context to use a tool effectively"""
        if tool_name == 'flight_planner':
            # Need location indicators
            return any(pattern in context for pattern in ['from', 'to', 'cincinnati', 'myrtle beach'])
        
        elif tool_name == 'flight_selector':
            # Need previous flight results and selection indicator
            return ('flight_planner' in self.recent_tool_results and 
                    any(sel in context for sel in ['option', 'choice', '1', '2', '3']))
        
        elif tool_name == 'hotel_planner':
            # Need location context
            return any(loc in context for loc in ['in', 'at', 'near', 'myrtle beach'])
        
        elif tool_name == 'restaurant_planner':
            # Need location context
            return any(loc in context for loc in ['in', 'at', 'near', 'myrtle beach'])
        
        return True  # Default to allowing tool if no specific validation needed
    
    def _extract_tool_parameters(self, llm_response: str, tool_name: str, step_description: str) -> Optional[Dict[str, Any]]:
        """Enhanced parameter extraction including document processing tools."""
        combined_text = f"{step_description} {llm_response}"
        
        if tool_name == 'document_processor':
            # Extract document processing parameters
            print(f"📄 Extracting document_processor parameters from: '{combined_text}'")
            
            # Look for file paths or names
            file_pattern = r'([a-zA-Z0-9_\-\.]+\.(pdf|txt|docx))'
            match = re.search(file_pattern, combined_text, re.IGNORECASE)
            
            source_file = None
            if match:
                source_file = match.group(1)
                print(f"📄 Found file: {source_file}")
            else:
                # Look for common file names
                common_files = ['example.txt', 'example.pdf', 'document.pdf', 'test.txt']
                for common_file in common_files:
                    if os.path.exists(common_file):
                        source_file = common_file
                        print(f"📄 Using existing file: {source_file}")
                        break
                
                if not source_file:
                    source_file = 'example.txt'  # Default fallback
                    print(f"📄 Using default file: {source_file}")
            
            # Determine processing mode
            processing_mode = "full"  # Default
            if 'steganographic only' in combined_text.lower():
                processing_mode = "steganographic_only"
            elif 'chunks only' in combined_text.lower():
                processing_mode = "chunks_only"
            
            return {
                'source_file': source_file,
                'processing_mode': processing_mode,
                'enable_external_api': True  # Can be made configurable
            }
            
        elif tool_name == 'document_query':
            # Extract query parameters
            print(f"🔍 Extracting document_query parameters from: '{combined_text}'")
            
            # The query is essentially the user's input cleaned up
            query = llm_response.strip()
            
            # Get RAG system from persistent objects
            rag_system = self.persistent_objects.get('advanced_rag_system')
            
            return {
                'query': query,
                'rag_system': rag_system,
                'max_chunks': 5  # Default
            }
        
        elif tool_name == 'flight_planner':
            # Extract flight search parameters with more flexible patterns
            origin = None
            destination = None
            
            # Pattern 1: "from X to Y" (more flexible with city names)
            from_to_pattern = r'from\s+([a-zA-Z][a-zA-Z\s]{1,25})\s+to\s+([a-zA-Z][a-zA-Z\s]{1,25})'
            match = re.search(from_to_pattern, combined_text, re.IGNORECASE)
            
            if match:
                origin = match.group(1).strip()
                destination = match.group(2).strip()
            else:
                # Pattern 2: Look for city names in context (Los Angeles, LA, Cincinnati, etc.)
                city_patterns = [
                    (r'\b(cincinnati|cincy|cvg)\b', 'cincinnati'),
                    (r'\b(los angeles|la|lax)\b', 'los angeles'),
                    (r'\b(new york|nyc|ny|jfk|lga)\b', 'new york'),
                    (r'\b(chicago|chi|ord)\b', 'chicago'),
                    (r'\b(myrtle beach|myrtle)\b', 'myrtle beach'),
                    (r'\b(miami|mia)\b', 'miami'),
                    (r'\b(san francisco|sf|sfo)\b', 'san francisco')
                ]
                
                found_cities = []
                for pattern, city_name in city_patterns:
                    if re.search(pattern, combined_text, re.IGNORECASE):
                        found_cities.append(city_name)
                
                # If we found cities in step description vs user input, try to determine origin/destination
                if found_cities:
                    if 'los angeles' in found_cities or 'myrtle beach' in found_cities:
                        # These are likely destinations
                        destination = 'los angeles' if 'los angeles' in found_cities else 'myrtle beach'
                        if 'cincinnati' in found_cities:
                            origin = 'cincinnati'
                    elif 'cincinnati' in found_cities and len(found_cities) > 1:
                        origin = 'cincinnati'
                        destination = [city for city in found_cities if city != 'cincinnati'][0]
            
            # If we have origin and destination, create parameters
            if origin and destination:
                # Validate city names (allow 2+ characters, alphabetic)
                if (len(origin) >= 2 and len(destination) >= 2 and 
                    origin.replace(' ', '').isalpha() and destination.replace(' ', '').isalpha()):
                    
                    return {
                        'origin': origin,
                        'destination': destination,
                        'departure_date': self._extract_date(combined_text, "departure") or "2025-07-29",
                        'return_date': self._extract_date(combined_text, "return") or "2025-08-01"
                    }
            
            # If no specific cities found, but step is about flights, create generic parameters
            if 'flight' in step_description.lower() or 'fly' in llm_response.lower():
                return {
                    'origin': 'cincinnati',  # Default based on context
                    'destination': 'destination_from_context',  # Will be handled by tool
                    'departure_date': self._extract_date(combined_text, "departure") or "2025-07-29",
                    'return_date': self._extract_date(combined_text, "return") or "2025-08-01"
                }
        
        elif tool_name == 'hotel_planner':
            # Extract hotel search parameters (location, dates, etc.)
            print(f"🏨 Extracting hotel_planner parameters from: '{combined_text}'")
            
            location = None
            
            # Pattern 1: Look for explicit location mentions with "in"
            location_pattern = r'in\s+([a-zA-Z][a-zA-Z\s]{2,30})'
            match = re.search(location_pattern, combined_text, re.IGNORECASE)
            
            if match:
                location = match.group(1).strip()
                print(f"🏨 Found location from 'in' pattern: {location}")
            else:
                # Pattern 2: Look for city names in the text (like we do for flight_planner)
                city_patterns = [
                    (r'\b(myrtle beach|myrtle)\b', 'myrtle beach'),
                    (r'\b(los angeles|la|lax)\b', 'los angeles'),
                    (r'\b(new york|nyc|ny|jfk|lga)\b', 'new york'),
                    (r'\b(chicago|chi|ord)\b', 'chicago'),
                    (r'\b(cincinnati|cincy|cvg)\b', 'cincinnati'),
                    (r'\b(miami|mia)\b', 'miami'),
                    (r'\b(san francisco|sf|sfo)\b', 'san francisco')
                ]
                
                for pattern, city_name in city_patterns:
                    if re.search(pattern, combined_text, re.IGNORECASE):
                        location = city_name
                        print(f"🏨 Found location from city pattern: {location}")
                        break
                
                # Pattern 3: If no location found but this is a hotel step, try to infer from step description
                if not location and ('hotel' in step_description.lower() or 'hotel' in combined_text.lower()):
                    # Look for destination cities in the step description (common in travel planning)
                    for pattern, city_name in city_patterns:
                        if re.search(pattern, step_description, re.IGNORECASE):
                            location = city_name
                            print(f"🏨 Inferred location from step context: {location}")
                            break
                    
                    # If still no location, use a default (this is common in travel tasks)
                    if not location:
                        location = 'destination city'  # Generic fallback
                        print(f"🏨 Using generic location fallback: {location}")
            
            if location:
                return {
                    'location': location,
                    'checkin_date': self._extract_date(combined_text, "checkin") or "2025-07-29",
                    'checkout_date': self._extract_date(combined_text, "checkout") or "2025-08-01"
                }
            else:
                print(f"🏨 No location found for hotel_planner")
                return None
        
        elif tool_name == 'restaurant_planner':
            # Extract restaurant search parameters
            print(f"🍽️ Extracting restaurant_planner parameters from: '{combined_text}'")
            
            location = None
            
            # Pattern 1: Look for explicit location mentions with "in" 
            location_pattern = r'in\s+([a-zA-Z][a-zA-Z\s]{2,30})'
            match = re.search(location_pattern, combined_text, re.IGNORECASE)
            
            if match:
                location = match.group(1).strip()
                print(f"🍽️ Found location from 'in' pattern: {location}")
            else:
                # Pattern 2: Look for city names in the text
                city_patterns = [
                    (r'\b(myrtle beach|myrtle)\b', 'myrtle beach'),
                    (r'\b(los angeles|la|lax)\b', 'los angeles'),
                    (r'\b(new york|nyc|ny|jfk|lga)\b', 'new york'),
                    (r'\b(chicago|chi|ord)\b', 'chicago'),
                    (r'\b(cincinnati|cincy|cvg)\b', 'cincinnati'),
                    (r'\b(miami|mia)\b', 'miami'),
                    (r'\b(san francisco|sf|sfo)\b', 'san francisco')
                ]
                
                for pattern, city_name in city_patterns:
                    if re.search(pattern, combined_text, re.IGNORECASE):
                        location = city_name
                        print(f"🍽️ Found location from city pattern: {location}")
                        break
                
                # Pattern 3: If no location found but this is a restaurant step, try to infer from step description
                if not location and ('restaurant' in step_description.lower() or 'dining' in step_description.lower() or 'eat' in combined_text.lower()):
                    # Look for destination cities in the step description
                    for pattern, city_name in city_patterns:
                        if re.search(pattern, step_description, re.IGNORECASE):
                            location = city_name
                            print(f"🍽️ Inferred location from step context: {location}")
                            break
                    
                    # If still no location, use a default
                    if not location:
                        location = 'destination city'  # Generic fallback
                        print(f"🍽️ Using generic location fallback: {location}")
            
            if location:
                return {
                    'location': location,
                    'date': self._extract_date(combined_text, "dinner") or "2025-07-29",
                    'party_size': self._extract_party_size(combined_text) or 2
                }
            else:
                print(f"🍽️ No location found for restaurant_planner")
                return None
        
        return None
    
    def _extract_party_size(self, text: str) -> Optional[int]:
        """Extract party size from text"""
        party_patterns = [
            r'(\d+)\s+people',
            r'party\s+of\s+(\d+)',
            r'table\s+for\s+(\d+)',
            r'(\d+)\s+person'
        ]
        
        for pattern in party_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return int(match.group(1))
        
        return None
    
    def _extract_date(self, text: str, date_type: str) -> Optional[str]:
        """Extract dates from text with support for relative dates like 'tomorrow'"""
        from datetime import datetime, timedelta
        
        # Handle relative dates first
        today = datetime.now()
        
        # Check for "tomorrow"
        if 'tomorrow' in text.lower():
            tomorrow = today + timedelta(days=1)
            if date_type in ["departure", "checkin"]:
                return tomorrow.strftime("%Y-%m-%d")
        
        # Check for "X days" duration
        days_match = re.search(r'(\d+)\s+days?', text.lower())
        if days_match and 'tomorrow' in text.lower():
            duration = int(days_match.group(1))
            if date_type in ["return", "checkout"]:
                return_date = today + timedelta(days=1 + duration)  # tomorrow + duration
                return return_date.strftime("%Y-%m-%d")
        
        # Standard date patterns
        date_patterns = [
            r"(\d{4}-\d{2}-\d{2})",  # ISO format
            r"July\s+(\d{1,2}),?\s*(\d{4})",  # July 29, 2025
            r"August\s+(\d{1,2}),?\s*(\d{4})"  # August 1, 2025
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                if len(match.groups()) == 1:
                    return match.group(1)  # ISO format
                elif len(match.groups()) == 2:
                    month_name = match.string[match.start():match.end()].split()[0].lower()
                    day = match.group(1)
                    year = match.group(2)
                    
                    month_map = {'july': '07', 'august': '08'}
                    month = month_map.get(month_name, '07')
                    
                    return f"{year}-{month}-{day.zfill(2)}"
        
        return None
    
    def execute_tool(self, tool_name: str, parameters: Dict[str, Any], session_manager=None) -> Dict[str, Any]:
        """Enhanced tool execution that handles persistent objects."""
        if tool_name not in self.available_tools:
            return {
                'status': 'error',
                'message': f"Tool '{tool_name}' not found",
                'available_tools': list(self.available_tools.keys())
            }
        
        try:
            tool_function = self.available_tools[tool_name]['function']
            print(f"🔧 Executing tool: {tool_name} with parameters: {parameters}")
            
            # Add session_manager to parameters if the tool supports it
            if session_manager is not None:
                parameters['session_manager'] = session_manager
            
            # Execute the tool
            result = tool_function(**parameters)
            
            # Handle persistent objects (like RAG systems)
            if tool_name == 'document_processor' and result.get('status') == 'success':
                # Store the RAG system for future use
                if 'advanced_rag_system' in result and result['advanced_rag_system']:
                    self.persistent_objects['advanced_rag_system'] = result['advanced_rag_system']
                    print(f"💾 Stored RAG system for future document queries")
                
                # Store processed chunks
                if 'chunks' in result:
                    self.persistent_objects['document_chunks'] = result['chunks']
                    print(f"💾 Stored {len(result['chunks'])} chunks for future use")
            
            # Store result as usual
            self.recent_tool_results[tool_name] = result
            
            return {
                'status': 'success',
                'tool_name': tool_name,
                'parameters': parameters,
                'result': result,
                'timestamp': datetime.now().isoformat()
            }
        
        except Exception as e:
            return {
                'status': 'error',
                'tool_name': tool_name,
                'parameters': parameters,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
    
    def enhance_llm_response(self, llm_response: str, context: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Analyze LLM response, detect tool needs, execute tools, and enhance the response.
        """
        # Detect what tools should be called (now with context awareness)
        tool_calls = self.detect_tool_needs(llm_response, context)
        
        if not tool_calls:
            return {
                'enhanced_response': llm_response,
                'tools_used': [],
                'tool_results': [],
                'should_regenerate_response': False
            }
        
        # Extract session_manager from context if available
        session_manager = context.get('session_manager') if context else None
        
        # Execute detected tools
        tool_results = []
        for tool_call in tool_calls:
            print(f"🎯 {tool_call['reason']}")
            result = self.execute_tool(tool_call['tool_name'], tool_call['parameters'], session_manager)
            tool_results.append(result)
            
            # Store successful tool results for future context
            if result['status'] == 'success':
                self.recent_tool_results[tool_call['tool_name']] = result['result']
        
        # Check if we should regenerate the LLM response with tool context
        if self._should_regenerate_with_tools(tool_results):
            return {
                'enhanced_response': llm_response,  # Original response for now
                'tools_used': [call['tool_name'] for call in tool_calls],
                'tool_results': tool_results,
                'should_regenerate_response': True,
                'tool_context': self._create_tool_context(tool_results)
            }
        else:
            # Enhance the response with tool results (current approach)
            enhanced_response = self._integrate_tool_results(llm_response, tool_results)
            
            return {
                'enhanced_response': enhanced_response,
                'tools_used': [call['tool_name'] for call in tool_calls],
                'tool_results': tool_results,
                'should_regenerate_response': False
            }
    
    def _should_regenerate_with_tools(self, tool_results: List[Dict[str, Any]]) -> bool:
        """Determine if we should regenerate the LLM response with tool context"""
        # For now, always integrate post-hoc, but this could be enhanced
        # to regenerate for critical tools like flights
        for result in tool_results:
            if result['status'] == 'success' and result['tool_name'] == 'flight_planner':
                return False  # Could be True for regeneration
        return False
    
    def _create_tool_context(self, tool_results: List[Dict[str, Any]]) -> str:
        """Create context string to prepend to LLM prompt for regeneration"""
        context = "\n\nTOOL RESULTS AVAILABLE:\n"
        for result in tool_results:
            if result['status'] == 'success':
                tool_name = result['tool_name']
                result_data = result['result']
                context += f"\n{tool_name.upper()} RESULTS:\n{json.dumps(result_data, indent=2)}\n"
        context += "\nPlease incorporate these tool results naturally into your response.\n"
        return context
    
    def _integrate_tool_results(self, original_response: str, tool_results: List[Dict[str, Any]]) -> str:
        """Enhanced result integration including document processing tools."""
        enhanced_response = original_response
        
        for tool_result in tool_results:
            if tool_result['status'] == 'success':
                tool_name = tool_result['tool_name']
                result_data = tool_result['result']
                
                if tool_name == 'document_query':
                    # Format document query results
                    query_text = "\n\n" + "="*50 + "\n"
                    query_text += f"🔍 **DOCUMENT SEARCH RESULTS**\n"
                    query_text += "="*50 + "\n"
                    
                    query_text += f"❓ Query: {result_data.get('query', 'N/A')}\n"
                    query_text += f"📁 Source: {result_data.get('source_file', 'N/A')}\n"
                    query_text += f"📊 Total Chunks: {result_data.get('total_chunks', 0)}\n"
                    
                    # Show enhanced answer if available (from advanced RAG)
                    if result_data.get('enhanced_answer'):
                        query_text += f"\n📄 **ANSWER:**\n{result_data['enhanced_answer']}\n"
                    elif result_data.get('relevant_chunks'):
                        # Fallback to showing relevant chunks
                        query_text += f"🔍 Relevant Chunks Found: {result_data.get('relevant_chunks_found', 0)}\n"
                        query_text += "\n📄 **RELEVANT CONTENT:**\n"
                        for chunk in result_data['relevant_chunks'][:3]:  # Show first 3 chunks
                            query_text += f"   {chunk['chunk_number']}. {chunk['content'][:200]}...\n"
                    else:
                        query_text += f"🔍 Relevant Chunks Found: {result_data.get('relevant_chunks_found', 0)}\n"
                    
                    query_text += f"\n💡 {result_data.get('summary', 'Query completed.')}\n"
                    query_text += "="*50
                    
                    enhanced_response = query_text + "\n\n" + result_data.get('query', original_response)
                    
                elif tool_name == 'document_processor':
                    # Format document processing results
                    doc_text = "\n\n" + "="*50 + "\n"
                    doc_text += "📄 **DOCUMENT PROCESSING COMPLETE!**\n"
                    doc_text += "="*50 + "\n"
                    
                    doc_text += f"📁 Source: {result_data.get('source_file', 'N/A')}\n"
                    doc_text += f"📊 Document Type: {result_data.get('doc_type', 'N/A')}\n"
                    doc_text += f"📄 Total Chunks: {result_data.get('total_chunks', 0)}\n"
                    doc_text += f"⚙️ Processing Mode: {result_data.get('processing_mode', 'N/A')}\n"
                    
                    if result_data.get('advanced_rag_system'):
                        doc_text += f"🧠 RAG System: ✅ Initialized and ready for queries\n"
                    
                    doc_text += "\n" + "="*50 + "\n"
                    doc_text += "💡 Document is now ready! You can:\n"
                    doc_text += "   - Ask questions about the document content\n"
                    doc_text += "   - Request summaries or analysis\n"
                    doc_text += "   - Search for specific information\n"
                    doc_text += "="*50
                    
                    enhanced_response = doc_text + "\n\n" + original_response
                
                elif tool_name == 'flight_planner' and 'flight_options' in result_data:
                    # Format flight results prominently at the top
                    flight_text = "\n\n" + "="*50 + "\n"
                    flight_text += "🛫 **FLIGHT SEARCH RESULTS FOUND!**\n"
                    flight_text += "="*50 + "\n"
                    
                    params = tool_result['parameters']
                    flight_text += f"✈️ Route: {params['origin']} → {params['destination']}\n"
                    flight_text += f"📅 Dates: {params['departure_date']} to {params['return_date']}\n\n"
                    
                    for i, flight in enumerate(result_data['flight_options'], 1):
                        stops_text = "Direct" if flight['stops'] == 0 else f"{flight['stops']} stop(s)"
                        flight_text += f"✈️ Option {i}: {flight['airline']}\n"
                        flight_text += f"   💰 Price: ${flight['price']:.2f}\n"
                        flight_text += f"   🛑 Stops: {stops_text}\n"  
                        flight_text += f"   🕐 Departure: {flight['departure_time']}\n\n"
                    
                    flight_text += "="*50 + "\n"
                    flight_text += "💡 These are your current flight options! You can now:\n"
                    flight_text += "   - Choose one of these flights\n"
                    flight_text += "   - Ask for different dates or airlines\n"
                    flight_text += "   - Continue to the next step (accommodation)\n"
                    flight_text += "="*50
                    
                    # Add flight results at the beginning for prominence
                    enhanced_response = flight_text + "\n\n" + original_response
                    
                elif tool_name == 'hotel_planner' and 'hotel_options' in result_data:
                    # Format hotel results prominently
                    hotel_text = "\n\n" + "="*50 + "\n"
                    hotel_text += "🏨 **HOTEL SEARCH RESULTS FOUND!**\n"
                    hotel_text += "="*50 + "\n"
                    
                    params = tool_result['parameters']
                    hotel_text += f"🏨 Location: {params['location'].title()}\n"
                    hotel_text += f"📅 Dates: {params['checkin_date']} to {params['checkout_date']}\n\n"
                    
                    for i, hotel in enumerate(result_data['hotel_options'], 1):
                        amenities_text = ", ".join(hotel['amenities'][:3])
                        hotel_text += f"🏨 Option {i}: {hotel['name']}\n"
                        hotel_text += f"   💰 Price: ${hotel['price']:.2f}/night\n"
                        hotel_text += f"   ⭐ Rating: {hotel['rating']}/5.0\n"
                        hotel_text += f"   🛏️ Room: {hotel['room_type']}\n"
                        hotel_text += f"   🎯 Amenities: {amenities_text}\n\n"
                    
                    hotel_text += "="*50 + "\n"
                    hotel_text += "💡 These are your accommodation options! You can now:\n"
                    hotel_text += "   - Choose one of these hotels\n"
                    hotel_text += "   - Ask for different dates or locations\n"
                    hotel_text += "   - Continue to the next step (activities)\n"
                    hotel_text += "="*50
                    
                    enhanced_response = hotel_text + "\n\n" + original_response
                    
                elif tool_name == 'hotel_selector' and 'selected_hotel' in result_data:
                    # Format hotel selection confirmation
                    selection_text = "\n\n" + "="*50 + "\n"
                    selection_text += "✅ **HOTEL BOOKING CONFIRMED!**\n"
                    selection_text += "="*50 + "\n"
                    
                    selected = result_data['selected_hotel']
                    selection_text += f"🎯 Selected: Option {result_data['option_number']}\n"
                    selection_text += f"🏨 Hotel: {selected['name']}\n"
                    selection_text += f"💰 Price: ${selected['price']:.2f}/night\n"
                    selection_text += f"⭐ Rating: {selected['rating']}/5.0\n"
                    selection_text += f"🛏️ Room: {selected['room_type']}\n"
                    selection_text += f"📍 Location: {selected['location']}\n\n"
                    
                    selection_text += "📋 **ITINERARY UPDATED:**\n"
                    itinerary = result_data['itinerary_update']
                    selection_text += f"   Hotel: {itinerary['hotel_confirmation']}\n"
                    selection_text += f"   Total Cost: ${itinerary['total_accommodation_cost']:.2f}\n\n"
                    
                    selection_text += "="*50 + "\n"
                    selection_text += f"💡 {result_data['confirmation_message']}\n"
                    if 'next_steps' in result_data and result_data['next_steps']:
                        selection_text += f"🎯 Next Steps: {result_data['next_steps']}\n"
                    selection_text += "="*50
                    
                    enhanced_response = selection_text + "\n\n" + original_response
                    
                elif tool_name == 'restaurant_planner' and 'restaurant_options' in result_data:
                    # Format restaurant results prominently
                    restaurant_text = "\n\n" + "="*50 + "\n"
                    restaurant_text += "🍽️ **RESTAURANT SEARCH RESULTS FOUND!**\n"
                    restaurant_text += "="*50 + "\n"
                    
                    params = tool_result['parameters']
                    restaurant_text += f"🍽️ Location: {params['location'].title()}\n"
                    restaurant_text += f"📅 Date: {params['date']}\n"
                    restaurant_text += f"👥 Party Size: {params['party_size']} people\n\n"
                    
                    for i, restaurant in enumerate(result_data['restaurant_options'], 1):
                        specialties_text = ", ".join(restaurant['specialties'][:2])
                        restaurant_text += f"🍽️ Option {i}: {restaurant['name']}\n"
                        restaurant_text += f"   🍴 Cuisine: {restaurant['cuisine']}\n"
                        restaurant_text += f"   💰 Price: {restaurant['price_range']}\n"
                        restaurant_text += f"   ⭐ Rating: {restaurant['rating']}/5.0\n"
                        restaurant_text += f"   🕐 Available: {restaurant['available_time']}\n"
                        restaurant_text += f"   🎯 Known for: {specialties_text}\n\n"
                    
                    restaurant_text += "="*50 + "\n"
                    restaurant_text += "💡 These are your dining options! You can now:\n"
                    restaurant_text += "   - Choose one of these restaurants\n"
                    restaurant_text += "   - Ask for different times or cuisine\n"
                    restaurant_text += "   - Continue with your trip planning\n"
                    restaurant_text += "="*50
                    
                    enhanced_response = restaurant_text + "\n\n" + original_response
                    
                elif tool_name == 'restaurant_selector' and 'selected_restaurant' in result_data:
                    # Format restaurant selection confirmation
                    selection_text = "\n\n" + "="*50 + "\n"
                    selection_text += "✅ **RESTAURANT RESERVATION CONFIRMED!**\n"
                    selection_text += "="*50 + "\n"
                    
                    selected = result_data['selected_restaurant']
                    selection_text += f"🎯 Selected: Option {result_data['option_number']}\n"
                    selection_text += f"🍽️ Restaurant: {selected['name']}\n"
                    selection_text += f"🍴 Cuisine: {selected['cuisine']}\n"
                    selection_text += f"💰 Price Range: {selected['price_range']}\n"
                    selection_text += f"⭐ Rating: {selected['rating']}/5.0\n"
                    selection_text += f"🕐 Time: {selected['available_time']}\n"
                    selection_text += f"📍 Location: {selected['location']}\n\n"
                    
                    selection_text += "📋 **ITINERARY UPDATED:**\n"
                    itinerary = result_data['itinerary_update']
                    selection_text += f"   Reservation: {itinerary['restaurant_reservation']}\n"
                    selection_text += f"   Time: {itinerary['reservation_time']}\n"
                    selection_text += f"   Party Size: {itinerary['party_size']}\n\n"
                    
                    selection_text += "="*50 + "\n"
                    selection_text += f"💡 {result_data['confirmation_message']}\n"
                    if 'next_steps' in result_data and result_data['next_steps']:
                        selection_text += f"🎯 Next Steps: {result_data['next_steps']}\n"
                    selection_text += "="*50
                    
                    enhanced_response = selection_text + "\n\n" + original_response
                    
                elif tool_name == 'flight_selector' and 'selected_flight' in result_data:
                    # Format flight selection confirmation
                    selection_text = "\n\n" + "="*50 + "\n"
                    selection_text += "✅ **FLIGHT SELECTION CONFIRMED!**\n"
                    selection_text += "="*50 + "\n"
                    
                    selected = result_data['selected_flight']
                    selection_text += f"🎯 Selected: Option {result_data['option_number']}\n"
                    selection_text += f"✈️ Airline: {selected['airline']}\n"
                    selection_text += f"💰 Price: ${selected['price']:.2f}\n"
                    selection_text += f"🛑 Stops: {'Direct' if selected['stops'] == 0 else str(selected['stops']) + ' stop(s)'}\n"
                    selection_text += f"🕐 Departure: {selected['departure_time']}\n"
                    selection_text += f"📅 Route: {selected['route']}\n\n"
                    
                    selection_text += "📋 **ITINERARY UPDATED:**\n"
                    itinerary = result_data['itinerary_update']
                    selection_text += f"   Flight: {itinerary['flight_confirmation']}\n"
                    selection_text += f"   Total Cost: ${itinerary['total_cost']:.2f}\n\n"
                    
                    selection_text += "="*50 + "\n"
                    selection_text += f"💡 {result_data['confirmation_message']}\n"
                    if 'next_steps' in result_data and result_data['next_steps']:
                        selection_text += f"🎯 Next Steps: {result_data['next_steps']}\n"
                    selection_text += "="*50
                    
                    enhanced_response = selection_text + "\n\n" + original_response
                    
                else:
                    # Generic tool result integration
                    enhanced_response += f"\n\n🔧 **{tool_name.upper()} RESULTS:**\n{json.dumps(result_data, indent=2)}"
            else:
                # Tool execution failed
                enhanced_response += f"\n\n⚠️ **Tool Error:** {tool_result['error']}"
        
        return enhanced_response
