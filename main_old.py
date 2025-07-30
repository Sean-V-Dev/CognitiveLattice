import re
import os
import json
import traceback
from typing import List, Dict, Any
from datetime import datetime
from utils.dictionary_manager import expand_dictionary, clean_input
from encoder.text_to_image import encode_text_to_image
from decoder.image_to_text import decode_image_to_text
from text_processor import extract_paragraphs, chunk_paragraphs
from file_handler import process_file
from llama_client import run_llama_inference_with_context, diagnose_content_type, extract_key_facts, SUMMARY_TEMPLATES, diagnose_user_intent
from page_extractor import integrate_page_based_extraction, PAGE_EXTRACTION_AVAILABLE
from memory_manager import search_memory, initialize_memory
from external_api_client import ExternalAPIClient, identify_relevant_chunks_for_external_analysis, save_external_analysis_results
from core.tool_manager import ToolManager
from core.cognitive_lattice import CognitiveLattice, SessionManager

# NEW: Advanced RAG system integration
from tokensight_advanced_rag import TokenSightAdvancedRAG


# === Initialize memory to store chunk summaries === #
memory = initialize_memory()

# Load encryption key
key_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config", "key.json")
with open(key_path, "r") as f:
    config = json.load(f)
    encryption_key = tuple(config["encryption_key"])

# === Main function for all executable code === #
def main():
    # === Initialize session manager and cognitive lattice === #
    session_manager = SessionManager()
    print(f"🧠 Cognitive Lattice initialized for session: {session_manager.lattice.session_id}")

    # === Initialize Tool Manager === #
    tool_manager = ToolManager()
    print(f"🔧 Tool Manager initialized")

    print("📋 TokenSight Enhanced PDF Processing")
    print("=" * 50)
    
    # Quick readiness check
    print("🔄 Checking system readiness...")
    try:
        # Test heavy imports that might cause delays
        from sentence_transformers import SentenceTransformer
        print("   ✅ AI models ready")
    except Exception as e:
        print(f"   ⚠️ AI models loading (first time may take 60+ seconds): {e}")
        print("   💡 For faster startup, run 'python startup.py' first")
    
    # === Ensure decoded.txt exists or create it === #
    decoded_path = "decoded.txt"
    source_input = "example.txt"  # or the original raw input
    enable_multimodal = source_input.endswith(".pdf")  # Enable multimodal for PDFs
    
    print(f"📄 Source: {source_input}")
    print(f"🖼️ Multimodal enabled: {enable_multimodal}")
    print(f"⚙️ Page extraction available: {PAGE_EXTRACTION_AVAILABLE}")

    # Check if we need to regenerate decoded.txt for new source
    source_cache_file = "cache/last_source.txt"
    os.makedirs("cache", exist_ok=True)
    
    regenerate_needed = True
    if os.path.exists(decoded_path) and os.path.exists(source_cache_file):
        try:
            with open(source_cache_file, 'r') as f:
                last_source = f.read().strip()
            if last_source == source_input:
                regenerate_needed = False
                print("♻️ Using existing decoded.txt (same source)")
            else:
                print(f"🔄 Source changed from {last_source} to {source_input} - regenerating...")
        except:
            print("⚠️ Could not read source cache - regenerating...")
    
    if regenerate_needed or not os.path.exists(decoded_path):
        print("🕒 Running full encode-decode pipeline...")

        raw_lines = process_file(source_input, enable_multimodal=False)  # Use text-only for encoding
        text = "\n".join(raw_lines)
        cleaned = clean_input(text)

        expand_dictionary(cleaned)
        img_path = "cache/decode_once.png"
        os.makedirs("cache", exist_ok=True)
        encode_text_to_image(cleaned, img_path, encryption_key)
        decode_image_to_text(img_path, decoded_path, encryption_key)

        # Cache the source file name
        with open(source_cache_file, 'w') as f:
            f.write(source_input)

        print(f"✅ decoded.txt generated from {source_input}")

    # === Chunk and process ==== #
    lines = process_file(decoded_path, enable_multimodal=False)  # Don't re-extract images from decoded.txt
    paragraphs = extract_paragraphs(lines)
    chunks = chunk_paragraphs(paragraphs, max_tokens=450)

    # ===Extract PDF pages as images if it's a PDF === #
    page_images_data = []
    if enable_multimodal and source_input.endswith(".pdf"):
        print("📄 Extracting PDF pages as images...")
        page_images_data = integrate_page_based_extraction(source_input, "pdf_pages")
        
        if page_images_data:
            print(f"🖼️ Processing {len(page_images_data)} page images...")
            for page_info in page_images_data:
                # Add page image to RAG system
                image_data = {
                    "image_id": f"page_{page_info['page_number']}",
                    "source_page": page_info['page_number'],
                    "file_path": page_info['filepath'],
                    "classification": "page_image",
                    "description": f"Page {page_info['page_number']} with visual content: {', '.join(page_info['visual_keywords'])}",
                    "properties": {
                        "visual_keywords": page_info['visual_keywords'],
                        "has_visual_content": page_info['has_visual_content'],
                        "dimensions": page_info['dimensions']
                    },
                    "confidence": 1.0 if page_info['has_visual_content'] else 0.5,
                    "estimated_tokens": page_info['estimated_tokens'],
                    "extracted_from": "page_based_extraction"
                }
                # Store image data for advanced system (no legacy storage)
                print(f"🖼️ Prepared image {image_data['image_id']} for advanced processing")
            print(f"✅ Prepared {len(page_images_data)} page images for knowledge base")
        else:
            print("📷 Page extraction not available - continuing with text-only processing")
    else:
        print("📷 Non-PDF source - text-only processing")

    output_img_dir = "encoded_chunks"
    output_txt_dir = "decoded_chunks"
    os.makedirs(output_img_dir, exist_ok=True)
    os.makedirs(output_txt_dir, exist_ok=True)

    # KEEP: Document type detection (still needed for routing)
    middle_idx = len(chunks) // 2
    middle_chunk_text = "\n".join(chunks[middle_idx])
    doc_type = diagnose_content_type(middle_chunk_text)
    print(f"📋 Detected document type: {doc_type}")

    # Process chunks for verbatim text extraction (no LLM summarization)
    chunk_storage = []  # Store raw chunks for advanced RAG
    for i, chunk in enumerate(chunks):
        chunk_id = f"chunk_{i+1}"
        text = "\n".join(chunk)
        
        # KEEP: Steganographic encoding/decoding (preserves encryption)
        cleaned = clean_input(text)
        expand_dictionary(cleaned)
        img_path = os.path.join(output_img_dir, f"{chunk_id}.png")
        encode_text_to_image(cleaned, img_path, encryption_key)
        decoded_path = os.path.join(output_txt_dir, f"{chunk_id}.txt")
        decode_image_to_text(img_path, decoded_path, encryption_key)
        with open(decoded_path, encoding="utf-8") as f:
            decoded = f.read().strip()
        
        
        
        # KEEP: Create structured chunk data (now using raw text instead of summary)
        chunk_data = {
            "chunk_id": chunk_id,
            "source_type": doc_type,
            "content": decoded,  # Raw text instead of LLM summary
            "original_text_length": len(decoded),
            "chunk_index": i,
            # "key_facts": key_facts,  # COMMENTED OUT: Will be extracted by external API
            "inferred_modality": doc_type,
            "processing_method": "verbatim_extraction"  # Flag for new processing method
        }
        
        # Store raw chunk for advanced RAG processing
        chunk_storage.append(chunk_data)
        
        # Store in memory for legacy compatibility
        memory[chunk_id] = decoded  # Store raw text instead of summary
        
        print(f"✅ Chunk {chunk_id} extracted (verbatim text, no LLM processing)")

    # === NEW: Specialized Model Integration for PDF/TXT === #
    print("\n🎯 Specialized Model Integration for Technical Documents")
    print("=" * 60)
    
    try:
        from integrated_json_rag import IntegratedJSONRAG
        
        # Initialize specialized RAG system with adaptive models
        specialized_rag = IntegratedJSONRAG(
            embedding_model="adaptive",  # Auto-select best model for content
            llm_provider="openai",
            chunk_size=100,  # Smaller since we pre-processed
            max_context_tokens=80000,
            use_gpu=True,
            specialized_models=True  # Enable domain-specific models
        )
        
        print(f"🤖 Initialized specialized embedding system")
        print(f"   📊 Available specialized models: {len(specialized_rag.rag_systems)} domains")
        
        # Convert our chunks to format expected by specialized system
        print(f"🔄 Converting {len(chunk_storage)} chunks for specialized processing...")
        
        # Process with specialized system directly (no JSON file needed)
        print(f"🎯 Processing with specialized embedding models...")
        processing_results = specialized_rag.process_raw_chunks(
            chunk_storage,
            document_type=doc_type
        )
        
        if processing_results['total_chunks'] > 0:
            print(f"✅ Specialized processing complete!")
            print(f"   🧠 Domain detected: {specialized_rag.current_document_domain}")
            print(f"   📊 Chunks processed: {processing_results['total_chunks']}")
            print(f"   🎯 Model used: {specialized_rag.current_document_domain.replace('_', ' ').title()}")
            
            # Store the specialized system for potential queries
            specialized_system = specialized_rag
            
            # Test a sample query to demonstrate the specialized model
            if doc_type in ['medical', 'scientific', 'technical']:
                sample_queries = {
                    'medical': 'What are the key medical findings in this document?',
                    'scientific': 'What are the main scientific concepts or findings?',
                    'technical': 'What are the primary technical specifications?'
                }
                
                test_query = sample_queries.get(doc_type, 'What are the key topics in this document?')
                print(f"\n🔍 Testing specialized model with query: '{test_query}'")
                
                query_results = specialized_rag.integrated_query(
                    test_query,
                    top_k_chunks=3,
                    similarity_threshold=0.2
                )
                
                if query_results['status'] == 'completed':
                    print(f"✅ Query successful using {specialized_rag.current_document_domain} model")
                    print(f"   📊 Found {len(query_results['semantic_search']['results'])} relevant chunks")
                    print(f"   ⏱️ Processing time: {query_results['processing_time_seconds']:.2f}s")
                else:
                    print(f"⚠️ Query test failed: {query_results.get('message', 'Unknown error')}")
        else:
            print("⚠️ No chunks were processed by specialized system")
            specialized_system = None
            
    except ImportError:
        print("⚠️ Specialized model system not available - continuing with standard processing")
        specialized_system = None
    except Exception as e:
        print(f"⚠️ Specialized model processing failed: {e}")
        specialized_system = None

    # === NEW: Advanced RAG System Integration === #
    print("\n🎯 Advanced RAG System Integration")
    print("=" * 50)
    
    try:
        # Initialize advanced RAG system
        advanced_rag = TokenSightAdvancedRAG(enable_external_api=True)
        
        # Use the raw chunks we just processed (no need to re-process)
        print(f"📄 Using {len(chunk_storage)} raw text chunks for advanced processing...")
        
        # Document metadata
        doc_info = {
            "source": source_input,
            "type": doc_type,
            "total_chunks": len(chunk_storage),
            "multimodal_enabled": enable_multimodal,
            "timestamp": "now",
            "processing_method": "verbatim_extraction"
        }
        
        # Process through advanced RAG system using raw chunks
        advanced_rag.process_document_chunks(chunk_storage, doc_info)
        
        print(f"✅ Advanced RAG system initialized with {len(chunk_storage)} raw chunks")
        
        # Test advanced query capabilities (LOCAL ONLY - no external API calls)
        print("\n🧠 Testing Advanced Query Capabilities (Local Only):")
        test_queries = [
            "What are the main safety requirements?",
            "How should electrical installations be protected?", 
            "What are the key technical specifications?",
            "Describe any visual elements or diagrams mentioned"
        ]
        
        for test_query in test_queries:
            print(f"\n🔍 Local Test Query: {test_query}")
            result = advanced_rag.enhanced_query(
                test_query, 
                max_chunks=3,
                enable_external_enhancement=False,  # NO external API during testing
                safety_threshold=0.7
            )
            
            # Display results summary (local only)
            print(f"   📊 Found {len(result['local_results']['results'])} relevant chunks")
            print(f"   🔒 Local processing only (no external API calls)")
            print(f"   🛡️ Safety status: {result.get('safety_status', 'unknown')}")
            
            if result.get('audit_results'):
                audit = result['audit_results']
                print(f"   📋 Audit passed: {'✅' if audit.get('audit_passed') else '❌'}")
                if audit.get('safety_audit'):
                    risk_level = audit['safety_audit'].get('risk_level', 'unknown')
                    print(f"   ⚠️ Risk level: {risk_level}")
        
        # Generate audit report
        advanced_rag.save_audit_report("tokensight_audit_report.json")
        print(f"\n📊 Comprehensive audit report saved")
        
    except Exception as e:
        print(f"⚠️ Advanced RAG system error: {e}")
        traceback.print_exc()
        print("   Falling back to legacy processing...")
    # === Interactive User-Driven Analysis ===
    print("\n💬 Starting Interactive Analysis Engine")
    print("=" * 50)
    print("🔔 NOTE: External API calls will ONLY be made when you explicitly request them!")
    print("Enter your request (e.g., 'Summarize the document', 'What are the safety requirements?'), or type 'exit' to quit.")

    while True:
        try:
            user_query = input("\nYour request: ")
            if user_query.lower() in ['exit', 'quit']:
                print("✅ Exiting interactive session.")
                break

            # 1. Check for active task FIRST - this creates a "task lock"
            # Clean up any malformed tasks first
            session_manager.lattice.cleanup_malformed_tasks()
            
            active_task = session_manager.lattice.get_active_task()
            
            # DEBUG: Show task status
            all_tasks = session_manager.lattice.get_nodes("task")
            if all_tasks:
                print(f"🔍 DEBUG: Found {len(all_tasks)} total tasks in lattice")
                for i, task in enumerate(all_tasks):
                    status = task.get("status", "unknown")
                    title = task.get("task_title", task.get("query", "Unknown"))[:50]
                    has_plan = "task_plan" in task and len(task.get("task_plan", [])) > 0
                    completed_count = len(task.get("completed_steps", []))
                    print(f"   Task {i+1}: {title}... (status: {status}, has_plan: {has_plan}, completed: {completed_count})")
            
            if active_task:
                print(f"🔒 ACTIVE TASK FOUND: {active_task.get('task_title', 'Untitled')[:50]}...")
            else:
                print(f"🔓 NO ACTIVE TASK FOUND")
            
            if active_task:
                # TASK LOCK: When a task is active, ALL input is treated as task-related
                task_progress = session_manager.lattice.get_task_progress(active_task)
                print(f"� Task Lock Active: {task_progress['completed_steps']}/{task_progress['total_steps']} steps completed")
                
                # Force intent to be "task" - bypass all other intent diagnosis
                intent = "task"
                action = "step_input"
                
                # Only check for explicit continuation keywords
                continue_keywords = ["continue", "next", "proceed", "go ahead", "keep going", "yes", "ok", "okay"]
                if user_query.lower().strip() in continue_keywords:
                    action = "continue"
                    print(f"   - Forced Intent: {intent} (continuation)")
                else:
                    print(f"   - Forced Intent: {intent} (user providing step input)")
                    
            else:
                # No active task, do normal intent detection
                print("🧠 Diagnosing user intent...")
                intent_info = diagnose_user_intent(user_query)
                intent = intent_info.get("intent", "query")
                action = intent_info.get("action", "query")
                
                # Handle nested intent/action structures
                if isinstance(intent, dict):
                    intent = intent.get("type", intent.get("intent", "query"))
                if isinstance(action, dict):
                    action = action.get("type", action.get("action", "query"))
                
                print(f"   - Intent: {intent}, Action: {action}")


            # 2. Add this turn to the cognitive lattice (audit log style)
            if intent == "task" and action == "step_input" and active_task:
                # For step input, we DON'T pre-add to lattice here
                # The task handler will create the updated node with API results
                pass
            else:
                # Add new event for new plan, chat, or query
                lattice_event = {
                    "type": intent,
                    "query": user_query,
                    "action": action,
                    "timestamp": datetime.now().isoformat(),
                    "status": "pending"
                }
                session_manager.lattice.add_event(lattice_event)


            # === Intent-based Routing === #
            if intent in ["chat", "simple", "conversation"]:
                # Simple chat intent: respond conversationally
                print(f"💬 [Simple Chat]: Routing to external API for conversational response...")
                if 'advanced_rag' in locals() and advanced_rag and hasattr(advanced_rag, 'external_client'):
                    try:
                        # Direct API call for simple chat - no chunking, no RAG
                        chat_response = advanced_rag.external_client.query_external_api(user_query)
                        print(f"✅ Chat response received")
                        print(f"\n💬 Response: {chat_response}")
                        
                        # Log the chat response as an event
                        session_manager.lattice.add_event({
                            "type": "chat_response",
                            "timestamp": datetime.now().isoformat(),
                            "query": user_query,
                            "response": chat_response,
                            "status": "completed"
                        })
                        
                    except Exception as e:
                        print(f"❌ Chat API call failed: {e}")
                        fallback_response = "I'm here to chat, but I'm having trouble connecting to my chat system right now."
                        print(f"💬 Fallback: {fallback_response}")
                        session_manager.lattice.add_event({
                            "type": "chat_response",
                            "timestamp": datetime.now().isoformat(),
                            "query": user_query,
                            "response": fallback_response,
                            "status": "error",
                            "error": str(e)
                        })
                else:
                    fallback_response = "I'm here to chat! (External API not available)"
                    print(f"💬 [Chatbot]: {fallback_response}")
                    session_manager.lattice.add_event({
                        "type": "chat_response",
                        "timestamp": datetime.now().isoformat(),
                        "query": user_query,
                        "response": fallback_response,
                        "status": "completed"
                    })

            elif intent == "query" and action in ["query", "question", "ask", "simple_question_answering"]:
                # Simple specific query - direct API call, no document analysis
                print(f"❓ [Simple Query]: Routing directly to external API...")
                if 'advanced_rag' in locals() and advanced_rag and hasattr(advanced_rag, 'external_client'):
                    try:
                        # Direct API call for simple questions - no chunking, no RAG
                        query_response = advanced_rag.external_client.query_external_api(user_query)
                        print(f"✅ Query response received")
                        print(f"\n💡 Response: {query_response}")
                        
                        # Log the query response as an event
                        session_manager.lattice.add_event({
                            "type": "query_response",
                            "timestamp": datetime.now().isoformat(),
                            "query": user_query,
                            "response": query_response,
                            "status": "completed"
                        })
                        
                    except Exception as e:
                        print(f"❌ Query API call failed: {e}")
                        fallback_response = "I'd be happy to help answer that, but I'm having trouble connecting right now."
                        print(f"💡 Fallback: {fallback_response}")
                        session_manager.lattice.add_event({
                            "type": "query_response",
                            "timestamp": datetime.now().isoformat(),
                            "query": user_query,
                            "response": fallback_response,
                            "status": "error",
                            "error": str(e)
                        })
                else:
                    fallback_response = "I'd be happy to help answer that! (External API not available)"
                    print(f"💡 [Query]: {fallback_response}")
                    session_manager.lattice.add_event({
                        "type": "query_response",
                        "timestamp": datetime.now().isoformat(),
                        "query": user_query,
                        "response": fallback_response,
                        "status": "completed"
                    })

            elif intent in ["analysis", "summarize", "broad"] or (intent == "specific" and action in ["analyze", "summarize", "extract", "review"]) or (intent == "query" and action in ["extract", "analyze", "review"]):
                # Document analysis or RAG-based query - use the full pipeline
                print(f"📊 [Document Analysis]: Using advanced RAG system...")
                # This is the previous 'broad' and 'specific' logic, now unified for all analysis intents
                # --- Begin migrated analysis logic ---
                saved_analysis = None
                analysis_files = [f for f in os.listdir('.') if f.startswith('external_analysis_') and f.endswith('.json')]

                # Also check current interactive session for previous analyses
                if 'session_results_file' in locals() and os.path.exists(session_results_file):
                    try:
                        if os.path.getsize(session_results_file) > 0:
                            with open(session_results_file, 'r', encoding='utf-8') as f:
                                session_data = json.load(f)
                            if session_data.get('queries'):
                                print(f"📁 Found current session with {len(session_data['queries'])} previous queries")
                                # Extract external analysis from previous queries in this session
                                session_analyses = []
                                for query_data in session_data['queries']:
                                    if query_data.get('external_analysis', {}).get('raw_results'):
                                        session_analyses.extend(query_data['external_analysis']['raw_results'])
                                if session_analyses:
                                    saved_analysis = {'results': session_analyses}
                                    print(f"   ✅ Loaded {len(session_analyses)} previously analyzed chunks from current session")
                    except Exception as e:
                        print(f"   ⚠️ Could not load current session data: {e}")

                # Fall back to external analysis files if no session data and it's not the first query
                if not saved_analysis and analysis_files and 'session_results_file' in locals():
                    # Use the most recent analysis file
                    latest_file = max(analysis_files, key=os.path.getmtime)
                    try:
                        # Check if file is not empty before trying to load
                        if os.path.getsize(latest_file) > 0:
                            print(f"📁 Found existing analysis: {latest_file}")
                            with open(latest_file, 'r', encoding='utf-8') as f:
                                saved_analysis = json.load(f)
                            print(f"   ✅ Loaded {len(saved_analysis.get('results', []))} previously analyzed chunks from external file")
                    except (json.JSONDecodeError, KeyError) as e:
                        print(f"   ⚠️ Could not parse saved analysis: {e}")
                    except Exception as e:
                        print(f"   ⚠️ Could not load saved analysis: {e}")

                if 'advanced_rag' in locals() and advanced_rag:
                    try:
                        # Check if we can reuse a previous analysis for this exact query
                        reused_previous_analysis = False
                        saved_analysis_result = None

                        # Determine current session file path
                        session_file_path = None
                        if 'session_results_file' in locals() and os.path.exists(session_results_file):
                            session_file_path = session_results_file
                        else:
                            # Find most recent session file if one isn't active
                            session_files = sorted([f for f in os.listdir('.') if f.startswith('interactive_session_') and f.endswith('.json')], key=os.path.getmtime, reverse=True)
                            if session_files:
                                session_file_path = session_files[0]

                        if session_file_path and os.path.exists(session_file_path):
                            try:
                                with open(session_file_path, 'r', encoding='utf-8') as f:
                                    # Check for empty file
                                    if os.path.getsize(session_file_path) > 0:
                                        session_data = json.load(f)
                                        # Look for this exact query in previous analyses
                                        for query_entry in session_data.get('queries', []):
                                            if query_entry.get('query', '').lower().strip() == user_query.lower().strip():
                                                saved_analysis_result = query_entry
                                                reused_previous_analysis = True
                                                break
                            except (json.JSONDecodeError, KeyError) as e:
                                print(f"   ⚠️ Could not parse session file {session_file_path}: {e}")
                            except Exception as e:
                                print(f"   ⚠️ Could not load session file {session_file_path}: {e}")

                        if reused_previous_analysis and saved_analysis_result:
                            print(f"♻️ Found exact match for '{user_query}' - reusing previous analysis (saving ~6000 tokens)")
                            # Use the entire saved result
                            result = saved_analysis_result
                            result['reused_analysis'] = True
                        else:
                            # Use the enhanced query method with fresh API call
                            print(f"🌐 Making fresh API call for new analysis...")
                            result = advanced_rag.enhanced_query(
                                user_query,
                                max_chunks=5, # More chunks for better context
                                enable_external_enhancement=True,
                                safety_threshold=0.7
                            )

                        # Save the interactive query results (reuse session file if exists)
                        if 'session_results_file' not in locals():
                            query_timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            session_results_file = f"interactive_session_{query_timestamp}.json"
                        query_results_file = session_results_file

                        # Clean the results for JSON serialization (remove embeddings and other non-serializable data)
                        def clean_for_json(obj):
                            """Recursively clean objects for JSON serialization"""
                            if isinstance(obj, dict):
                                cleaned = {}
                                for key, value in obj.items():
                                    if key in ['embedding', 'embeddings']:
                                        cleaned[key] = f"<embedding_array_length_{len(value) if hasattr(value, '__len__') else 'unknown'}>"
                                    else:
                                        cleaned[key] = clean_for_json(value)
                                return cleaned
                            elif isinstance(obj, list):
                                return [clean_for_json(item) for item in obj]
                            elif hasattr(obj, 'tolist'):
                                return f"<numpy_array_shape_{obj.shape}>"
                            elif hasattr(obj, '__dict__'):
                                return str(obj)
                            else:
                                return obj

                        # Load existing session data if file exists
                        session_data = {"queries": []}
                        if os.path.exists(query_results_file):
                            try:
                                with open(query_results_file, 'r', encoding='utf-8') as f:
                                    session_data = json.load(f)
                                if "queries" not in session_data:
                                    session_data["queries"] = []
                            except Exception as load_err:
                                print(f"⚠️ Could not load existing session file: {load_err}")
                                session_data = {"queries": []}

                        # Format the current query result
                        query_result = {
                            "query": user_query,
                            "timestamp": datetime.now().isoformat(),
                            "query_type": "interactive_specific",
                            "chunks_found": len(result['local_results']['results']),
                            "local_results": result['local_results'],
                            "external_analysis": result.get('external_analysis'),
                            "audit_results": result.get('audit_results'),
                            "safety_status": result.get('safety_status', 'unknown')
                        }

                        # Clean the result for JSON serialization
                        cleaned_query_result = clean_for_json(query_result)

                        # Add to session data only if it's a new analysis
                        if not result.get('reused_analysis'):
                            session_data["queries"].append(cleaned_query_result)
                            session_data["session_start"] = session_data.get("session_start", datetime.now().isoformat())
                            session_data["last_updated"] = datetime.now().isoformat()
                            session_data["total_queries"] = len(session_data["queries"])

                            try:
                                with open(query_results_file, 'w', encoding='utf-8') as f:
                                    json.dump(session_data, f, indent=2, ensure_ascii=False)
                                print(f"💾 Query results saved to session: {query_results_file} ({session_data['total_queries']} queries)")
                            except Exception as save_error:
                                print(f"⚠️ Could not save query results: {save_error}")

                        # Display results summary
                        print(f"\n✅ Advanced Query Complete:")
                        print(f"   📊 Found {len(result['local_results']['results'])} relevant chunks")
                        print(f"   🌐 External analysis: {'✅' if result.get('external_analysis') else '❌'}")

                        # If we have saved analysis, supplement the answer
                        if saved_analysis and result.get('local_results', {}).get('results'):
                            print(f"\n🔍 Supplementing with Previous Analysis:")
                            relevant_chunk_ids = [chunk.get('chunk_id', f"chunk_{i+1}") for i, chunk in enumerate(result['local_results']['results'])]

                            for chunk_id in relevant_chunk_ids:
                                # Find matching analysis from saved data
                                matching_analysis = None
                                for saved_chunk in saved_analysis.get('results', []):
                                    if saved_chunk.get('chunk_id') == chunk_id:
                                        matching_analysis = saved_chunk.get('external_analysis', {})
                                        break

                                if matching_analysis:
                                    print(f"\n   📄 {chunk_id} insights:")
                                    # Extract key themes and facts
                                    key_insights = matching_analysis.get('Key Insights', {}) or matching_analysis.get('KeyInsights', {})
                                    if key_insights:
                                        themes = key_insights.get('Themes', key_insights.get('MainTopics', []))
                                        if themes:
                                            print(f"      🎯 Themes: {', '.join(themes[:3])}")

                                    # Extract factual information
                                    factual = matching_analysis.get('Factual Extraction', {}) or matching_analysis.get('FactualExtraction', {})
                                    if factual:
                                        names = factual.get('Names', [])
                                        locations = factual.get('Locations', [])
                                        if names:
                                            print(f"      👤 Characters: {', '.join(names[:3])}")
                                        if locations:
                                            print(f"      📍 Locations: {', '.join(locations[:3])}")

                        # Display results in user-friendly format instead of raw JSON
                        print(f"\n" + "="*60)
                        print(f"📝 ANALYSIS RESULTS FOR: '{user_query}'")
                        print(f"="*60)

                        local_results = result.get('local_results', {})
                        if local_results and local_results.get('results'):
                            print(f"📊 Found {len(local_results['results'])} relevant chunks")

                        if result.get('reused_analysis'):
                            print(f"♻️ Used previous analysis (saved ~6000 tokens)")

                        # Extract and format the analysis from external_analysis
                        if result.get('external_analysis'):

                            print(f"\n🔍 DETAILED ANALYSIS:")
                            enhanced_answer = result['external_analysis'].get('enhanced_answer', '')
                            # If the enhanced_answer is a unified summary (from the new summarization step), print it directly
                            if enhanced_answer and isinstance(enhanced_answer, str) and len(enhanced_answer) > 0:
                                print(f"\n{enhanced_answer.strip()}\n")
                            else:
                                # Fallback: show per-chunk analysis as before
                                try:
                                    parsed_analyses = []
                                    json_parts = enhanced_answer.strip().split('\n\n')
                                    for part in json_parts:
                                        if part.strip().startswith('{'):
                                            try:
                                                parsed_analyses.append(json.loads(part.strip()))
                                            except json.JSONDecodeError:
                                                continue
                                    if parsed_analyses:
                                        for i, analysis in enumerate(parsed_analyses, 1):
                                            print(f"\n📄 CHUNK {i} ANALYSIS:")
                                            key_insights = analysis.get('Key Insights', analysis.get('KeyInsights', {}))
                                            if isinstance(key_insights, dict):
                                                themes = key_insights.get('Themes', [])
                                                topics = key_insights.get('Main Topics', key_insights.get('MainTopics', []))
                                                if themes:
                                                    print(f"   🎭 THEMES: {', '.join(themes[:3])}")
                                                if topics:
                                                    print(f"   🎯 TOPICS: {', '.join(topics[:3])}")
                                            factual = analysis.get('Factual Extraction', analysis.get('FactualExtraction', {}))
                                            if isinstance(factual, dict):
                                                names = factual.get('Names', factual.get('CharacterNames', []))
                                                if isinstance(factual.get('Facts'), dict):
                                                    names.extend(factual['Facts'].get('Names', []))
                                                locations = factual.get('Locations', [])
                                                if names:
                                                    unique_names = sorted(list(set(names)))
                                                    print(f"   👤 CHARACTERS: {', '.join(unique_names[:4])}")
                                                if locations:
                                                    print(f"   📍 LOCATIONS: {', '.join(locations[:3])}")
                                    else:
                                        print(f"\n💡 ANALYSIS SUMMARY:")
                                        print(f"   {enhanced_answer[:500].strip()}...")
                                except Exception as e:
                                    print(f"\n💡 Could not fully parse analysis, showing summary: {e}")
                                    print(f"   {enhanced_answer[:500].strip()}...")

                        # Show source chunk previews
                        if local_results and local_results.get('results'):
                            print(f"\n📚 SOURCE CHUNKS ANALYZED:")
                            for i, chunk in enumerate(local_results['results'][:3], 1):
                                chunk_preview = chunk.get('content', '')[:100].replace('\n', ' ')
                                print(f"   {i}. {chunk_preview}...")

                        # Show audit results
                        if result.get('audit_results'):
                            audit = result['audit_results']
                            print(f"\n🛡️ SAFETY: {'✅ PASSED' if audit.get('audit_passed') else '❌ FAILED'}")
                            if audit.get('safety_audit'):
                                risk_level = audit['safety_audit'].get('risk_level', 'unknown')
                                print(f"   Risk Level: {risk_level.upper()}")

                        print(f"\n" + "="*60)
                    except Exception as query_error:
                        print(f"   ❌ Query failed: {query_error}")
                        traceback.print_exc()
                else:
                    print("   ⚠️ Advanced RAG system not available for analysis queries.")
                # --- End migrated analysis logic ---

            elif intent in ["task", "structured_task", "plan", "planner"] or (intent == "query" and action in ["plan", "planning", "step_by_step", "itinerary"]):
                # This is the master logic for handling all structured tasks.
                print(f"🧩 [Task Planner]: Routing to structured task handler.")
                
                current_task = session_manager.lattice.get_active_task()
                
                # SCENARIO 1: A task is already active. The user is providing input for the current step.
                if current_task:
                    print(f"📋 Continuing existing task: {current_task.get('task_title', 'Untitled Task')}")
                    print(f"🔍 Task details: query='{current_task.get('query', 'N/A')[:30]}...', status='{current_task.get('status', 'N/A')}'")
                    task_plan = current_task.get("task_plan", [])
                    completed_steps = current_task.get("completed_steps", [])
                    print(f"🔍 Task has {len(task_plan)} planned steps and {len(completed_steps)} completed steps")
                    
                    # Handle "continue/next" action - advance to next step
                    if action == "continue":
                        # Mark current step as completed and move to next
                        completed_steps = current_task.get("completed_steps", [])
                        current_step_index = len(completed_steps)
                        
                        # Mark the current in-progress step as fully completed (if it exists)
                        if completed_steps and completed_steps[-1].get("status") == "in_progress":
                            step_number = completed_steps[-1].get("step_number", len(completed_steps))
                            session_manager.lattice.mark_step_completed(step_number)
                            print(f"✅ Step {step_number} marked as completed")
                        
                        # Check if there are more steps
                        task_plan = current_task.get("task_plan", [])
                        if current_step_index < len(task_plan):
                            next_step_description = task_plan[current_step_index]
                            print(f"\n⏭️ Moving to step {current_step_index + 1}/{len(task_plan)}: {next_step_description}")
                            print(f"💡 Provide the information for this step or type 'continue' if no input is needed.")
                            session_manager.lattice.save()
                            continue  # Skip the rest of the task logic, wait for user input on new step
                        else:
                            session_manager.lattice.complete_current_task()
                            print(f"🎉 Task completed! All {len(task_plan)} steps executed.")
                            continue
                    
                    # Normal step processing - find current active step (first incomplete step)
                    current_step_index = 0
                    
                    # Find the first step that hasn't been completed yet
                    for i, step_data in enumerate(completed_steps):
                        if step_data.get("status") == "completed":
                            current_step_index = i + 1
                        else:
                            # Found an in-progress or incomplete step, this is our current step
                            current_step_index = i
                            break
                    
                    # If all existing steps are completed, we're on the next new step
                    if current_step_index >= len(completed_steps):
                        current_step_index = len(completed_steps)
                    
                    # Validate that the task has a proper task plan
                    if not task_plan:
                        print("⚠️ Found task without a valid plan. Marking as completed and starting fresh.")
                        current_task["status"] = "completed"
                        session_manager.lattice.save()
                        # Set current_task to None so we create a new task
                        current_task = None
                    elif current_step_index < len(task_plan):
                        # Process the current step (existing logic continues here...)
                        current_step_description = task_plan[current_step_index]
                        print(f"🎯 Executing step {current_step_index + 1}/{len(task_plan)}: {current_step_description}")
                        
                        # Create a comprehensive context-aware prompt for the LLM
                        # Build context from completed steps
                        completed_steps_context = ""
                        if completed_steps:
                            completed_steps_context = "\n\nPREVIOUSLY COMPLETED STEPS:\n"
                            for i, step_data in enumerate(completed_steps, 1):
                                completed_steps_context += f"Step {i}: {step_data.get('description', 'N/A')}\n"
                                completed_steps_context += f"  User Input: {step_data.get('user_input', 'N/A')}\n"
                                completed_steps_context += f"  Result: {step_data.get('result', 'N/A')[:150]}...\n\n"
                        
                        # Build full task plan context
                        task_plan_context = "\n\nFULL TASK PLAN (ITINERARY):\n"
                        for i, step_desc in enumerate(task_plan, 1):
                            status_marker = "✅" if i <= len(completed_steps) else ("🎯" if i == current_step_index + 1 else "⏳")
                            task_plan_context += f"{status_marker} Step {i}: {step_desc}\n"
                        
                        # Build recent tool results context for external API
                        tool_context = ""
                        if hasattr(tool_manager, 'recent_tool_results') and tool_manager.recent_tool_results:
                            tool_context = "\n\nRECENT TOOL RESULTS AVAILABLE:\n"
                            for tool_name, tool_result in tool_manager.recent_tool_results.items():
                                tool_context += f"\n{tool_name.upper()} RESULTS:\n"
                                if tool_name == 'flight_planner' and 'flight_options' in tool_result:
                                    tool_context += f"Route: {tool_result.get('route', 'N/A')}\n"
                                    tool_context += f"Available Options:\n"
                                    for i, flight in enumerate(tool_result['flight_options'], 1):
                                        tool_context += f"  Option {i}: {flight['airline']} - ${flight['price']:.2f} - {flight['stops']} stops - {flight['departure_time']}\n"
                                elif tool_name == 'hotel_planner' and 'hotel_options' in tool_result:
                                    tool_context += f"Location: {tool_result.get('search_parameters', {}).get('location', 'N/A').title()}\n"
                                    tool_context += f"Available Options:\n"
                                    for i, hotel in enumerate(tool_result['hotel_options'], 1):
                                        tool_context += f"  Option {i}: {hotel['name']} - ${hotel['price']:.2f}/night - {hotel['rating']}/5 stars - {hotel['room_type']}\n"
                                elif tool_name == 'restaurant_planner' and 'restaurant_options' in tool_result:
                                    tool_context += f"Location: {tool_result.get('search_parameters', {}).get('location', 'N/A').title()}\n"
                                    tool_context += f"Available Options:\n"
                                    for i, restaurant in enumerate(tool_result['restaurant_options'], 1):
                                        tool_context += f"  Option {i}: {restaurant['name']} - {restaurant['cuisine']} - {restaurant['price_range']} - {restaurant['available_time']}\n"
                                else:
                                    # Generic tool result formatting
                                    tool_context += f"{str(tool_result)[:200]}...\n"
                            tool_context += "\nNOTE: User may refer to these results by option number (e.g., 'option 2' means the second option above).\n"
                        
                        # Check if this current step has received previous user inputs
                        current_step_inputs = ""
                        # Look for any incomplete/partial work on this step in the lattice
                        recent_task_nodes = [node for node in session_manager.lattice.nodes[-10:] if node.get('type') == 'task']
                        for node in recent_task_nodes:
                            if node.get('current_step_index') == current_step_index and node.get('partial_inputs'):
                                current_step_inputs = f"\n\nPREVIOUS INPUTS FOR THIS STEP:\n{node.get('partial_inputs')}\n"
                                break
                        
                        step_execution_prompt = f"""You are helping a user with a step-by-step task plan. Here is the complete context:

ORIGINAL TASK PLAN YOU CREATED:
{chr(10).join([f"{i+1}. {step}" for i, step in enumerate(current_task.get('task_plan', []))])}

CURRENT STEP: You are currently working on Step {current_step_index + 1} of this task plan.
CURRENT STEP DESCRIPTION: "{current_step_description}"

USER INPUT FOR THIS STEP: "{user_query}"

{tool_context}

INSTRUCTIONS: 
- The user has provided input specifically for Step {current_step_index + 1}: "{current_step_description}"
- Factor in the user's new input and provide a response that addresses this specific step
- If user refers to options by number (e.g., "option 2"), use the tool results context above
- Do NOT advance to other steps - focus only on completing or updating Step {current_step_index + 1}
- Provide a helpful, actionable response for this current step based on the user's input

COMPLETED STEPS SO FAR:
{chr(10).join([f"Step {step.get('step_number', i+1)}: {step.get('description', 'No description')} - COMPLETED" for i, step in enumerate(completed_steps)]) if completed_steps else "None completed yet"}

Please respond with information relevant to Step {current_step_index + 1} only."""
                        
                        if 'advanced_rag' in locals() and advanced_rag and hasattr(advanced_rag, 'external_client'):
                            try:
                                # 🔧 TOOL-FIRST APPROACH: Check for tools before making external API call
                                tool_enhancement = tool_manager.enhance_llm_response(
                                    user_query,  # Check user input directly for tool needs
                                    context={
                                        'step_number': current_step_index + 1,
                                        'step_description': current_step_description,
                                        'user_input': user_query,
                                        'task_context': current_task,
                                        'external_client': advanced_rag.external_client  # Pass LLM for tool selection
                                    }
                                )
                                
                                # If tools were used, skip external API call and use tool results directly
                                if tool_enhancement['tools_used']:
                                    print(f"🔧 Tools detected - using tool results directly (skipping external API)")
                                    final_step_result = tool_enhancement['enhanced_response']
                                else:
                                    # No tools needed, proceed with normal external API call
                                    step_result = advanced_rag.external_client.query_external_api(step_execution_prompt)
                                    final_step_result = step_result
                                
                                # Log tool usage if any tools were used
                                if tool_enhancement['tools_used']:
                                    print(f"🔧 Tools used: {', '.join(tool_enhancement['tools_used'])}")
                                    session_manager.lattice.add_event({
                                        "type": "tools_executed",
                                        "timestamp": datetime.now().isoformat(),
                                        "step_number": current_step_index + 1,
                                        "tools_used": tool_enhancement['tools_used'],
                                        "tool_results": tool_enhancement['tool_results']
                                    })
                                
                                # Update the active task state using the new hybrid approach
                                session_manager.lattice.execute_step(
                                    step_number=current_step_index + 1,
                                    user_input=user_query,
                                    result=final_step_result
                                )
                                
                                print(f"🔄 Step {current_step_index + 1} updated:")
                                
                                # Display the result with better formatting and no truncation for flight results
                                if "FLIGHT SEARCH RESULTS FOUND" in final_step_result or "FLIGHT SELECTION CONFIRMED" in final_step_result:
                                    # Show full flight results without truncation
                                    print(f"   📄 Result: {final_step_result}")
                                else:
                                    # For other results, show more characters but still truncate if very long
                                    if len(final_step_result) > 500:
                                        print(f"   📄 Result: {final_step_result[:500]}...")
                                    else:
                                        print(f"   📄 Result: {final_step_result}")
                                
                                print(f"\n💡 This step is ready. You can:")
                                print(f"   - Type 'next' or 'continue' to move to the next step")
                                print(f"   - Provide more information to refine this step further")
                                print(f"   - Ask questions about this step")

                                session_manager.lattice.save()

                            except Exception as e:
                                print(f"❌ Step execution failed: {e}")
                                # Log the error event
                                session_manager.lattice.add_event({
                                    "type": "step_error",
                                    "timestamp": datetime.now().isoformat(),
                                    "step_number": current_step_index + 1,
                                    "error": str(e),
                                    "user_input": user_query
                                })
                                session_manager.lattice.save()
                        else:
                            print("⚠️ External API not available for step execution.")
                    else:
                        print("✅ Task is already complete.")
                        current_task["status"] = "completed"
                        session_manager.lattice.save()
                        # Set current_task to None so we create a new task
                        current_task = None

                # SCENARIO 2: No active task. The user is starting a new one.
                if not current_task:
                    # Double-check: make sure there really isn't an active task before creating a new one
                    double_check_active = session_manager.lattice.get_active_task()
                    if double_check_active:
                        print(f"⚠️ Found active task during double-check: {double_check_active.get('task_title', 'Untitled')}")
                        print(f"   This should not happen! There may be a bug in task detection.")
                        print(f"   Treating user input as step input for existing task instead.")
                        # Redirect to existing task logic
                        current_task = double_check_active
                        # Process as step input
                        intent = "task"
                        action = "step_input"
                        # Re-run the task processing logic here...
                        # For now, just inform the user
                        print(f"   Please try your input again - it should work correctly now.")
                        continue
                    
                    print("🚀 Initiating new structured task planning...")
                    if 'advanced_rag' in locals() and advanced_rag and hasattr(advanced_rag, 'external_client'):
                        try:
                            plan_response = advanced_rag.external_client.create_task_plan(user_query)
                            
                            if plan_response.get("success"):
                                plan_text = plan_response.get("plan_text", "")
                                task_steps = [step.strip() for step in plan_text.split('\n') if step.strip() and step.strip()[0].isdigit()]
                                task_steps = [re.sub(r'^\d+\.\s*', '', step) for step in task_steps]

                                if task_steps:
                                    # Create the new task using the hybrid approach
                                    new_task = session_manager.lattice.create_new_task(user_query, task_steps)
                                    
                                    print(f"📋 Task plan created with {len(task_steps)} steps:")
                                    for i, step in enumerate(task_steps, 1):
                                        print(f"   {i}. {step}")
                                    
                                    print(f"\n🎯 Ready to execute step 1: {task_steps[0]}")
                                    print(f"💡 Provide the information for this step or type 'continue' if no input is needed.")
                                else:
                                    print("⚠️ Could not parse a valid plan from the external response.")
                                    session_manager.lattice.add_event({
                                        "type": "task_creation_failed",
                                        "timestamp": datetime.now().isoformat(),
                                        "query": user_query,
                                        "error": "Could not parse plan"
                                    })
                                    session_manager.lattice.nodes[-1]["error"] = "Could not parse plan"
                                    session_manager.lattice.save()
                            else:
                                print(f"⚠️ API call for planning failed: {plan_response.get('error')}")
                                session_manager.lattice.nodes[-1]["error"] = plan_response.get('error')
                                session_manager.lattice.save()
                        except Exception as e:
                            print(f"❌ Task planning failed: {e}")
                            session_manager.lattice.nodes[-1]["status"] = "error"
                            session_manager.lattice.nodes[-1]["error"] = str(e)
                            session_manager.lattice.save()
                    else:
                        print("⚠️ External API not available for task planning.")
                        session_manager.lattice.nodes[-1]["response"] = "External API required for structured tasks"
                        session_manager.lattice.save()

            else:
                print(f"❓ [System]: Unrecognized intent '{intent}'. Please try rephrasing your request.")
                session_manager.lattice.nodes[-1]["response"] = f"Unrecognized intent '{intent}'."
                session_manager.lattice.save()

        except KeyboardInterrupt:
            print("\n⚠️ Process interrupted by user. Exiting.")
            break
        except Exception as e:
            print(f"\n❌ An error occurred during interactive analysis: {e}")
            traceback.print_exc()

# Only run if this file is executed directly
if __name__ == "__main__":
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error in main execution: {e}")
        traceback.print_exc()