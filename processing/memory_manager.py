"""
Memory Management Module for CognitiveLattice
Handles memory search and chunk memory operations with semantic search capabilities
"""




def search_memory(memory, keyword, use_semantic=True, max_results=5):
    """
    Search through memory chunks for a specific keyword with semantic understanding.
    
    Args:
        memory: Dictionary of chunk_id -> summary mappings (legacy support)
        keyword: Keyword or query to search for
        use_semantic: Whether to use semantic search (True) or literal search (False)
        max_results: Maximum number of results to return
        
    Returns:
        None (prints results directly)
    """
    print(f"\n🔍 Searching for: '{keyword}'")
    
    if use_semantic and len(chunk_metadata) > 0:
        # Use semantic search through RAG system
        print("🧠 Using semantic search...")
        
        # Get semantically similar chunks from RAG system
        similar_chunks = retrieve_similar_summaries(keyword, k=max_results)
        
        if similar_chunks:
            print(f"\n🎯 Found {len(similar_chunks)} semantically relevant chunks:")
            
            for i, chunk in enumerate(similar_chunks, 1):
                chunk_id = chunk.get('chunk_id', f'chunk_{i}')
                content = chunk.get('content', 'No content available')
                source_type = chunk.get('source_type', 'unknown')
                
                # Display with relevance indicator
                print(f"\n📄 {chunk_id} (Type: {source_type})")
                print(f"   {content[:150]}{'...' if len(content) > 150 else ''}")
                
                # Show key facts if available
                if 'key_facts' in chunk and chunk['key_facts']:
                    key_facts = chunk['key_facts']
                    if isinstance(key_facts, dict):
                        # Try to extract relevant facts
                        for key, value in key_facts.items():
                            if keyword.lower() in str(value).lower():
                                print(f"   💡 Relevant fact: {key} = {value}")
                                break
        else:
            print("🤖 No semantically similar content found.")
            
            # Fallback to literal search if semantic search returns nothing
            print("🔄 Falling back to literal search...")
            _literal_search(memory, keyword)
    else:
        # Use literal search (original functionality)
        print("📝 Using literal text search...")
        _literal_search(memory, keyword)


def _literal_search(memory, keyword):
    """
    Perform literal text search (original functionality)
    
    Args:
        memory: Dictionary of chunk_id -> summary mappings
        keyword: Keyword to search for literally
    """
    results = []
    for chunk_id, summary in memory.items():
        if keyword.lower() in summary.lower():
            results.append((chunk_id, summary))

    if results:
        print(f"\n� Found {len(results)} literal matches:")
        for chunk_id, text in results:
            print(f"{chunk_id}: {text[:120]}{'...' if len(text) > 120 else ''}")
    else:
        print("🚛 No literal matches found.")


def search_memory_advanced(query, search_type="semantic", max_results=5, include_context=True):
    """
    Advanced search function with multiple search strategies.
    
    Args:
        query: Search query (can be a question or keywords)
        search_type: "semantic", "literal", or "hybrid"
        max_results: Maximum number of results to return
        include_context: Whether to include additional context from related chunks
        
    Returns:
        List of relevant chunks with metadata
    """
    print(f"\n🔍 Advanced search for: '{query}'")
    print(f"🎯 Search strategy: {search_type}")
    
    results = []
    
    if search_type in ["semantic", "hybrid"] and len(chunk_metadata) > 0:
        # Semantic search
        semantic_results = retrieve_similar_summaries(query, k=max_results)
        
        for chunk in semantic_results:
            chunk_info = {
                "chunk_id": chunk.get('chunk_id', 'unknown'),
                "content": chunk.get('content', ''),
                "source_type": chunk.get('source_type', 'unknown'),
                "search_method": "semantic",
                "key_facts": chunk.get('key_facts', {}),
                "relevance": "high"  # Could implement actual scoring
            }
            results.append(chunk_info)
    
    if search_type in ["literal", "hybrid"]:
        # Literal search through chunk metadata
        for chunk in chunk_metadata:
            content = chunk.get('content', '')
            if query.lower() in content.lower():
                chunk_info = {
                    "chunk_id": chunk.get('chunk_id', 'unknown'),
                    "content": content,
                    "source_type": chunk.get('source_type', 'unknown'),
                    "search_method": "literal",
                    "key_facts": chunk.get('key_facts', {}),
                    "relevance": "exact_match"
                }
                # Avoid duplicates in hybrid search
                if not any(r["chunk_id"] == chunk_info["chunk_id"] for r in results):
                    results.append(chunk_info)
    
    # Display results
    if results:
        print(f"\n🎯 Found {len(results)} results:")
        
        for i, result in enumerate(results[:max_results], 1):
            print(f"\n📄 Result {i}: {result['chunk_id']}")
            print(f"   📋 Type: {result['source_type']}")
            print(f"   🔍 Method: {result['search_method']}")
            print(f"   📊 Relevance: {result['relevance']}")
            print(f"   📝 Content: {result['content'][:200]}{'...' if len(result['content']) > 200 else ''}")
            
            # Show relevant key facts
            if result['key_facts']:
                key_facts = result['key_facts']
                if isinstance(key_facts, dict):
                    relevant_facts = []
                    for key, value in key_facts.items():
                        if query.lower() in str(value).lower() or any(word in str(value).lower() for word in query.lower().split()):
                            relevant_facts.append(f"{key}: {value}")
                    
                    if relevant_facts:
                        print(f"   💡 Key facts: {'; '.join(relevant_facts[:2])}")
    else:
        print("🚛 No results found for your query.")
    
    return results


def initialize_memory():
    """
    Initialize empty memory dictionary.
    
    Returns:
        Empty dictionary for storing chunk memories
    """
    return {}
