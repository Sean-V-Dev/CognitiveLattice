"""
External API Integration for CognitiveLattice
Sends relevant chunks to external APIs (OpenAI, Claude, etc.) for enhanced analysis
"""

import os
import json
import requests
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime

# Try to load environment variables, but don't fail if dotenv isn't available
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    print("💡 python-dotenv not available, reading .env manually...")
    # Manually read .env file if dotenv is not available
    env_path = ".env"
    if os.path.exists(env_path):
        with open(env_path, 'r') as f:
            for line in f:
                if line.strip() and not line.startswith('#'):
                    key, value = line.strip().split('=', 1)
                    os.environ[key] = value

class ExternalAPIClient:
    def summarize_analyses(self, analyses: List[Dict[str, Any]], original_query: str) -> Dict[str, Any]:
        """
        Sends multiple analysis results to the external API for a final summary.
        """
        print(f"🌐 Summarizing {len(analyses)} analysis results for query: '{original_query}'")

        # Prepare the content for the summarization prompt
        # We'll extract just the core analysis to keep the prompt focused
        core_analyses = [
            res.get("external_analysis", {}) for res in analyses if "external_analysis" in res
        ]
        if not core_analyses:
            print("⚠️ No analysis results to summarize.")
            return {"error": "No content to summarize."}
            
        analysis_json_str = json.dumps(core_analyses, indent=2)

        prompt = f"""The user asked the following question: \"{original_query}\"

Based on the following chunk-by-chunk JSON analyses of a document, synthesize a single, comprehensive, and user-friendly answer.
Do not present the information on a \"per-chunk\" basis. Instead, consolidate all the information into a unified response. For example, if the user asks for characters, provide a single list of all characters found across all chunks under a \"Characters\" heading.

Here is the detailed analysis data from multiple document chunks:
{analysis_json_str}

Please provide a final, consolidated answer based on this data. The answer should be in a clear, readable format. Interpret the JSON and present the information naturally.
"""

        try:
            # Using gpt-4o-mini for cost-effectiveness and speed
            model = "gpt-4o-mini"
            messages = [
                {"role": "system", "content": "You are an expert synthesis agent. Your job is to combine multiple detailed JSON analyses into a single, coherent, and user-friendly answer."},
                {"role": "user", "content": prompt}
            ]

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            payload = {
                "model": model,
                "messages": messages,
                "max_tokens": 2000,
                "temperature": 0.5,
            }

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120 # Increased timeout for potentially large summarization task
            )

            response.raise_for_status()
            response_json = response.json()
            
            summary_content = response_json["choices"][0]["message"]["content"]
            
            print("✅ Summarization complete.")
            return {
                "summary_text": summary_content,
                "tokens_used": response_json.get("usage", {}).get("total_tokens"),
                "model_used": response_json.get("model", model)
            }

        except Exception as e:
            print(f"Error summarizing analyses: {e}")
            return {"error": str(e), "summary_text": "Could not generate summary."}

    def create_task_plan(self, user_query: str) -> Dict[str, Any]:
        """
        Asks the external API to create a step-by-step plan for a given query.
        """
        print(f"📋 Asking external API to create a plan for: '{user_query}'")
        
        # The current date is added to give the LLM temporal context.
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        prompt = f"""The user wants to accomplish the following task: "{user_query}"

Your role is to act as an expert planner. Break down this task into a series of clear, actionable steps.
Do NOT attempt to execute the steps yourself.
Return ONLY a numbered list of the steps required to complete the task.

CRITICAL REQUIREMENT - READ CAREFULLY:
You MUST combine research and booking actions into single steps. This is absolutely required.
Do NOT create separate "research" and "book" steps - they MUST be combined.

FORBIDDEN PATTERNS (DO NOT DO THIS):
❌ Step X: "Research flights"  Step Y: "Book flights"
❌ Step X: "Find hotels"  Step Y: "Book hotel" 
❌ Step X: "Look for restaurants"  Step Y: "Make reservations"

REQUIRED PATTERNS (DO THIS INSTEAD):
✅ "Research and select round-trip flights, comparing prices and times"
✅ "Find and book accommodation that fits budget and location preferences"
✅ "Plan dining options and make necessary restaurant reservations"

EXAMPLE FOR TRAVEL PLANNING:
User Query: "Help me plan a trip to Paris"
CORRECT Response:
1. Determine travel dates and duration
2. Research and select round-trip flights to Paris (compare airlines, prices, schedules)
3. Find and book accommodation for the stay (hotels, Airbnb, etc.)
4. Plan daily itinerary with attractions, activities, and dining
5. Prepare travel documents and pack for the trip

WRONG Response (DO NOT DO):
1. Research flight options ❌
2. Book selected flight ❌
3. Research hotels ❌  
4. Book hotel room ❌

The current date is {current_date}. 

Remember: COMBINE research and booking into single steps. Do not separate them.

Now create the plan for: "{user_query}"
"""

        try:
            model = "gpt-4o-mini" 
            messages = [
                {"role": "system", "content": "You are a world-class planner. CRITICAL REQUIREMENT: You MUST combine research and booking actions into single cohesive steps. NEVER separate 'research X' and 'book X' into different steps - they must be combined. You only provide consolidated plans, you do not execute them."},
                {"role": "user", "content": prompt}
            ]
            
            response_data = self._call_openai_api(model, messages, max_tokens=1000, temperature=0.6)
            
            plan_text = response_data["choices"][0]["message"]["content"]
            
            # Parse the plan text into a list of steps
            plan_steps = []
            lines = plan_text.strip().split('\n')
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('*')):
                    # Remove numbering and bullet points
                    clean_step = line
                    if '. ' in line:
                        clean_step = line.split('. ', 1)[1] if len(line.split('. ', 1)) > 1 else line
                    elif line.startswith('- '):
                        clean_step = line[2:]
                    elif line.startswith('* '):
                        clean_step = line[2:]
                    
                    if clean_step.strip():
                        plan_steps.append(clean_step.strip())
            
            # Fallback: if no steps parsed, split by lines and filter
            if not plan_steps:
                for line in lines:
                    line = line.strip()
                    if line and len(line) > 10:  # Reasonable step length
                        plan_steps.append(line)
            
            return {
                "success": True,
                "plan": plan_steps,  # Return as 'plan' not 'plan_text'
                "plan_text": plan_text,  # Keep original text too
                "tokens_used": response_data.get("usage", {}).get("total_tokens", 0)
            }

        except Exception as e:
            print(f"❌ Error creating task plan: {e}")
            return {"success": False, "error": str(e)}

    """
    Client for sending CognitiveLattice chunks to external APIs
    """
    
    def __init__(self, api_provider="openai"):
        self.api_provider = api_provider
        self.api_key = self._load_api_key()
        self.base_url = self._get_base_url()
        
    def _load_api_key(self) -> str:
        """Load API key from environment"""
        if self.api_provider == "openai":
            key = os.getenv("OPENAI_API_KEY")
            if not key:
                raise ValueError("OPENAI_API_KEY not found in environment variables")
            return key
        else:
            raise ValueError(f"Unsupported API provider: {self.api_provider}")
    
    def _get_base_url(self) -> str:
        """Get base URL for API provider"""
        if self.api_provider == "openai":
            return "https://api.openai.com/v1"
        else:
            raise ValueError(f"Unsupported API provider: {self.api_provider}")
    
    def query_external_api(self, query: str) -> str:
        """
        Send a direct query to external API for simple questions and chat
        
        Args:
            query (str): The user's question or chat message
            
        Returns:
            str: The response from the external API
        """
        try:
            print(f"🌐 Sending direct query to external API...")
            
            # Get current date for context
            from datetime import datetime
            current_date = datetime.now().strftime("%B %d, %Y")
            current_month = datetime.now().strftime("%B")
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            messages = [
                {"role": "system", "content": f"You are a helpful AI assistant. Today's date is {current_date}. When answering questions about 'this time of year' or current conditions, use {current_month} {datetime.now().year} as the reference point. Provide clear, informative responses to user questions."},
                {"role": "user", "content": query}
            ]
            
            payload = {
                "model": "gpt-4o-mini",  # Using cost-effective model for simple queries
                "messages": messages,
                "max_tokens": 1000,
                "temperature": 0.7,
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            response.raise_for_status()
            response_json = response.json()
            
            return response_json["choices"][0]["message"]["content"]
            
        except Exception as e:
            print(f"❌ Direct query failed: {e}")
            return f"I apologize, but I'm having trouble connecting to provide an answer right now. Error: {str(e)}"
    
    def analyze_chunk_with_external_api(self, chunk_data: Dict[str, Any], analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Send a chunk to external API for enhanced analysis
        
        Args:
            chunk_data: The chunk metadata from CognitiveLattice RAG system
            analysis_type: Type of analysis ("comprehensive", "factual", "technical", "visual")
        
        Returns:
            Enhanced analysis results from external API
        """
        print(f"🌐 Sending {chunk_data['chunk_id']} to {self.api_provider.upper()} for {analysis_type} analysis...")
        
        # Prepare the prompt based on analysis type
        prompt = self._create_analysis_prompt(chunk_data, analysis_type)
        
        try:
            if self.api_provider == "openai":
                response = self._call_openai_api_for_analysis(prompt, chunk_data)
            else:
                raise ValueError(f"Unsupported provider: {self.api_provider}")
            
            # Process and structure the response
            enhanced_analysis = self._process_api_response(response, chunk_data, analysis_type)
            
            print(f"✅ Enhanced analysis completed for {chunk_data['chunk_id']}")
            return enhanced_analysis
            
        except Exception as e:
            print(f"❌ External API analysis failed for {chunk_data['chunk_id']}: {e}")
            return self._create_fallback_response(chunk_data, str(e))
    
    def _create_analysis_prompt(self, chunk_data: Dict[str, Any], analysis_type: str) -> str:
        """Create specialized prompts for different analysis types"""
        
        base_content = chunk_data.get("content", "")
        chunk_id = chunk_data.get("chunk_id", "unknown")
        source_type = chunk_data.get("source_type", "unknown")
        
        prompts = {
            "comprehensive": f"""Analyze this content chunk from a {source_type} document and provide comprehensive insights:

CHUNK ID: {chunk_id}
CONTENT:
{base_content}

Please provide:
1. **Key Insights**: Main topics, themes, and important information
2. **Factual Extraction**: Specific facts, numbers, dates, names, locations
3. **Relationships**: Connections to other concepts or entities mentioned
4. **Action Items**: Any procedures, instructions, or actionable information
5. **Context Clues**: Implicit information that helps understand the broader document
6. **Questions Raised**: What questions does this content raise that might be answered elsewhere?

Format your response as structured JSON with these categories.""",

            "factual": f"""Extract and structure all factual information from this {source_type} content:

CHUNK ID: {chunk_id}
CONTENT:
{base_content}

Extract as structured data:
- Entities (people, places, organizations, products)
- Numbers and measurements
- Dates and times
- Procedures and steps
- Technical specifications
- Requirements and constraints

Return as structured JSON.""",

            "technical": f"""Provide technical analysis of this {source_type} content:

CHUNK ID: {chunk_id}
CONTENT:
{base_content}

Focus on:
- Technical procedures and instructions
- Specifications and requirements
- Safety considerations
- Troubleshooting information
- Installation or setup steps
- Maintenance procedures

Return detailed technical breakdown as JSON.""",

            "visual": f"""Analyze this content for visual and multimodal elements:

CHUNK ID: {chunk_id}
CONTENT:
{base_content}

Identify:
- References to visual elements (diagrams, charts, images)
- Spatial relationships and layouts
- Visual cues and formatting
- Cross-references to figures or tables
- Description of visual processes

Return analysis as structured JSON."""
        }
        
        return prompts.get(analysis_type, prompts["comprehensive"])
    
    def _call_openai_api_for_analysis(self, prompt: str, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
        """Make API call to OpenAI"""
        
        # Check if chunk has associated images that need vision model
        has_images = "image_metadata" in chunk_data or chunk_data.get("modality") == "visual"
        
        if has_images:
            model = "gpt-4o-mini"  # Use mini for vision tasks too
            messages = self._prepare_vision_messages(prompt, chunk_data)
        else:
            model = "gpt-4o-mini"  # Changed from gpt-4-turbo-preview to mini
            messages = [
                {"role": "system", "content": "You are an expert document analyst. Provide structured, detailed analysis in JSON format."},
                {"role": "user", "content": prompt}
            ]
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 2000,
            "temperature": 0.3,
            "response_format": {"type": "json_object"} if not has_images else None
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        response.raise_for_status()
        return response.json()
    
    def _prepare_vision_messages(self, prompt: str, chunk_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Prepare messages for vision-enabled models"""
        messages = [
            {"role": "system", "content": "You are an expert multimodal document analyst. Analyze both text and visual content."}
        ]
        
        # Add text content
        user_message = {
            "role": "user",
            "content": [
                {"type": "text", "text": prompt}
            ]
        }
        
        # Add image if available
        if "image_metadata" in chunk_data:
            image_path = chunk_data["image_metadata"].get("file_path")
            if image_path and os.path.exists(image_path):
                try:
                    with open(image_path, "rb") as image_file:
                        image_data = base64.b64encode(image_file.read()).decode('utf-8')
                    
                    user_message["content"].append({
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_data}",
                            "detail": "high"
                        }
                    })
                except Exception as e:
                    print(f"⚠️ Could not load image {image_path}: {e}")
        
        messages.append(user_message)
        return messages
    
    def _process_api_response(self, response: Dict[str, Any], chunk_data: Dict[str, Any], analysis_type: str) -> Dict[str, Any]:
        """Process and structure the API response"""
        
        try:
            content = response["choices"][0]["message"]["content"]
            
            # Try to parse as JSON if possible
            try:
                analysis_result = json.loads(content)
            except json.JSONDecodeError:
                # If not JSON, create structured response
                analysis_result = {
                    "raw_analysis": content,
                    "analysis_type": analysis_type
                }
            
            # Add metadata
            enhanced_result = {
                "chunk_id": chunk_data["chunk_id"],
                "original_chunk": chunk_data,
                "external_analysis": analysis_result,
                "api_provider": self.api_provider,
                "analysis_type": analysis_type,
                "tokens_used": response["usage"]["total_tokens"],
                "model_used": response.get("model", "unknown"),
                "timestamp": json.dumps({"timestamp": "now"}),  # You'd use actual timestamp
                "confidence": "high" if response["usage"]["total_tokens"] > 100 else "medium"
            }
            
            return enhanced_result
            
        except Exception as e:
            return self._create_fallback_response(chunk_data, f"Response processing error: {e}")
    
    def _create_fallback_response(self, chunk_data: Dict[str, Any], error_msg: str) -> Dict[str, Any]:
        """Create fallback response when API fails"""
        return {
            "chunk_id": chunk_data["chunk_id"],
            "original_chunk": chunk_data,
            "external_analysis": {
                "error": error_msg,
                "fallback": True,
                "local_content": chunk_data.get("content", "")
            },
            "api_provider": self.api_provider,
            "analysis_type": "error",
            "confidence": "none"
        }
    
    def analyze_multiple_chunks(self, chunks: List[Dict[str, Any]], analysis_type: str = "comprehensive") -> List[Dict[str, Any]]:
        """
        Analyze multiple chunks with external API
        Includes rate limiting and error handling
        """
        results = []
        
        print(f"🌐 Processing {len(chunks)} chunks with external API...")
        
        for i, chunk in enumerate(chunks):
            try:
                result = self.analyze_chunk_with_external_api(chunk, analysis_type)
                results.append(result)
                
                # Basic rate limiting (adjust based on API limits)
                if i < len(chunks) - 1:  # Don't wait after last chunk
                    import time
                    time.sleep(1)  # 1 second between requests
                    
            except Exception as e:
                print(f"❌ Failed to process chunk {chunk.get('chunk_id', i)}: {e}")
                results.append(self._create_fallback_response(chunk, str(e)))
        
        print(f"✅ Completed external analysis of {len(results)} chunks")
        return results

    def _call_openai_api(self, model: str, messages: List[Dict[str, Any]], max_tokens: int, temperature: float) -> Dict[str, Any]:
        """Make API call to OpenAI with specified model and parameters"""
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        response.raise_for_status()
        return response.json()
    
def identify_relevant_chunks_for_external_analysis(chunk_metadata: List[Dict[str, Any]], 
                                                 criteria: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    """
    Identify which chunks should be sent to external API based on criteria
    
    Args:
        chunk_metadata: List of all chunks from RAG system
        criteria: Selection criteria (complexity, visual content, etc.)
    
    Returns:
        Filtered list of chunks for external analysis
    """
    if criteria is None:
        criteria = {
            "min_content_length": 200,
            "has_visual_content": True,
            "source_types": ["technical_manual", "scientific_paper"],
            "max_chunks": 10
        }
    
    relevant_chunks = []
    
    for chunk in chunk_metadata:
        # Apply filters
        content_length = len(chunk.get("content", ""))
        has_visual = chunk.get("modality") == "visual" or "image_metadata" in chunk
        source_type = chunk.get("source_type", "default")
        
        # Check criteria
        if criteria.get("min_content_length", 0) > 0:
            if content_length < criteria["min_content_length"]:
                continue
        
        if criteria.get("has_visual_content", False):
            if not has_visual:
                continue
        
        if criteria.get("source_types"):
            if source_type not in criteria["source_types"]:
                continue
        
        relevant_chunks.append(chunk)
        
        # Limit number of chunks
        if len(relevant_chunks) >= criteria.get("max_chunks", float('inf')):
            break
    
    print(f"🎯 Selected {len(relevant_chunks)} chunks for external API analysis")
    return relevant_chunks

def save_external_analysis_results(results: List[Dict[str, Any]], filepath: str = "external_analysis_results.json"):
    """Save external API analysis results to file"""
    
    analysis_summary = {
        "total_chunks_analyzed": len(results),
        "successful_analyses": len([r for r in results if not r["external_analysis"].get("error")]),
        "failed_analyses": len([r for r in results if r["external_analysis"].get("error")]),
        "api_provider": results[0]["api_provider"] if results else "unknown",
        "results": results
    }
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(analysis_summary, f, indent=2, ensure_ascii=False)
    
    print(f"💾 External analysis results saved to {filepath}")
    return analysis_summary
