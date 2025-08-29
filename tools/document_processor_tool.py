"""
Document Processing Tool for CognitiveLattice Framework
Handles document analysis, chunking, and RAG system initialization as a tool
"""

import os
import json
from typing import Dict, Any, Optional
from datetime import datetime

def document_processor(source_file: str, processing_mode: str = "full", enable_external_api: bool = True, session_manager=None) -> Dict[str, Any]:
    """
    A tool that processes documents through the CognitiveLattice pipeline.
    
    Args:
        source_file: Path to the document to process
        processing_mode: "full", "steganographic_only", "chunks_only", or "rag_only"
        enable_external_api: Whether to enable external API calls for the RAG system
    
    Returns:
        Dict containing processing results and RAG system
    """
    print(f"📄 DOCUMENT PROCESSOR: Processing {source_file} in {processing_mode} mode")
    
    try:
        # Import the document processor functions
        from processing.document_processor import (
            run_document_pipeline, 
            run_steganographic_pipeline, 
            process_chunks_only,
            initialize_rag_system
        )
        
        # Load encryption key (this should be in a more secure location in production)
        key_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config", "key.json")
        try:
            with open(key_path, "r") as f:
                config = json.load(f)
                encryption_key = tuple(config["encryption_key"])
        except Exception as key_error:
            print(f"⚠️ Could not load encryption key: {key_error}")
            return {
                "status": "error",
                "message": f"Could not load encryption key: {key_error}",
                "timestamp": datetime.now().isoformat()
            }
        
        # Execute based on processing mode
        if processing_mode == "full":
            # Full pipeline processing
            result = run_document_pipeline(source_file, encryption_key)
            
            # Store RAG system in session manager if available
            rag_system = result.get("advanced_rag_system")
            rag_system_status = "not_initialized"
            
            if rag_system and session_manager:
                from core.rag_manager import get_rag_manager
                rag_manager = get_rag_manager()
                
                # Create unique document ID
                document_id = f"{source_file}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                
                # Store RAG system with metadata
                rag_metadata = {
                    "source_file": source_file,
                    "doc_type": result.get("doc_type"),
                    "total_chunks": result.get("total_chunks", 0),
                    "processing_mode": processing_mode,
                    "document_id": document_id
                }
                
                if rag_manager.store_rag_system(document_id, rag_system, rag_metadata):
                    rag_system_status = "stored_in_session"
                    print(f"✅ RAG system stored for document: {document_id}")
            
            processed_content = {
                "doc_type": result.get("doc_type"),
                "total_chunks": result.get("total_chunks", 0),
                "chunks": result.get("chunks", []),
                "advanced_rag_system": rag_system_status,
                "page_images_data": result.get("page_images_data", []),
                "processing_success": result.get("processing_success", False),
                "summary": f"Successfully processed {result.get('total_chunks', 0)} chunks from {source_file}",
                "timestamp": datetime.now().isoformat()
            }
            
            # Save to lattice if session_manager is provided
            if session_manager is not None:
                session_manager.lattice.add_event({
                    "type": "document_processed",
                    "timestamp": datetime.now().isoformat(),
                    "source_file": source_file,
                    "processing_mode": processing_mode,
                    "content": processed_content,
                    "status": "completed"
                })
            
            return {
                "status": "success",
                "processing_mode": processing_mode,
                "source_file": source_file,
                **processed_content
            }
            
        elif processing_mode == "steganographic_only":
            # Just the encode/decode pipeline
            decoded_path = run_steganographic_pipeline(source_file, encryption_key)
            
            return {
                "status": "success",
                "processing_mode": processing_mode,
                "source_file": source_file,
                "decoded_file": decoded_path,
                "summary": f"Steganographic processing complete: {decoded_path}",
                "timestamp": datetime.now().isoformat()
            }
            
        elif processing_mode == "chunks_only":
            # Just chunking from existing decoded file
            decoded_path = "decoded.txt"  # Assume it exists
            if not os.path.exists(decoded_path):
                return {
                    "status": "error",
                    "message": f"Decoded file {decoded_path} not found. Run steganographic processing first.",
                    "timestamp": datetime.now().isoformat()
                }
            
            chunks = process_chunks_only(decoded_path)
            
            return {
                "status": "success",
                "processing_mode": processing_mode,
                "source_file": source_file,
                "total_chunks": len(chunks),
                "chunks": chunks,
                "summary": f"Processed {len(chunks)} chunks from {decoded_path}",
                "timestamp": datetime.now().isoformat()
            }
            
        elif processing_mode == "rag_only":
            # Initialize RAG system with existing chunks (assumes chunks exist)
            # This would need chunk data passed in or loaded from somewhere
            return {
                "status": "error",
                "message": "RAG-only mode requires existing chunk data. Use full mode instead.",
                "timestamp": datetime.now().isoformat()
            }
            
        else:
            return {
                "status": "error",
                "message": f"Unknown processing mode: {processing_mode}",
                "timestamp": datetime.now().isoformat()
            }
            
    except Exception as e:
        return {
            "status": "error",
            "source_file": source_file,
            "processing_mode": processing_mode,
            "error": str(e),
            "message": f"Document processing failed: {e}",
            "timestamp": datetime.now().isoformat()
        }

def document_query(query: str, rag_system=None, max_chunks: int = 5, session_manager=None) -> Dict[str, Any]:
    """
    A tool that queries a previously processed document using the RAG system.
    
    Args:
        query: The query to search for
        rag_system: The CognitiveLatticeAdvancedRAG system (from previous document_processor results)
        max_chunks: Maximum number of chunks to return
        session_manager: Session manager for accessing stored RAG systems
    
    Returns:
        Dict containing query results
    """
    print(f"🔍 DOCUMENT QUERY: Searching for '{query}'")
    
    # Try to get RAG system from session manager first
    if session_manager is not None:
        from core.rag_manager import get_rag_manager
        rag_manager = get_rag_manager()
        
        # Get the most recent RAG system
        active_rag_system = rag_manager.get_rag_system()
        rag_metadata = rag_manager.get_metadata()
        
        if active_rag_system and hasattr(active_rag_system, 'enhanced_query'):
            try:
                # Use the actual RAG system for querying
                results = active_rag_system.enhanced_query(query, max_chunks=max_chunks)
                
                # Extract the enhanced answer from the complex results structure
                enhanced_answer = None
                external_analysis = results.get("external_analysis", {})
                
                if isinstance(external_analysis, dict) and "enhanced_answer" in external_analysis:
                    enhanced_answer = external_analysis["enhanced_answer"]
                elif isinstance(external_analysis, dict) and "summary_text" in external_analysis:
                    enhanced_answer = external_analysis["summary_text"]
                
                # Fallback to local results if no external answer
                if not enhanced_answer:
                    local_results = results.get("local_results", {}).get("results", [])
                    if local_results:
                        enhanced_answer = "\n\n".join([
                            f"**Chunk {i+1}:** {chunk.get('content', '')[:500]}..." 
                            for i, chunk in enumerate(local_results[:3])
                        ])
                
                # Final fallback
                if not enhanced_answer:
                    enhanced_answer = "Document processed successfully, but no specific answer could be generated for this query."
                
                return {
                    "status": "success",
                    "query": query,
                    "source_file": rag_metadata.get("source_file", "unknown") if rag_metadata else "unknown",
                    "total_chunks": rag_metadata.get("total_chunks", 0) if rag_metadata else 0,
                    "method": "advanced_rag_query",
                    "enhanced_answer": enhanced_answer,
                    "raw_results": results,  # Include raw results for debugging
                    "summary": f"Found relevant information using advanced RAG system.",
                    "timestamp": datetime.now().isoformat()
                }
            except Exception as e:
                print(f"⚠️ RAG system query failed, falling back to lattice search: {e}")
    
    # Fallback to lattice-based search if RAG system is not available
    if session_manager is not None:
        # Get recent document processing events from lattice
        try:
            all_events = session_manager.lattice.events
            doc_events = [e for e in all_events if e.get("type") == "document_processed"]
            
            if doc_events:
                latest = doc_events[-1]  # Get most recent
                content = latest.get("content", {})
                
                # Extract useful information from the processed content
                chunks = content.get("chunks", [])
                total_chunks = content.get("total_chunks", 0)
                source_file = latest.get("source_file", "unknown")
                
                if chunks and len(chunks) > 0:
                    # Search through chunks for relevant content
                    relevant_chunks = []
                    query_lower = query.lower()
                    
                    for i, chunk in enumerate(chunks[:max_chunks]):  # Limit search
                        chunk_text = str(chunk).lower()
                        if any(word in chunk_text for word in query_lower.split()):
                            relevant_chunks.append({
                                "chunk_number": i + 1,
                                "content": str(chunk)[:500] + "..." if len(str(chunk)) > 500 else str(chunk)
                            })
                    
                    if relevant_chunks:
                        return {
                            "status": "success",
                            "query": query,
                            "source_file": source_file,
                            "total_chunks": total_chunks,
                            "method": "lattice_fallback_search",
                            "relevant_chunks_found": len(relevant_chunks),
                            "relevant_chunks": relevant_chunks,
                            "summary": f"Found {len(relevant_chunks)} relevant chunks in {source_file} using fallback search.",
                            "timestamp": datetime.now().isoformat()
                        }
                    else:
                        return {
                            "status": "success",
                            "query": query,
                            "source_file": source_file,
                            "total_chunks": total_chunks,
                            "relevant_chunks_found": 0,
                            "summary": f"Document {source_file} has been processed with {total_chunks} chunks, but no content directly matches your query '{query}'.",
                            "timestamp": datetime.now().isoformat()
                        }
                else:
                    return {
                        "status": "success",
                        "query": query,
                        "source_file": source_file,
                        "total_chunks": 0,
                        "summary": f"Document {source_file} was processed but contains no extractable chunks.",
                        "timestamp": datetime.now().isoformat()
                    }
            else:
                return {
                    "status": "error",
                    "message": "No document has been processed yet. Please use the document_processor tool first.",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Error accessing lattice: {e}",
                "timestamp": datetime.now().isoformat()
            }
    else:
        return {
            "status": "error",
            "message": "Session manager not available.",
            "timestamp": datetime.now().isoformat()
        }
    
    if not rag_system:
        return {
            "status": "error",
            "message": "No RAG system available. Process a document first using document_processor tool.",
            "timestamp": datetime.now().isoformat()
        }
    
    try:
        # Use the RAG system to query
        result = rag_system.enhanced_query(
            query,
            max_chunks=max_chunks,
            enable_external_enhancement=True,  # Can be made configurable
            safety_threshold=0.7
        )
        
        return {
            "status": "success",
            "query": query,
            "chunks_found": len(result.get('local_results', {}).get('results', [])),
            "external_analysis": result.get('external_analysis'),
            "local_results": result.get('local_results'),
            "audit_results": result.get('audit_results'),
            "safety_status": result.get('safety_status', 'unknown'),
            "summary": f"Found {len(result.get('local_results', {}).get('results', []))} relevant chunks for query",
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "status": "error",
            "query": query,
            "error": str(e),
            "message": f"Document query failed: {e}",
            "timestamp": datetime.now().isoformat()
        }