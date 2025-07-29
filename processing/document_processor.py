"""
Document Processing Pipeline - Core document processing orchestration
Extracted from main.py for better modularity and testability
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from utils.dictionary_manager import expand_dictionary, clean_input
from encoder.text_to_image import encode_text_to_image
from decoder.image_to_text import decode_image_to_text
from text_processor import extract_paragraphs, chunk_paragraphs
from file_handler import process_file
from llama_client import diagnose_content_type
from page_extractor import integrate_page_based_extraction, PAGE_EXTRACTION_AVAILABLE
from memory_manager import initialize_memory


class DocumentProcessor:
    """
    Handles the complete document processing pipeline including:
    - Steganographic encoding/decoding
    - Chunking and text processing
    - PDF page extraction
    - Document type detection
    """
    
    def __init__(self, encryption_key: tuple):
        self.encryption_key = encryption_key
        self.memory = initialize_memory()
        
    def process_document(self, source_input: str, enable_multimodal: bool = None) -> Dict[str, Any]:
        """
        Complete document processing pipeline
        
        Args:
            source_input: Path to source document
            enable_multimodal: Enable PDF page extraction (auto-detected if None)
            
        Returns:
            Dictionary containing processed chunks, metadata, and extracted content
        """
        if enable_multimodal is None:
            enable_multimodal = source_input.endswith(".pdf")
            
        print(f"📄 Source: {source_input}")
        print(f"🖼️ Multimodal enabled: {enable_multimodal}")
        print(f"⚙️ Page extraction available: {PAGE_EXTRACTION_AVAILABLE}")

        # Ensure decoded.txt exists or create it
        decoded_path = "decoded.txt"
        regenerate_needed = self._check_regeneration_needed(source_input, decoded_path)
        
        if regenerate_needed:
            print("🕒 Running full encode-decode pipeline...")
            self._run_encode_decode_pipeline(source_input, decoded_path)
            print(f"✅ decoded.txt generated from {source_input}")

        # Process chunks
        lines = process_file(decoded_path, enable_multimodal=False)
        paragraphs = extract_paragraphs(lines)
        chunks = chunk_paragraphs(paragraphs, max_tokens=450)

        # Extract PDF pages if needed
        page_images_data = []
        if enable_multimodal and source_input.endswith(".pdf"):
            page_images_data = self._extract_pdf_pages(source_input)

        # Process chunks with steganographic verification
        chunk_storage = self._process_chunks(chunks)
        
        # Detect document type
        doc_type = self._detect_document_type(chunks)
        print(f"📋 Detected document type: {doc_type}")

        return {
            "chunks": chunk_storage,
            "document_type": doc_type,
            "page_images": page_images_data,
            "source": source_input,
            "multimodal_enabled": enable_multimodal,
            "total_chunks": len(chunk_storage),
            "processing_timestamp": datetime.now().isoformat()
        }
    
    def _check_regeneration_needed(self, source_input: str, decoded_path: str) -> bool:
        """Check if we need to regenerate decoded.txt for new source"""
        source_cache_file = "cache/last_source.txt"
        os.makedirs("cache", exist_ok=True)
        
        if os.path.exists(decoded_path) and os.path.exists(source_cache_file):
            try:
                with open(source_cache_file, 'r') as f:
                    last_source = f.read().strip()
                if last_source == source_input:
                    print("♻️ Using existing decoded.txt (same source)")
                    return False
                else:
                    print(f"🔄 Source changed from {last_source} to {source_input} - regenerating...")
                    return True
            except:
                print("⚠️ Could not read source cache - regenerating...")
                return True
        
        return True
    
    def _run_encode_decode_pipeline(self, source_input: str, decoded_path: str):
        """Run the full steganographic encode-decode pipeline"""
        raw_lines = process_file(source_input, enable_multimodal=False)
        text = "\n".join(raw_lines)
        cleaned = clean_input(text)

        expand_dictionary(cleaned)
        img_path = "cache/decode_once.png"
        os.makedirs("cache", exist_ok=True)
        encode_text_to_image(cleaned, img_path, self.encryption_key)
        decode_image_to_text(img_path, decoded_path, self.encryption_key)

        # Cache the source file name
        source_cache_file = "cache/last_source.txt"
        with open(source_cache_file, 'w') as f:
            f.write(source_input)
    
    def _extract_pdf_pages(self, source_input: str) -> List[Dict[str, Any]]:
        """Extract PDF pages as images if multimodal is enabled"""
        print("📄 Extracting PDF pages as images...")
        page_images_data = integrate_page_based_extraction(source_input, "pdf_pages")
        
        if page_images_data:
            print(f"🖼️ Processing {len(page_images_data)} page images...")
            prepared_images = []
            
            for page_info in page_images_data:
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
                prepared_images.append(image_data)
                print(f"🖼️ Prepared image {image_data['image_id']} for advanced processing")
            
            print(f"✅ Prepared {len(prepared_images)} page images for knowledge base")
            return prepared_images
        else:
            print("📷 Page extraction not available - continuing with text-only processing")
            return []
    
    def _process_chunks(self, chunks: List[List[str]]) -> List[Dict[str, Any]]:
        """Process chunks with steganographic encoding/decoding"""
        output_img_dir = "encoded_chunks"
        output_txt_dir = "decoded_chunks"
        os.makedirs(output_img_dir, exist_ok=True)
        os.makedirs(output_txt_dir, exist_ok=True)

        chunk_storage = []
        
        for i, chunk in enumerate(chunks):
            chunk_id = f"chunk_{i+1}"
            text = "\n".join(chunk)
            
            # Steganographic encoding/decoding (preserves encryption)
            cleaned = clean_input(text)
            expand_dictionary(cleaned)
            
            img_path = os.path.join(output_img_dir, f"{chunk_id}.png")
            encode_text_to_image(cleaned, img_path, self.encryption_key)
            print(f"✅ Encoded image saved to {img_path}")
            
            decoded_path = os.path.join(output_txt_dir, f"{chunk_id}.txt")
            decode_image_to_text(img_path, decoded_path, self.encryption_key)
            print(f"✅ Decoded text saved to {decoded_path}")
            
            with open(decoded_path, encoding="utf-8") as f:
                decoded = f.read().strip()
            
            # Create structured chunk data (using raw text for modern processing)
            chunk_data = {
                "chunk_id": chunk_id,
                "content": decoded,  # Raw text for modern RAG systems
                "original_text_length": len(decoded),
                "chunk_index": i,
                "inferred_modality": "text",
                "processing_method": "verbatim_extraction",
                "encoded_image_path": img_path,
                "decoded_text_path": decoded_path,
                "timestamp": datetime.now().isoformat()
            }
            
            chunk_storage.append(chunk_data)
            
            # Store in memory for legacy compatibility
            self.memory[chunk_id] = decoded
            
            print(f"✅ Chunk {chunk_id} extracted (verbatim text, no LLM processing)")
        
        return chunk_storage
    
    def _detect_document_type(self, chunks: List[List[str]]) -> str:
        """Detect document type from middle chunk"""
        if not chunks:
            return "unknown"
            
        middle_idx = len(chunks) // 2
        middle_chunk_text = "\n".join(chunks[middle_idx])
        return diagnose_content_type(middle_chunk_text)
    
    def get_memory(self):
        """Get the memory manager instance"""
        return self.memory
