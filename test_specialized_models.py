"""
Test script to demonstrate specialized embedding models for different document types
"""

from integrated_json_rag import IntegratedJSONRAG

def test_specialized_models():
    """Test the integrated system with specialized models"""
    
    print("🧪 TESTING SPECIALIZED EMBEDDING MODELS")
    print("=" * 70)
    
    # Test 1: Adaptive mode with specialized models
    print("\n🎯 TEST 1: Adaptive Mode with Specialized Models")
    print("-" * 50)
    
    rag_system = IntegratedJSONRAG(
        embedding_model="adaptive",  # Use specialized models
        llm_provider="openai", 
        chunk_size=100,
        max_context_tokens=80000,
        use_gpu=True,
        specialized_models=True  # Enable multiple models
    )
    
    # Process FDA file (should detect medical_pharmaceutical domain)
    fda_file = "drug-label-0001-of-0013.json"
    print(f"\n📁 Processing FDA file: {fda_file}")
    
    processing_results = rag_system.process_json_file(
        fda_file,
        json_path="results.item"
    )
    
    if processing_results['total_chunks_created'] > 0:
        print(f"\n✅ Processed {len(rag_system.chunk_metadata)} chunks")
        print(f"🎯 Detected domain: {rag_system.current_document_domain}")
        
        # Test query with specialized model
        query = "List drugs approved for pediatric use"
        print(f"\n🔍 Testing query: {query}")
        
        results = rag_system.integrated_query(
            query,
            top_k_chunks=5,
            similarity_threshold=0.15
        )
        
        if results['status'] == 'completed':
            print(f"✅ Query successful!")
            print(f"   📊 Found {len(results['semantic_search']['results'])} relevant chunks")
            print(f"   🎯 Used domain-specific model: {rag_system.current_document_domain}")
            print(f"   ⏱️ Processing time: {results['processing_time_seconds']:.2f}s")
        else:
            print(f"❌ Query failed: {results.get('message', 'Unknown error')}")
    
    print("\n" + "=" * 70)
    
    # Test 2: Single model mode (backward compatibility)
    print("\n🎯 TEST 2: Single Model Mode (Backward Compatibility)")
    print("-" * 50)
    
    single_rag = IntegratedJSONRAG(
        embedding_model="all-MiniLM-L6-v2",  # Specific single model
        llm_provider="openai", 
        chunk_size=100,
        max_context_tokens=80000,
        use_gpu=True,
        specialized_models=False  # Disable specialized models
    )
    
    print(f"✅ Single model system initialized")
    print(f"   🎯 Using: all-MiniLM-L6-v2 (general purpose)")
    
    print("\n" + "=" * 70)
    
    # Test 3: Model comparison
    print("\n🎯 TEST 3: Available Specialized Models")
    print("-" * 50)
    
    if rag_system.rag_systems:
        for domain, model_info in rag_system.rag_systems.items():
            print(f"📋 {domain.replace('_', ' ').title()}:")
            print(f"   🤖 Model: {model_info['model_name']}")
            print(f"   📐 Dimensions: {model_info['vector_dim']}")
            print(f"   📝 Description: {model_info['description']}")
            print(f"   ✅ Loaded: {'Yes' if model_info['model'] is not None else 'No'}")
            print()

def compare_model_performance():
    """Compare performance between specialized and general models"""
    
    print("📊 MODEL PERFORMANCE COMPARISON")
    print("=" * 50)
    
    # This would require processing the same data with different models
    # and comparing embedding quality, but that's beyond this demo
    
    print("🎯 Performance characteristics:")
    print("   📈 allenai/specter: Best for scientific/medical content")
    print("   📈 all-mpnet-base-v2: Best for legal/regulatory content")  
    print("   📈 all-MiniLM-L12-v2: Balanced for technical content")
    print("   📈 all-MiniLM-L6-v2: Fastest for general content")
    
    print("\n✅ Adaptive model selection provides:")
    print("   🎯 Domain-specific accuracy improvements")
    print("   🚀 Optimized embedding quality per document type")
    print("   🔄 Automatic model selection based on content")
    print("   ⚡ GPU acceleration for all models")

if __name__ == "__main__":
    test_specialized_models()
    print("\n")
    compare_model_performance()
