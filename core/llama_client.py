"""
LLaMA Client Module for CognitiveLattice
Handles all LLaMA model interactions, prompts, and content analysis
"""

import requests
import json


# === Summarization templates by content type ===
SUMMARY_TEMPLATES = {
    "novel": (
        "[INST] Extract and summarize the factual content from this novel excerpt. "
        "Include: character names, locations, actions taken, dialogue content, "
        "events that occur, and specific details mentioned. "
        "Report only what explicitly happens - do not interpret emotions or themes. "
        "Be comprehensive but factual.\n\n"
        "TEXT:\n{text}\n\n"
        "FACTUAL SUMMARY:[/INST]"
    ),
    "scientific_paper": (
        "[INST] Extract the key factual information from this scientific text. "
        "Include: research objectives, methods used, data presented, "
        "results obtained, and conclusions stated. "
        "Report the facts without interpretation or analysis.\n\n"
        "TEXT:\n{text}\n\n"
        "FACTUAL SUMMARY:[/INST]"
    ),
    "technical_manual": (
        "[INST] Extract the procedural and technical information from this text. "
        "Include: specific steps, measurements, specifications, requirements, "
        "safety instructions, and technical details mentioned. "
        "List facts and procedures without commentary.\n\n"
        "TEXT:\n{text}\n\n"
        "FACTUAL SUMMARY:[/INST]"
    ),
    "default": (
        "[INST] Extract the key factual information from this text. "
        "Include: who, what, when, where, and specific details mentioned. "
        "Report only the facts presented without interpretation or analysis.\n\n"
        "TEXT:\n{text}\n\n"
        "FACTUAL SUMMARY:[/INST]"
    ),
}


def run_llama_inference(prompt, server_url="http://localhost:8080/completion"):
    """
    Basic LLaMA inference without context.
    
    Args:
        prompt: Text prompt to send to LLaMA
        server_url: URL of the LLaMA server
        
    Returns:
        Generated text response or "CONFUSED" on error
    """
    print("🔧 Sending prompt to llama-server...")
    try:
        response = requests.post(
            server_url,
            headers={"Content-Type": "application/json"},
            json={
                "prompt": prompt,
                "n_predict": 512,
                "temperature": 0.3,
                "top_p": 0.95,
                "repeat_penalty": 1.1,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        print("✅ LLaMA output:")
        print(data['content'])
        return data['content'].strip()
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return "CONFUSED"


def run_llama_inference_with_context(prompt, context=None, server_url="http://localhost:8080/completion"):
    """
    LLaMA inference with optional context from previous chunks.
    
    Args:
        prompt: Text prompt to send to LLaMA
        context: Optional context dictionary with previous_chunks
        server_url: URL of the LLaMA server
        
    Returns:
        Generated text response or "CONFUSED" on error
    """
    if context and context["previous_chunks"]:
        # Add context to the prompt
        context_summary = "\n".join([
            f"Previous chunk {chunk['chunk_id']}: {chunk['content'][:100]}..."
            for chunk in context["previous_chunks"][-2:]  # Last 2 chunks
        ])
        
        enhanced_prompt = f"""[INST] Context from previous chunks:
{context_summary}

{prompt}[/INST]"""
        
        print(f"🧠 Using context from {len(context['previous_chunks'])} previous chunks")
    else:
        enhanced_prompt = prompt
    
    return run_llama_inference(enhanced_prompt, server_url)


def diagnose_content_type(sample_text):
    """
    Use LLaMA to classify the document type.
    
    Args:
        sample_text: Sample text from the document
        
    Returns:
        Document type classification string
    """
    diagnose_prompt = f"""[INST] Classify this text as one of: novel, scientific_paper, technical_manual, or default.
    
    TEXT: {sample_text[:500]}
    
    Respond with only the classification word.[/INST]"""
    
    diagnosis = run_llama_inference(diagnose_prompt).strip().lower()
    
    # Map variations to our template keys
    if any(word in diagnosis for word in ["novel", "fiction", "story", "literature"]):
        return "novel"
    elif any(word in diagnosis for word in ["scientific", "research", "study", "paper", "journal"]):
        return "scientific_paper"
    elif any(word in diagnosis for word in ["manual", "technical", "instruction", "procedure", "guide"]):
        return "technical_manual"
    else:
        return "default"


def diagnose_user_intent(user_query, server_url="http://localhost:8080/completion"):
    """
    Use LLaMA to classify the user's intent.

    Args:
        user_query: The user's request.
        server_url: URL of the LLaMA server.

    Returns:
        A dictionary with 'intent' and 'action'.
    """
    prompt = f"""[INST] Analyze the user's request to determine the type of request and action needed.

Intent Types:
- "chat": Simple conversational question or greeting (e.g., "How are you?", "What's the weather like?")
- "query": Simple factual question that doesn't require document analysis (e.g., "How is Myrtle Beach this time of year?")
- "analysis": Request to analyze, summarize, or extract information from a document
- "broad": Request for overall summary or analysis of entire document
- "task": Complex structured task requiring multiple steps (e.g., "Plan a trip", "Create a business plan")
- "web_automation": Request to navigate websites, interact with web pages, or perform web automation (e.g., "Navigate to chipotle.com", "Order food online", "Click the login button")

Action Types:
- "chat": Conversational response
- "query": Simple question answering
- "analyze": Analyze document content
- "summarize": Summarize document
- "extract": Extract specific information
- "plan": Create a multi-step plan
- "web_navigate": Navigate and interact with websites

User Request: "{user_query}"

Respond with a JSON object with two keys: "intent" and "action".

JSON Response:[/INST]"""

    response_text = run_llama_inference(prompt, server_url)

    try:
        # The model might return markdown ```json ... ```, so we clean it
        if response_text.startswith("```json"):
            response_text = response_text[7:-4].strip()
        intent_data = json.loads(response_text)
        if isinstance(intent_data, dict) and "intent" in intent_data and "action" in intent_data:
            # Basic validation
            valid_intents = ["chat", "query", "analysis", "broad", "task", "web_automation"]
            if intent_data.get("intent") not in valid_intents:
                intent_data["intent"] = "query" # Default to simple query
            return intent_data
        else:
            # Fallback if JSON is not as expected
            print("⚠️ Intent diagnosis returned malformed JSON, falling back.")
            if "summarize" in user_query.lower() or "overview" in user_query.lower():
                return {"intent": "broad", "action": "summarize"}
            elif "plan" in user_query.lower() or "help me" in user_query.lower():
                return {"intent": "task", "action": "plan"}
            elif any(word in user_query.lower() for word in ["navigate", "website", "click", "order", "login", "web", "browser"]):
                return {"intent": "web_automation", "action": "web_navigate"}
            elif any(word in user_query.lower() for word in ["hello", "hi", "how are you", "thanks", "thank you"]):
                return {"intent": "chat", "action": "chat"}
            return {"intent": "query", "action": "query"}
    except json.JSONDecodeError:
        # Fallback for non-JSON response
        print("⚠️ Intent diagnosis failed (not JSON), falling back.")
        if "summarize" in user_query.lower() or "overview" in user_query.lower():
            return {"intent": "broad", "action": "summarize"}
        elif "plan" in user_query.lower() or "help me" in user_query.lower():
            return {"intent": "task", "action": "plan"}
        elif any(word in user_query.lower() for word in ["navigate", "website", "click", "order", "login", "web", "browser"]):
            return {"intent": "web_automation", "action": "web_navigate"}
        elif any(word in user_query.lower() for word in ["hello", "hi", "how are you", "thanks", "thank you"]):
            return {"intent": "chat", "action": "chat"}
        return {"intent": "query", "action": "query"}


def extract_key_facts(summary_text, doc_type):
    """
    Use LLaMA to extract structured key facts from the summary.
    
    Args:
        summary_text: Text summary to analyze
        doc_type: Document type for context
        
    Returns:
        Dictionary of extracted facts (JSON parsed or raw facts)
    """
    fact_prompt = f"""[INST] Extract key facts from this {doc_type} summary as JSON:
{summary_text}

Return only a JSON object with relevant keys like: characters, locations, events, dates, etc.[/INST]"""
    
    facts_json = run_llama_inference(fact_prompt)
    try:
        return json.loads(facts_json)
    except:
        return {"raw_facts": facts_json}