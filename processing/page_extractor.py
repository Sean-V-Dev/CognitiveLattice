"""
Page Extraction Module for CognitiveLattice
Handles PDF page-based extraction and visual content analysis
"""

import os
import json

# Page-based extraction imports
try:
    import fitz  # PyMuPDF
    from PIL import Image
    PAGE_EXTRACTION_AVAILABLE = True
except ImportError:
    PAGE_EXTRACTION_AVAILABLE = False


def get_visual_content_for_llm_routing(page_number=None, visual_keywords=None):
    """
    Prepare visual content metadata for routing to large vision models.
    Returns structured context for external API calls.
    
    Args:
        page_number: Specific page number to analyze
        visual_keywords: List of visual content keywords
        
    Returns:
        Dictionary with visual content routing information
    """
    visual_context = {
        "visual_elements_found": [],
        "page_references": [],
        "routing_recommendation": "local"
    }
    
    # Check if we need external vision model
    high_value_keywords = ["diagram", "chart", "graph", "technical", "blueprint", "schematic"]
    if visual_keywords:
        if any(keyword in visual_keywords for keyword in high_value_keywords):
            visual_context["routing_recommendation"] = "external_vision_model"
    
    return visual_context


def integrate_page_based_extraction(pdf_path, output_dir="pdf_pages"):
    """
    Extract each PDF page as a full image for comprehensive visual processing.
    
    Args:
        pdf_path: Path to the PDF file
        output_dir: Directory to save extracted page images
        
    Returns:
        List of page information dictionaries
    """
    if not PAGE_EXTRACTION_AVAILABLE:
        print("⚠️ Page extraction dependencies not available - using fallback")
        return []
    
    print(f"📄 Extracting PDF pages as images: {pdf_path}")
    
    os.makedirs(output_dir, exist_ok=True)
    doc = fitz.open(pdf_path)
    extracted_pages = []
    
    for page_num in range(len(doc)):
        page = doc[page_num]
        
        # Extract text for keyword analysis
        text_content = page.get_text()
        
        # Render page as high-quality image
        mat = fitz.Matrix(2, 2)  # 2x scaling for quality
        pix = page.get_pixmap(matrix=mat)
        
        # Save as PNG
        filename = f"page_{page_num+1:03d}.png"
        filepath = os.path.join(output_dir, filename)
        pix.save(filepath)
        
        # Analyze text for visual keywords
        visual_keywords = []
        keyword_patterns = {
            'diagram': ['diagram', 'figure', 'fig', 'illustration', 'drawing'],
            'table': ['table', 'chart', 'graph', 'data'],
            'installation': ['install', 'setup', 'assembly', 'mount'],
            'parts': ['parts', 'components', 'items', 'pieces'],
            'procedure': ['step', 'procedure', 'instruction', 'process'],
            'maintenance': ['maintenance', 'service', 'repair', 'clean']
        }
        
        text_lower = text_content.lower()
        for category, keywords in keyword_patterns.items():
            if any(keyword in text_lower for keyword in keywords):
                visual_keywords.append(category)
        
        # Estimate token usage for vision models
        img = Image.open(filepath)
        width, height = img.size
        tiles_width = max(1, width // 512)
        tiles_height = max(1, height // 512)
        estimated_tokens = tiles_width * tiles_height * 85  # Standard vision model calculation
        
        page_info = {
            "page_number": page_num + 1,
            "filename": filename,
            "filepath": filepath,
            "text_content": text_content,
            "visual_keywords": visual_keywords,
            "has_visual_content": bool(visual_keywords),
            "dimensions": {"width": width, "height": height},
            "estimated_tokens": estimated_tokens,
            "text_length": len(text_content)
        }
        
        extracted_pages.append(page_info)
        
        status = "📊 Visual" if visual_keywords else "📝 Text"
        keywords_str = ", ".join(visual_keywords[:3]) if visual_keywords else "None"
        print(f"  {status} Page {page_num+1}: {estimated_tokens} tokens, Keywords: {keywords_str}")
    
    doc.close()
    
    # Save metadata
    metadata = {
        "source_pdf": pdf_path,
        "total_pages": len(extracted_pages),
        "output_directory": output_dir,
        "pages": extracted_pages,
        "total_estimated_tokens": sum(p["estimated_tokens"] for p in extracted_pages),
        "pages_with_visual_content": len([p for p in extracted_pages if p["has_visual_content"]])
    }
    
    metadata_file = os.path.join(output_dir, "pages_metadata.json")
    with open(metadata_file, 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)
    
    total_tokens = metadata["total_estimated_tokens"]
    visual_pages = metadata["pages_with_visual_content"]
    
    print(f"✅ Extracted {len(extracted_pages)} pages to {output_dir}")
    print(f"📊 Summary: {visual_pages} visual pages, ~{total_tokens:,} total tokens")
    
    return extracted_pages
