"""
Document processing functions - now used by the document_processor_tool
"""

import os
import sys
import traceback
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.dictionary_manager import expand_dictionary, clean_input
from encoder.text_to_image import encode_text_to_image
from decoder.image_to_text import decode_image_to_text
from text_processor import extract_paragraphs, chunk_paragraphs
from file_handler import process_file
from llama_client import diagnose_content_type
from page_extractor import integrate_page_based_extraction, PAGE_EXTRACTION_AVAILABLE

def run_document_pipeline(source_input: str, encryption_key: tuple) -> Dict[str, Any]:
    """
    Runs the full document processing pipeline on a given source file.
    Now returns a clean dictionary suitable for tool integration.
    """
    print("🚀 Starting Document Processing Pipeline...")
    print(f"📄 Source: {source_input}")

    try:
        # Check if source file exists
        if not os.path.exists(source_input):
            return {
                "processing_success": False,
                "error": f"Source file not found: {source_input}",
                "source_file": source_input
            }

        # === Steganographic Pipeline === #
        decoded_path = run_steganographic_pipeline(source_input, encryption_key)
        
        # === Chunking === #
        chunks = process_chunks_only(decoded_path)
        
        # === Document Type Detection === #
        if chunks:
            middle_idx = len(chunks) // 2
            middle_chunk_text = chunks[middle_idx].get('content', '')
            doc_type = diagnose_content_type(middle_chunk_text)
        else:
            doc_type = "unknown"
        
        print(f"📋 Detected document type: {doc_type}")

        # === PDF Page Extraction (Optional) === #
        page_images_data = []
        if source_input.endswith(".pdf") and PAGE_EXTRACTION_AVAILABLE:
            try:
                page_images_data = integrate_page_based_extraction(source_input, "pdf_pages")
                print(f"🖼️ Extracted {len(page_images_data)} page images")
            except Exception as e:
                print(f"⚠️ Page extraction failed: {e}")

        # === Initialize RAG System === #
        advanced_rag = initialize_rag_system(chunks, source_input, doc_type)

        print("✅ Document Processing Pipeline Complete")
        
        return {
            "processing_success": True,
            "source_file": source_input,
            "doc_type": doc_type,
            "total_chunks": len(chunks),
            "chunks": chunks,
            "advanced_rag_system": advanced_rag,
            "page_images_data": page_images_data,
            "decoded_file": decoded_path
        }

    except Exception as e:
        print(f"❌ Document processing failed: {e}")
        traceback.print_exc()
        return {
            "processing_success": False,
            "error": str(e),
            "source_file": source_input
        }

def run_steganographic_pipeline(source_input: str, encryption_key: tuple) -> str:
    """Run steganographic encode/decode pipeline."""
    print("🔒 Running steganographic pipeline...")
    
    raw_lines = process_file(source_input, enable_multimodal=False)
    text = "\n".join(raw_lines)
    cleaned = clean_input(text)
    expand_dictionary(cleaned)
    
    img_path = "cache/decode_once.png"
    os.makedirs("cache", exist_ok=True)
    encode_text_to_image(cleaned, img_path, encryption_key)
    
    decoded_path = "decoded.txt"
    decode_image_to_text(img_path, decoded_path, encryption_key)
    
    print(f"✅ Steganographic pipeline complete: {decoded_path}")
    return decoded_path

def process_chunks_only(decoded_path: str, doc_type: str = None) -> List[Dict[str, Any]]:
    """Process text into chunks."""
    print("📄 Processing chunks...")
    
    lines = process_file(decoded_path, enable_multimodal=False)
    paragraphs = extract_paragraphs(lines)
    chunks = chunk_paragraphs(paragraphs, max_tokens=450)
    
    # Auto-detect document type if not provided
    if not doc_type and chunks:
        middle_idx = len(chunks) // 2
        middle_chunk_text = "\n".join(chunks[middle_idx])
        doc_type = diagnose_content_type(middle_chunk_text)
    
    chunk_storage = []
    for i, chunk in enumerate(chunks):
        chunk_id = f"chunk_{i+1}"
        text = "\n".join(chunk)
        chunk_data = {
            "chunk_id": chunk_id,
            "source_type": doc_type or "unknown",
            "content": text,
            "chunk_index": i,
            "original_text_length": len(text),
            "processing_method": "verbatim_extraction"
        }
        chunk_storage.append(chunk_data)
    
    print(f"✅ Processed {len(chunk_storage)} chunks")
    return chunk_storage

def initialize_rag_system(chunk_storage: List[Dict[str, Any]], 
                         source_input: str, 
                         doc_type: str,
                         enable_external_api: bool = True):
    """Initialize RAG system with processed chunks."""
    print("🧠 Initializing RAG system...")
    
    try:
        from tokensight_advanced_rag import TokenSightAdvancedRAG
        
        advanced_rag = TokenSightAdvancedRAG(enable_external_api=enable_external_api)
        
        doc_info = {
            "source": source_input,
            "type": doc_type,
            "total_chunks": len(chunk_storage),
            "processing_method": "verbatim_extraction"
        }
        
        advanced_rag.process_document_chunks(chunk_storage, doc_info)
        print(f"✅ RAG system initialized with {len(chunk_storage)} chunks")
        
        return advanced_rag
        
    except Exception as e:
        print(f"⚠️ RAG system initialization failed: {e}")
        return None