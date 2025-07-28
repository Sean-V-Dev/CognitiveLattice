#!/usr/bin/env python3
"""
Simple Page-Based Visual Extraction
Extracts each PDF page as a high-quality image for efficient visual processing.
This approach is more robust and provides full context for each page.
"""

import os
import sys
import json

def test_dependencies():
    """Test if all required dependencies are available."""
    try:
        import fitz  # PyMuPDF
        import PIL
        print("✅ All dependencies available!")
        return True
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        print("Please install: pip install pymupdf pillow")
        return False

def extract_pdf_pages_as_images(pdf_path, output_dir="pdf_pages"):
    """
    Extract each PDF page as a high-quality image.
    Simple, robust approach that provides full context for each page.
    """
    
    if not test_dependencies():
        return []
    
    import fitz
    
    print(f"📄 Extracting PDF pages as images: {pdf_path}")
    print("=" * 50)
    
    if not os.path.exists(pdf_path):
        print(f"❌ PDF not found: {pdf_path}")
        return []
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    extracted_pages = []
    
    try:
        doc = fitz.open(pdf_path)
        
        print(f"📊 Total pages: {len(doc)}")
        
        for page_num in range(len(doc)):
            page = doc[page_num]
            
            # Convert page to high-quality image (2x scaling for good quality)
            mat = page.get_pixmap(matrix=fitz.Matrix(2, 2))
            
            # Create filename
            page_filename = f"page_{page_num + 1:03d}.png"
            page_filepath = os.path.join(output_dir, page_filename)
            
            # Save the page image
            mat.save(page_filepath)
            
            # Get page text for metadata
            page_text = page.get_text()
            
            # Estimate token usage for this page image
            width, height = mat.width, mat.height
            tiles_width = max(1, width // 512)
            tiles_height = max(1, height // 512)
            estimated_tokens = tiles_width * tiles_height * 85
            
            page_info = {
                "page_number": page_num + 1,
                "filename": page_filename,
                "filepath": page_filepath,
                "text_content": page_text,
                "text_length": len(page_text),
                "dimensions": {"width": width, "height": height},
                "estimated_tokens": estimated_tokens,
                "file_size": os.path.getsize(page_filepath)
            }
            
            extracted_pages.append(page_info)
            
            print(f"  ✅ Page {page_num + 1}: {page_filename} - {width}x{height} (~{estimated_tokens} tokens)")
        
        doc.close()
        
        # Save metadata
        metadata_file = os.path.join(output_dir, "pages_metadata.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump({
                "source_pdf": pdf_path,
                "total_pages": len(extracted_pages),
                "pages": extracted_pages,
                "extraction_info": {
                    "total_estimated_tokens": sum(p["estimated_tokens"] for p in extracted_pages),
                    "total_file_size": sum(p["file_size"] for p in extracted_pages),
                    "average_tokens_per_page": sum(p["estimated_tokens"] for p in extracted_pages) // len(extracted_pages) if extracted_pages else 0
                }
            }, f, indent=2)
        
        print(f"\n🎯 EXTRACTION COMPLETE:")
        print("=" * 30)
        print(f"Pages extracted: {len(extracted_pages)}")
        print(f"Output directory: {output_dir}")
        print(f"Metadata saved: {metadata_file}")
        
        total_tokens = sum(p["estimated_tokens"] for p in extracted_pages)
        total_size = sum(p["file_size"] for p in extracted_pages)
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total estimated tokens: ~{total_tokens:,}")
        print(f"   Total file size: {total_size:,} bytes")
        print(f"   Average tokens per page: ~{total_tokens // len(extracted_pages) if extracted_pages else 0}")
        
        # Open the results folder
        if os.name == 'nt':
            try:
                os.system(f'explorer "{os.path.abspath(output_dir)}"')
                print("📁 Results folder opened!")
            except:
                pass
        
        return extracted_pages
        
    except Exception as e:
        print(f"❌ Error during extraction: {e}")
        return []

def create_page_based_routing_system(pages_metadata):
    """
    Create a routing system that can match queries to relevant pages.
    """
    
    print(f"\n🧠 Creating Page-Based Routing System")
    print("=" * 40)
    
    if not pages_metadata:
        print("❌ No page metadata available")
        return None
    
    # Create searchable page summaries
    page_summaries = []
    
    for page_info in pages_metadata:
        page_num = page_info["page_number"]
        text = page_info["text_content"]
        
        # Extract key terms and concepts from each page
        words = text.lower().split()
        
        # Common technical keywords that might indicate visual content
        visual_keywords = [
            'figure', 'diagram', 'chart', 'table', 'image', 'illustration',
            'step', 'installation', 'assembly', 'maintenance', 'procedure',
            'schematic', 'drawing', 'graph', 'screenshot', 'example'
        ]
        
        found_visual_keywords = [kw for kw in visual_keywords if kw in words]
        
        # Create a summary for this page
        summary = {
            "page_number": page_num,
            "filename": page_info["filename"],
            "filepath": page_info["filepath"],
            "text_preview": text[:300] + "..." if len(text) > 300 else text,
            "word_count": len(words),
            "visual_keywords": found_visual_keywords,
            "has_visual_content": len(found_visual_keywords) > 0,
            "estimated_tokens": page_info["estimated_tokens"]
        }
        
        page_summaries.append(summary)
        
        status = "📊 Visual" if found_visual_keywords else "📝 Text"
        keywords_str = ", ".join(found_visual_keywords[:3]) if found_visual_keywords else "None"
        print(f"  {status} Page {page_num}: {len(words)} words, Keywords: {keywords_str}")
    
    routing_system = {
        "page_summaries": page_summaries,
        "total_pages": len(page_summaries),
        "pages_with_visual_content": len([p for p in page_summaries if p["has_visual_content"]]),
        "all_visual_keywords": list(set(kw for p in page_summaries for kw in p["visual_keywords"]))
    }
    
    print(f"\n✅ Routing system created:")
    print(f"   📄 Total pages: {routing_system['total_pages']}")
    print(f"   📊 Pages with visual content: {routing_system['pages_with_visual_content']}")
    print(f"   � Unique visual keywords: {len(routing_system['all_visual_keywords'])}")
    
    return routing_system

def find_relevant_pages(query, routing_system, max_pages=3):
    """
    Find the most relevant pages for a given query.
    """
    
    if not routing_system:
        return []
    
    query_lower = query.lower()
    page_scores = []
    
    # Check for explicit page references
    import re
    page_match = re.search(r'\bpage\s+(\d+)\b', query_lower)
    if page_match:
        requested_page = int(page_match.group(1))
        print(f"🎯 Explicit page request: Page {requested_page}")
        
        # Return the requested page plus adjacent pages for context
        relevant_pages = []
        for page_num in [requested_page - 1, requested_page, requested_page + 1]:
            for page_summary in routing_system["page_summaries"]:
                if page_summary["page_number"] == page_num:
                    relevant_pages.append({
                        "page_info": page_summary,
                        "relevance_score": 10 if page_num == requested_page else 5,
                        "reason": "Explicit request" if page_num == requested_page else "Context"
                    })
        
        return sorted(relevant_pages, key=lambda x: x["relevance_score"], reverse=True)
    
    # Score pages based on content relevance
    query_words = query_lower.split()
    
    for page_summary in routing_system["page_summaries"]:
        score = 0
        reasons = []
        
        # Check visual keywords match
        for keyword in page_summary["visual_keywords"]:
            if keyword in query_lower:
                score += 3
                reasons.append(f"Visual keyword: {keyword}")
        
        # Check text content match
        page_text = page_summary["text_preview"].lower()
        for word in query_words:
            if len(word) > 3 and word in page_text:  # Skip short words
                score += 1
                
        # Boost pages with visual content for visual queries
        visual_query_indicators = ['show', 'diagram', 'image', 'visual', 'see', 'display', 'illustration']
        if any(indicator in query_lower for indicator in visual_query_indicators):
            if page_summary["has_visual_content"]:
                score += 2
                reasons.append("Has visual content")
        
        if score > 0:
            page_scores.append({
                "page_info": page_summary,
                "relevance_score": score,
                "reasons": reasons
            })
    
    # Sort by relevance and return top results
    page_scores.sort(key=lambda x: x["relevance_score"], reverse=True)
    
    return page_scores[:max_pages]

def get_page_context(page_number, routing_system, include_adjacent=True):
    """
    Get a page with optional adjacent page summaries for context.
    """
    
    result = {
        "main_page": None,
        "previous_page_summary": None,
        "next_page_summary": None,
        "context_pages": []
    }
    
    for page_summary in routing_system["page_summaries"]:
        if page_summary["page_number"] == page_number:
            result["main_page"] = page_summary
        elif include_adjacent:
            if page_summary["page_number"] == page_number - 1:
                result["previous_page_summary"] = page_summary
            elif page_summary["page_number"] == page_number + 1:
                result["next_page_summary"] = page_summary
    
    # Add context pages to list
    if result["previous_page_summary"]:
        result["context_pages"].append(result["previous_page_summary"])
    if result["next_page_summary"]:
        result["context_pages"].append(result["next_page_summary"])
    
    return result

def analyze_extracted_images(output_dir="all_visual_regions"):
    """Analyze the extracted images."""
    
    if not os.path.exists(output_dir):
        print(f"❌ Directory not found: {output_dir}")
        return
    
    import cv2
    
    print(f"\n📊 ANALYZING EXTRACTED IMAGES")
    print("=" * 40)
    
    image_files = [f for f in os.listdir(output_dir) if f.endswith('.png')]
    
    if not image_files:
        print("❌ No extracted images found")
        return
    
    total_size = 0
    image_stats = []
    
    for img_file in image_files:
        img_path = os.path.join(output_dir, img_file)
        
        try:
            # Get file size
            file_size = os.path.getsize(img_path)
            total_size += file_size
            
            # Get image dimensions
            img = cv2.imread(img_path)
            if img is not None:
                height, width = img.shape[:2]
                
                # Estimate token usage (rough calculation)
                # Large vision models typically use ~85 tokens per 512x512 tile
                tiles_width = max(1, width // 512)
                tiles_height = max(1, height // 512) 
                estimated_tokens = tiles_width * tiles_height * 85
                
                image_stats.append({
                    "filename": img_file,
                    "width": width,
                    "height": height,
                    "file_size": file_size,
                    "estimated_tokens": estimated_tokens
                })
                
        except Exception as e:
            print(f"❌ Error analyzing {img_file}: {e}")
    
    # Sort by estimated tokens (most efficient first)
    image_stats.sort(key=lambda x: x["estimated_tokens"])
    
    print(f"📈 EXTRACTED IMAGE ANALYSIS:")
    print("-" * 40)
    
    for i, stats in enumerate(image_stats, 1):
        print(f"{i:2d}. {stats['filename']}")
        print(f"    📏 Size: {stats['width']} x {stats['height']} pixels")
        print(f"    💾 File: {stats['file_size']:,} bytes")
        print(f"    🎯 Est. tokens: ~{stats['estimated_tokens']}")
        print()
    
    total_tokens = sum(stats["estimated_tokens"] for stats in image_stats)
    
    print(f"📊 SUMMARY:")
    print(f"   Total images: {len(image_stats)}")
    print(f"   Total file size: {total_size:,} bytes")
    print(f"   Estimated total tokens: ~{total_tokens:,}")
    print(f"   Average tokens per image: ~{total_tokens // len(image_stats) if image_stats else 0}")
    
    # Compare to full page tokens
    full_page_tokens = 850  # Estimated tokens per full PDF page
    pages_with_content = len(set(stats["filename"].split("_")[1] for stats in image_stats))
    traditional_tokens = pages_with_content * full_page_tokens
    
    if traditional_tokens > 0:
        savings = traditional_tokens - total_tokens
        savings_percent = (savings / traditional_tokens) * 100
        
        print(f"\n💰 TOKEN EFFICIENCY:")
        print(f"   Traditional (full pages): ~{traditional_tokens:,} tokens")
        print(f"   Smart cropping: ~{total_tokens:,} tokens")
        print(f"   Savings: ~{savings:,} tokens ({savings_percent:.1f}%)")

def main():
    """Main extraction function."""
    
    pdf_path = "example.pdf"
    
    print("🎯 Advanced Visual Content Extraction")
    print("=" * 50)
    
    if not test_dependencies():
        print("❌ Missing dependencies")
        print("Please install: pip install opencv-python pymupdf pillow")
        return
    
    # Extract PDF pages as images
    extracted_pages = extract_pdf_pages_as_images(pdf_path, "pdf_pages")
    
    if extracted_pages:
        # Create routing system for the pages
        metadata_file = os.path.join("pdf_pages", "pages_metadata.json")
        if os.path.exists(metadata_file):
            with open(metadata_file, 'r', encoding='utf-8') as f:
                metadata = json.load(f)
                routing_system = create_page_based_routing_system(metadata["pages"])
                
                # Test the routing system with some sample queries
                test_queries = [
                    "How do i install this?",
                    "what does figure 1 show?",
                    "page 2 content",
                    "assembly diagram"
                ]
                
                print(f"\n🔍 Testing Page Routing System:")
                print("=" * 40)
                
                for query in test_queries:
                    relevant_pages = find_relevant_pages(query, routing_system)
                    if relevant_pages:
                        print(f"\nQuery: '{query}'")
                        for result in relevant_pages[:2]:  # Show top 2
                            page_info = result["page_info"]
                            score = result["relevance_score"]
                            print(f"  📄 Page {page_info['page_number']} (score: {score}) - {page_info['filename']}")
                    else:
                        print(f"\nQuery: '{query}' - No relevant pages found")
        
        print(f"\n✅ SUCCESS! Extracted {len(extracted_pages)} pages as images")
        print("This simple approach provides full context for each page!")
    else:
        print("\n⚠️ No pages could be extracted")

if __name__ == "__main__":
    main()
