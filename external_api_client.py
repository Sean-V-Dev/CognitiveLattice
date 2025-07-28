"""
External API Integration for TokenSight
Sends relevant chunks to external APIs (OpenAI, Claude, etc.) for enhanced analysis
"""

import os
import json
import requests
import base64
from typing import List, Dict, Any, Optional

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
    """
    Client for sending TokenSight chunks to external APIs
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
    
    def analyze_chunk_with_external_api(self, chunk_data: Dict[str, Any], analysis_type: str = "comprehensive") -> Dict[str, Any]:
        """
        Send a chunk to external API for enhanced analysis
        
        Args:
            chunk_data: The chunk metadata from TokenSight RAG system
            analysis_type: Type of analysis ("comprehensive", "factual", "technical", "visual")
        
        Returns:
            Enhanced analysis results from external API
        """
        print(f"🌐 Sending {chunk_data['chunk_id']} to {self.api_provider.upper()} for {analysis_type} analysis...")
        
        # Prepare the prompt based on analysis type
        prompt = self._create_analysis_prompt(chunk_data, analysis_type)
        
        try:
            if self.api_provider == "openai":
                response = self._call_openai_api(prompt, chunk_data)
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
    
    def _call_openai_api(self, prompt: str, chunk_data: Dict[str, Any]) -> Dict[str, Any]:
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
