"""
FDA Search Interface - Integrated RAG System
============================================

Complete RAG pipeline for FDA drug data with semantic search,
LLM analysis, and hallucination prevention.
"""

import json
import os
import sys
from pathlib import Path
from integrated_json_rag import IntegratedJSONRAG

# Global RAG system instance
rag_system = None

def initialize_rag_system():
    """
    Initialize the integrated RAG system with GPU acceleration
    """
    global rag_system
    
    if rag_system is None:
        print("🚀 Initializing TokenSight Integrated RAG System...")
        print("=" * 60)
        
        rag_system = IntegratedJSONRAG(
            embedding_model="all-MiniLM-L6-v2",  # Fast, lightweight model
            llm_provider="openai",
            chunk_size=100,  # Reasonable chunk size
            max_context_tokens=80000,  # Leave room for response
            use_gpu=True  # Enable GPU acceleration
        )

# Global RAG system instance
rag_system = None

def initialize_rag_system():
    """
    Initialize the integrated RAG system
    """
    global rag_system
    
    if rag_system is None:
        print("� Initializing TokenSight Integrated RAG System...")
        print("=" * 60)
        
        rag_system = IntegratedJSONRAG(
            embedding_model="all-MiniLM-L6-v2",  # Fast, lightweight model
            llm_provider="openai",
            chunk_size=100,  # Reasonable chunk size
            max_context_tokens=80000  # Leave room for response
        )
        
        # Process FDA file if it exists
        fda_file = "drug-label-0001-of-0013.json"
        if os.path.exists(fda_file):
            print(f"\n📁 Processing FDA file: {fda_file}")
            
            processing_results = rag_system.process_json_file(
                fda_file,
                json_path="results.item"
            )
            
            if processing_results['total_chunks_created'] == 0:
                print("⚠️ No chunks created - check FDA file format")
                return False
            
            print(f"✅ System ready! Processed {processing_results['total_chunks_created']} chunks")
            return True
        else:
            print(f"❌ FDA file not found: {fda_file}")
            print("   Please ensure the FDA file exists in the TokenSight directory")
            return False
    
    return True

def search_fda_chunks(query, max_results=10):
    """
    Search through processed FDA chunks using integrated RAG system
    """
    if not initialize_rag_system():
        print("❌ Could not initialize RAG system")
        return
    
    print(f"🔍 INTEGRATED RAG SEARCH")
    print("=" * 50)
    print(f"Query: {query}")
    print("=" * 50)
    
    # Run the integrated query pipeline
    results = rag_system.integrated_query(
        query,
        top_k_chunks=50,  # Consider more chunks for better results
        similarity_threshold=0.2  # Lower threshold for broader results
    )
    
    # Display results in user-friendly format
    if results['status'] == 'completed':
        print_query_results(results, max_results)
    else:
        print(f"❌ Query failed: {results.get('message', 'Unknown error')}")

def print_query_results(results, max_results=10):
    """
    Display query results in a user-friendly format
    """
    verification = results['verification']
    llm_response = results['llm_response']
    
    print(f"📊 SEARCH RESULTS")
    print("=" * 50)
    
    # Show LLM response
    if 'external_analysis' in llm_response and not llm_response['external_analysis'].get('error'):
        response_content = llm_response['external_analysis']
        print(f"🤖 AI Analysis:")
        print(f"{response_content}")
        print()
    else:
        print("❌ No valid response from AI analysis")
        print()
    
    # Show verification status
    print(f"🛡️ VERIFICATION STATUS")
    print("-" * 30)
    print(f"Status: {verification['verification_status']}")
    print(f"Confidence: {verification['confidence_score']:.2f}")
    print(f"Hallucination detected: {verification['hallucination_detected']}")
    
    if verification['verification_notes']:
        print("Notes:")
        for note in verification['verification_notes']:
            print(f"  {note}")
    
    print()
    
    # Show metadata
    search_info = results['semantic_search']
    context_info = results['context_preparation']
    
    print(f"📈 SEARCH METADATA")
    print("-" * 30)
    print(f"Chunks analyzed: {search_info['chunks_found']}")
    print(f"Chunks used in context: {context_info['chunks_used']}")
    print(f"Search method: {search_info['search_method']}")
    print(f"Processing time: {results['processing_time_seconds']:.2f}s")
    print(f"Context tokens: ~{context_info['estimated_tokens']:,}")
    
    if context_info['chunk_ids']:
        print(f"Source chunks: {', '.join(context_info['chunk_ids'][:5])}{'...' if len(context_info['chunk_ids']) > 5 else ''}")

def query_pediatric_drugs():
    """
    Search for pediatric-relevant drugs with comprehensive analysis
    """
    print("👶 PEDIATRIC DRUG ANALYSIS")
    print("=" * 50)
    
    queries = [
        "How many drugs have been approved for pediatric use?",
        "List medications that are specifically indicated for children and infants",
        "What are the safety considerations for pediatric drug use?",
        "Which drugs have pediatric dosage information available?"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n� Query {i}: {query}")
        print("-" * 40)
        search_fda_chunks(query)
        
        if i < len(queries):
            input("\nPress Enter to continue to next query...")

def query_contraindications():
    """
    Search for drug contraindications with detailed analysis
    """
    print("⚠️ CONTRAINDICATION ANALYSIS")
    print("=" * 50)
    
    queries = [
        "What are the most common drug contraindications?",
        "List drugs with contraindications for pregnant women",
        "Which medications are contraindicated for elderly patients?",
        "Find drugs with serious adverse reactions or black box warnings"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n� Query {i}: {query}")
        print("-" * 40)
        search_fda_chunks(query)
        
        if i < len(queries):
            input("\nPress Enter to continue to next query...")

def custom_query():
    """
    Allow user to enter custom queries
    """
    print("💭 CUSTOM QUERY MODE")
    print("=" * 50)
    print("Enter your query about FDA drug data:")
    print("Examples:")
    print("  - 'Find drugs for treating diabetes'")
    print("  - 'What drugs interact with warfarin?'")
    print("  - 'List antibiotics with pediatric indications'")
    print()
    
    while True:
        query = input("Enter query (or 'back' to return): ").strip()
        
        if query.lower() in ['back', 'exit', 'quit']:
            break
        
        if query:
            search_fda_chunks(query)
            print("\n" + "="*50 + "\n")
        else:
            print("Please enter a valid query.")

def main():
    """
    Interactive FDA search interface with integrated RAG
    """
    print("🏥 TOKENSIGHT FDA INTEGRATED RAG SEARCH")
    print("=" * 60)
    print("Advanced AI-powered search with hallucination prevention")
    print()
    
    # Initialize system
    if not initialize_rag_system():
        print("❌ System initialization failed")
        return
    
    while True:
        print("\n" + "="*60)
        print("Choose an option:")
        print("1. Custom query")
        print("2. Pediatric drug analysis")
        print("3. Contraindication analysis") 
        print("4. System status")
        print("5. Exit")
        
        choice = input("\nEnter choice (1-5): ").strip()
        
        if choice == '1':
            custom_query()
        elif choice == '2':
            query_pediatric_drugs()
        elif choice == '3':
            query_contraindications()
        elif choice == '4':
            show_system_status()
        elif choice == '5':
            print("👋 Goodbye!")
            break
        else:
            print("❌ Invalid choice, try again.")

def show_system_status():
    """
    Show current system status and statistics
    """
    if rag_system is None:
        print("❌ RAG system not initialized")
        return
    
    print("📊 SYSTEM STATUS")
    print("=" * 40)
    print(f"Embedding model: {rag_system.embedding_model_name}")
    print(f"Chunk size: {rag_system.chunk_size:,}")
    print(f"Max context tokens: {rag_system.max_context_tokens:,}")
    print(f"Available chunks: {len(rag_system.chunk_metadata):,}")
    print(f"Embeddings created: {len(rag_system.chunk_embeddings) if hasattr(rag_system, 'chunk_embeddings') else 'N/A'}")
    print(f"Verbatim chunks stored: {len(rag_system.verbatim_chunks):,}")
    
    temp_dir = Path(rag_system.json_processor.temp_dir)
    if temp_dir.exists():
        batch_files = list(temp_dir.glob("*_batch_*.json"))
        print(f"Processed batch files: {len(batch_files)}")
    
    print("✅ System operational and ready for queries")

if __name__ == "__main__":
    main()
