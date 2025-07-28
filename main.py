# Standard library
import os
import json
from datetime import datetime

# Local modules
from utils.dictionary_manager import expand_dictionary, clean_input
from encoder.text_to_image import encode_text_to_image
from decoder.image_to_text import decode_image_to_text
from text_processor import extract_paragraphs, chunk_paragraphs
from file_handler import process_file
from llama_client import run_llama_inference_with_context, diagnose_content_type, extract_key_facts, SUMMARY_TEMPLATES, diagnose_user_intent
from page_extractor import integrate_page_based_extraction, PAGE_EXTRACTION_AVAILABLE
from memory_manager import search_memory, initialize_memory
from external_api_client import ExternalAPIClient, identify_relevant_chunks_for_external_analysis, save_external_analysis_results

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
                print("� Using existing decoded.txt (same source)")
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
        
        # === DEPRECATED: Local LLM Summarization Layer === #
        # This section has been replaced by the Advanced RAG System
        # Raw chunks are now sent directly to external APIs for processing
        
        # # COMMENTED OUT: Get context from previous chunks
        # context = get_previous_chunks_context(i, lookback=3)
        # 
        # # COMMENTED OUT: Use the template for summarization with context
        # template_raw = SUMMARY_TEMPLATES[doc_type]
        # summary_prompt = template_raw.format(text=decoded)
        # 
        # # COMMENTED OUT: Run inference with context awareness
        # summary = run_llama_inference_with_context(summary_prompt, context)
        # 
        # # COMMENTED OUT: Extract key facts using local LLM
        # key_facts = extract_key_facts(summary, doc_type)
        
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
            print(f"   � Local processing only (no external API calls)")
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
        import traceback
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

            # 1. Diagnose user intent using local LLM
            print("🧠 Diagnosing user intent...")
            intent_info = diagnose_user_intent(user_query)
            intent = intent_info.get("intent", "specific")
            action = intent_info.get("action", "query")
            print(f"   - Intent: {intent}, Action: {action}")

            if intent == 'broad':
                # 2a. Broad Intent: Use all chunks for analysis
                print(f"🎯 Broad request detected. Sending all {len(chunk_storage)} chunks to external API for '{action}'.")

                # Use the advanced RAG system's external client for consistency
                if 'advanced_rag' in locals() and advanced_rag and hasattr(advanced_rag, 'external_api_client') and advanced_rag.external_api_client:
                    print(f"🌐 Using external API client for {action} analysis...")
                    # The 'action' can be passed as the analysis_type
                    external_results = advanced_rag.external_api_client.analyze_multiple_chunks(
                        chunk_storage,
                        analysis_type=action # e.g., 'summarize', 'analyze'
                    )
                    save_external_analysis_results(external_results, f"external_analysis_{action}.json")
                    
                    # Display a summary of the results
                    if external_results:
                        print("\n✅ External API Analysis Complete:")
                        # Display the summary from the first result
                        first_result = external_results[0].get("external_analysis", {})
                        summary = first_result.get("summary", "No summary available.")
                        print(f"   📄 Summary: {summary[:1000]}...")
                        
                        # If multiple results, show count
                        if len(external_results) > 1:
                            print(f"   📊 Total results: {len(external_results)} chunk analyses")
                    else:
                        print("   ⚠️ No results returned from external analysis.")

                else:
                    print("   ⚠️ Advanced RAG system with external API not available for broad analysis.")
                    # Fallback to legacy external API client
                    try:
                        api_client = ExternalAPIClient(api_provider="openai")
                        external_results = api_client.analyze_multiple_chunks(
                            chunk_storage,
                            analysis_type=action
                        )
                        save_external_analysis_results(external_results, f"external_analysis_{action}.json")
                        
                        if external_results:
                            print("\n✅ Legacy External API Analysis Complete:")
                            first_result = external_results[0].get("external_analysis", {})
                            summary = first_result.get("summary", "No summary available.")
                            print(f"   📄 Summary: {summary[:1000]}...")
                        else:
                            print("   ⚠️ No results returned from legacy external analysis.")
                    except Exception as fallback_error:
                        print(f"   ❌ Fallback external API also failed: {fallback_error}")

            elif intent == 'specific':
                # 2b. Specific Intent: Use Advanced RAG for a targeted query
                print(f"🎯 Specific request detected. Using Advanced RAG to find relevant chunks and enhance with external API.")
                
                # First, check if we have existing external analysis to leverage
                saved_analysis = None
                analysis_files = [f for f in os.listdir('.') if f.startswith('external_analysis_') and f.endswith('.json')]
                if analysis_files:
                    # Use the most recent analysis file
                    latest_file = max(analysis_files, key=os.path.getmtime)
                    print(f"📁 Found existing analysis: {latest_file}")
                    try:
                        with open(latest_file, 'r', encoding='utf-8') as f:
                            saved_analysis = json.load(f)
                        print(f"   ✅ Loaded {len(saved_analysis.get('results', []))} previously analyzed chunks")
                    except Exception as e:
                        print(f"   ⚠️ Could not load saved analysis: {e}")
                
                if 'advanced_rag' in locals() and advanced_rag:
                    try:
                        # Use the enhanced query method
                        result = advanced_rag.enhanced_query(
                            user_query,
                            max_chunks=5, # More chunks for better context
                            enable_external_enhancement=True,
                            safety_threshold=0.7
                        )

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
                        
                        if result.get('external_analysis'):
                            enhanced_answer = result['external_analysis'].get('enhanced_answer', 'No enhanced answer provided.')
                            print(f"\n   💡 Enhanced Answer:\n{enhanced_answer}")

                        if result.get('audit_results'):
                            audit = result['audit_results']
                            print(f"   📋 Audit passed: {'✅' if audit.get('audit_passed') else '❌'}")
                            if audit.get('safety_audit'):
                                risk_level = audit['safety_audit'].get('risk_level', 'unknown')
                                print(f"   ⚠️ Risk level: {risk_level}")
                    except Exception as query_error:
                        print(f"   ❌ Query failed: {query_error}")
                        import traceback
                        traceback.print_exc()
                else:
                    print("   ⚠️ Advanced RAG system not available for specific queries.")

        except KeyboardInterrupt:
            print("\n⚠️ Process interrupted by user. Exiting.")
            break
        except Exception as e:
            print(f"\n❌ An error occurred during interactive analysis: {e}")
            import traceback
            traceback.print_exc()

# Only run if this file is executed directly
if __name__ == "__main__":
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n⚠️ Process interrupted by user")
    except Exception as e:
        print(f"\n❌ Error in main execution: {e}")
        import traceback
        traceback.print_exc()