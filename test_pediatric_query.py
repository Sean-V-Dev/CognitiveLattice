"""
Test script to demonstrate real pediatric drug queries with actual FDA data
"""

from integrated_json_rag import IntegratedJSONRAG

def test_pediatric_drugs():
    """Test the integrated system with a pediatric drug query"""
    
    print("🧪 TESTING PEDIATRIC DRUG QUERIES WITH REAL FDA DATA")
    print("=" * 70)
    
    # Initialize the system with adaptive specialized models
    rag_system = IntegratedJSONRAG(
        embedding_model="adaptive",  # Use specialized models automatically
        llm_provider="openai", 
        chunk_size=100,
        max_context_tokens=80000,
        use_gpu=True,  # Enable GPU acceleration
        specialized_models=True  # Enable domain-specific models
    )
    
    # Process FDA file to get real drug data
    fda_file = "drug-label-0001-of-0013.json"
    print(f"\n📁 Processing FDA file: {fda_file}")
    
    processing_results = rag_system.process_json_file(
        fda_file,
        json_path="results.item"
    )
    
    if processing_results['total_chunks_created'] == 0:
        print("❌ No chunks were created")
        return
    
    # Test pediatric-specific queries
    pediatric_queries = [
        "List drugs that are approved for pediatric use",
        "Which medications are safe for children and infants?", 
        "What drugs have pediatric dosage information?",
        "Show me medications indicated for children"
    ]
    
    for query in pediatric_queries:
        print(f"\n" + "🔍" + "="*60)
        print(f"QUERY: {query}")
        print("="*70)
        
        # Run the integrated query
        results = rag_system.integrated_query(
            query,
            top_k_chunks=20,
            similarity_threshold=0.15  # Lower threshold to catch more results
        )
        
        if results['status'] == 'completed':
            # Extract and show the actual drug information
            llm_response = results['llm_response']
            verification = results['verification']
            
            print(f"🤖 AI ANALYSIS:")
            print("-" * 40)
            
            if 'external_analysis' in llm_response:
                analysis = llm_response['external_analysis']
                print(f"{analysis}")
            
            print(f"\n🛡️ VERIFICATION:")
            print(f"Status: {verification['verification_status']}")
            print(f"Confidence: {verification.get('confidence_score', 0.0):.2f}")
            print(f"Hallucination detected: {verification.get('hallucination_detected', 'Unknown')}")
            
            if 'error' in verification:
                print(f"⚠️ Verification error: {verification['error']}")
            
            print(f"\n📊 SEARCH STATS:")
            search_info = results['semantic_search']
            context_info = results['context_preparation']
            print(f"Chunks analyzed: {search_info['chunks_found']}")
            print(f"Context chunks used: {context_info['chunks_used']}")
            print(f"Processing time: {results['processing_time_seconds']:.2f}s")
            
            # Show some of the actual source chunks used
            print(f"\n📄 SOURCE CHUNKS (sample):")
            for chunk_id in context_info['chunk_ids'][:3]:
                if chunk_id in rag_system.verbatim_chunks:
                    chunk_content = rag_system.verbatim_chunks[chunk_id]
                    print(f"\n📋 {chunk_id}:")
                    print(f"{chunk_content[:300]}...")
        
        else:
            print(f"❌ Query failed: {results.get('message', 'Unknown error')}")
        
        print("\n" + "="*70)
        
        # Wait a bit between queries for rate limiting
        import time
        time.sleep(2)

if __name__ == "__main__":
    test_pediatric_drugs()
