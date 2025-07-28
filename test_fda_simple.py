"""
Simple FDA Test Script
======================

Quick test of the massive JSON processor with your actual FDA file
"""

from massive_json_processor import MassiveJSONProcessor

def test_fda_file():
    print("🧪 Testing FDA File Processing")
    print("=" * 50)
    
    # Initialize processor with small chunk size for testing
    processor = MassiveJSONProcessor(
        chunk_size=50,  # Small for testing
        temp_dir="fda_test_temp"
    )
    
    
    file_path = "drug-label-0001-of-0013.json"
    
    try:
        print(f"📁 Processing: {file_path}")
        
        # FDA files have structure: {"results": [...]}
        results = processor.process_single_file(
            file_path,
            json_path="results.item",  # Correct path for FDA structure
            save_intermediate=True
        )
        
        print(f"\n✅ Test Complete!")
        print(f"   📊 Batches processed: {results['batches_processed']}")
        print(f"   🧩 Chunks created: {results['total_chunks_created']}")
        print(f"   📁 File size: {results['structure_analysis']['file_size_mb']:.1f} MB")
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_fda_file()
