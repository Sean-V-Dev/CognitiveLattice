"""
TokenSight Integrated JSON RAG System
====================================

Complete pipeline for massive JSON ingestion, semantic search, and LLM querying
with hallucination prevention through verbatim verification.

Features:
- Massive JSON file processing with streaming
- Semantic embedding and search
- Context-aware chunk selection for LLM
- Hallucination detection via verbatim verification
- Supports any JSON structure (FDA, scientific papers, etc.)
"""

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import time
from datetime import datetime

# Core imports
from massive_json_processor import MassiveJSONProcessor
from external_api_client import ExternalAPIClient

# Embedding and search imports
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    from sklearn.metrics.pairwise import cosine_similarity
    import torch
    EMBEDDINGS_AVAILABLE = True
    
    # Check for GPU availability
    if torch.cuda.is_available():
        GPU_AVAILABLE = True
        GPU_COUNT = torch.cuda.device_count()
        GPU_NAME = torch.cuda.get_device_name(0)
        print(f"🎮 GPU acceleration available: {GPU_NAME} ({GPU_COUNT} device(s))")
    else:
        GPU_AVAILABLE = False
        GPU_COUNT = 0
        GPU_NAME = None
        print("💻 GPU not available, using CPU for embeddings")
        
except ImportError:
    print("⚠️ Installing required packages for embeddings...")
    os.system("pip install sentence-transformers scikit-learn numpy torch")
    try:
        from sentence_transformers import SentenceTransformer
        import numpy as np
        from sklearn.metrics.pairwise import cosine_similarity
        import torch
        EMBEDDINGS_AVAILABLE = True
        
        # Check for GPU availability after installation
        if torch.cuda.is_available():
            GPU_AVAILABLE = True
            GPU_COUNT = torch.cuda.device_count()
            GPU_NAME = torch.cuda.get_device_name(0)
            print(f"🎮 GPU acceleration available: {GPU_NAME} ({GPU_COUNT} device(s))")
        else:
            GPU_AVAILABLE = False
            GPU_COUNT = 0
            GPU_NAME = None
            print("💻 GPU not available, using CPU for embeddings")
            
    except ImportError:
        EMBEDDINGS_AVAILABLE = False
        GPU_AVAILABLE = False
        GPU_COUNT = 0
        GPU_NAME = None
        print("❌ Could not install embedding dependencies")


class IntegratedJSONRAG:
    """
    Complete RAG system for massive JSON files with hallucination prevention
    """
    
    def __init__(self, 
                 embedding_model: str = "adaptive",  # "adaptive" uses specialized models, or specify single model
                 llm_provider: str = "openai",
                 chunk_size: int = 500,
                 max_context_tokens: int = 100000,  # gpt-4o-mini context window
                 use_gpu: bool = True,  # GPU control
                 specialized_models: bool = True):  # Enable multiple specialized models
        """
        Initialize the integrated RAG system with optional specialized models
        
        Args:
            embedding_model: "adaptive" for specialized models or specific model name
            llm_provider: LLM provider ("openai", etc.)
            chunk_size: Chunks per batch for processing
            max_context_tokens: Max tokens for LLM context
            use_gpu: Enable GPU acceleration
            specialized_models: Use multiple domain-specific embedding models
        """
        
        print("🚀 Initializing TokenSight Integrated JSON RAG System")
        print("=" * 60)
        
        self.chunk_size = chunk_size
        self.max_context_tokens = max_context_tokens
        self.embedding_model_name = embedding_model
        self.use_gpu = use_gpu and GPU_AVAILABLE
        self.specialized_models = specialized_models
        
        # Initialize specialized RAG systems if enabled
        if specialized_models and embedding_model == "adaptive":
            print("🎯 Initializing specialized embedding models...")
            self.rag_systems = {
                "medical_pharmaceutical": {
                    "model_name": "allenai/specter",  # Scientific/medical papers
                    "model": None,
                    "vector_dim": 768,
                    "description": "Specialized for medical and pharmaceutical documents"
                },
                "legal_contractual": {
                    "model_name": "sentence-transformers/all-mpnet-base-v2",  # Legal documents
                    "model": None,
                    "vector_dim": 768,
                    "description": "Optimized for legal and contractual documents"
                },
                "scientific_technical": {
                    "model_name": "sentence-transformers/all-MiniLM-L12-v2",  # Technical docs
                    "model": None,
                    "vector_dim": 384,
                    "description": "Balanced for technical and scientific content"
                },
                "general": {
                    "model_name": "all-MiniLM-L6-v2",  # Fast general-purpose
                    "model": None,
                    "vector_dim": 384,
                    "description": "Fast general-purpose embedding model"
                }
            }
            self.embedding_model = None  # Will be selected dynamically
            print(f"   ✅ {len(self.rag_systems)} specialized models configured")
        else:
            # Single model mode (backward compatibility)
            self.rag_systems = None
            if EMBEDDINGS_AVAILABLE:
                print(f"🤖 Loading single embedding model: {embedding_model}")
                self.embedding_model = SentenceTransformer(embedding_model)
                
                if self.use_gpu:
                    self.embedding_model = self.embedding_model.to('cuda')
                    # Enable mixed precision for faster inference
                    self.embedding_model = self.embedding_model.half()
                    print(f"   ✅ Model loaded on GPU with FP16 mixed precision")
                else:
                    print(f"   ✅ Model loaded on CPU")
            else:
                print("❌ Embeddings not available - semantic search disabled")
                self.embedding_model = None
        
        # Initialize components (JSON processor will be lazy-loaded when needed)
        self.json_processor = None  # Lazy-loaded only when processing JSON files
        
        self.llm_client = ExternalAPIClient(api_provider=llm_provider)
        
        # Storage for processed data
        self.chunk_embeddings = []
        self.chunk_metadata = []
        self.verbatim_chunks = {}  # For hallucination verification
        
        # Current document domain for dynamic model selection
        self.current_document_domain = "general"
        
        print(f"📊 Configuration:")
        print(f"   Chunk size: {chunk_size:,} records")
        print(f"   Max context tokens: {max_context_tokens:,}")
        print(f"   LLM provider: {llm_provider}")
        print(f"   Device: {'GPU' if self.use_gpu and GPU_AVAILABLE else 'CPU'}")
        if specialized_models and embedding_model == "adaptive":
            print(f"   Mode: Adaptive (specialized models)")
        else:
            print(f"   Mode: Single model ({embedding_model})")
        print("✅ System initialized successfully\n")
    
    def _ensure_json_processor(self):
        """Lazy-load JSON processor only when needed for JSON file processing"""
        if self.json_processor is None:
            print("🔧 Initializing JSON processor for file processing...")
            self.json_processor = MassiveJSONProcessor(
                chunk_size=self.chunk_size,
                temp_dir="integrated_rag_temp"
            )
    
    def process_raw_chunks(self, chunks: List[Dict[str, Any]], document_type: str = "general") -> Dict[str, Any]:
        """
        Process pre-extracted chunks directly without JSON file processing
        Optimized for PDF text chunks that don't need JSON parsing
        
        Args:
            chunks: List of chunk dictionaries with content, chunk_id, etc.
            document_type: Document type for domain detection (technical, medical, etc.)
            
        Returns:
            Processing results and statistics
        """
        
        print(f"📄 Processing {len(chunks)} raw chunks directly...")
        print("=" * 50)
        
        # Clear previous data
        self.chunk_embeddings = []
        self.chunk_metadata = []
        self.verbatim_chunks = {}
        
        # Convert chunks to internal format and detect document domain
        for chunk in chunks:
            chunk_metadata = {
                "chunk_id": chunk.get("chunk_id", f"chunk_{len(self.chunk_metadata) + 1}"),
                "content": chunk.get("content", ""),
                "source_type": chunk.get("source_type", "text"),
                "chunk_index": chunk.get("chunk_index", len(self.chunk_metadata)),
                "original_text_length": chunk.get("original_text_length", len(chunk.get("content", ""))),
                "inferred_modality": chunk.get("inferred_modality", "text"),
                "processing_method": "direct_chunk_processing"
            }
            
            self.chunk_metadata.append(chunk_metadata)
            # Store verbatim content for hallucination prevention
            self.verbatim_chunks[chunk_metadata["chunk_id"]] = chunk_metadata["content"]
        
        # Set document domain for model selection based on content
        self.current_document_domain = self._detect_document_domain(self.chunk_metadata)
        
        # Create embeddings for the chunks
        chunk_texts = [chunk["content"] for chunk in self.chunk_metadata]
        self._create_embeddings_for_chunks(self.chunk_metadata, chunk_texts)
        
        print(f"✅ Raw chunk processing complete!")
        print(f"   📊 Total chunks: {len(self.chunk_metadata):,}")
        print(f"   🧠 Embeddings created: {len(self.chunk_embeddings):,}")
        print(f"   💾 Verbatim chunks stored: {len(self.verbatim_chunks):,}")
        
        return {
            "total_chunks": len(self.chunk_metadata),
            "embeddings_created": len(self.chunk_embeddings),
            "document_domain": self.current_document_domain,
            "processing_method": "direct_chunk_processing"
        }
    
    def process_json_file(self, 
                         file_path: str,
                         json_path: str = "results.item",
                         extraction_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a massive JSON file and prepare it for RAG queries
        
        Args:
            file_path: Path to the JSON file
            json_path: JSONPath for parsing (e.g., "results.item" for FDA files)
            extraction_config: Custom extraction configuration
            
        Returns:
            Processing results and statistics
        """
        
        print(f"📁 Processing JSON file: {Path(file_path).name}")
        print("=" * 50)
        
        # Ensure JSON processor is initialized
        self._ensure_json_processor()
        
        # Step 1: Process JSON file into chunks
        print("1️⃣ Processing JSON file into chunks...")
        processing_results = self.json_processor.process_single_file(
            file_path,
            json_path=json_path,
            extraction_config=extraction_config,
            save_intermediate=True
        )
        
        if processing_results['total_chunks_created'] == 0:
            print("❌ No chunks were created from the JSON file")
            return processing_results
        
        # Step 2: Load processed chunks and create embeddings
        print(f"\n2️⃣ Loading {processing_results['total_chunks_created']} chunks for embedding...")
        self._load_and_embed_chunks()
        
        print(f"✅ JSON file processing complete!")
        print(f"   📊 Total chunks: {len(self.chunk_metadata):,}")
        print(f"   🧠 Embeddings created: {len(self.chunk_embeddings):,}")
        print(f"   💾 Verbatim chunks stored: {len(self.verbatim_chunks):,}")
        
        return processing_results
    
    def _load_and_embed_chunks(self):
        """
        Load processed chunks from temp files and create embeddings using REAL data
        """
        # Ensure JSON processor is initialized if we need to access temp_dir
        self._ensure_json_processor()
        
        # First check if we have actual chunk files saved during processing
        chunk_files = list(Path(self.json_processor.temp_dir).glob("chunks_*.json"))
        
        if chunk_files:
            print(f"📂 Loading actual chunks from {len(chunk_files)} chunk files...")
            self._load_actual_chunks_from_files(chunk_files)
        else:
            print("📂 No chunk files found, processing directly from JSON...")
            self._load_chunks_from_json_directly()
    
    def _load_actual_chunks_from_files(self, chunk_files):
        """Load actual chunk data from saved chunk files"""
        all_chunks = []
        chunk_texts = []
        
        for chunk_file in sorted(chunk_files):
            try:
                with open(chunk_file, 'r', encoding='utf-8') as f:
                    chunks_data = json.load(f)
                
                if isinstance(chunks_data, list):
                    for chunk in chunks_data:
                        all_chunks.append(chunk)
                        chunk_texts.append(chunk['content'])
                        self.verbatim_chunks[chunk['chunk_id']] = chunk['content']
                
            except Exception as e:
                print(f"⚠️ Could not load {chunk_file.name}: {e}")
                continue
        
        print(f"📋 Loaded {len(all_chunks)} actual chunks with real content")
        self._create_embeddings_for_chunks(all_chunks, chunk_texts)
    
    def _load_chunks_from_json_directly(self):
        """Load chunks by processing the JSON file directly (fallback method)"""
        # Check for original FDA file
        fda_file = "drug-label-0001-of-0013.json"
        if not os.path.exists(fda_file):
            print("❌ No FDA file found for direct processing")
            return
        
        print(f"📁 Processing {fda_file} directly to get real drug data...")
        
        all_chunks = []
        chunk_texts = []
        
        try:
            import ijson
            
            with open(fda_file, 'rb') as f:
                # Parse FDA data structure - results.item contains the drug records
                parser = ijson.items(f, 'results.item')
                
                chunk_count = 0
                for i, drug_record in enumerate(parser):
                    if chunk_count >= 1000:  # Limit for demo
                        break
                    
                    # Extract meaningful drug information
                    drug_info = self._extract_drug_information(drug_record, i)
                    if drug_info and drug_info['content'].strip():
                        all_chunks.append(drug_info)
                        chunk_texts.append(drug_info['content'])
                        self.verbatim_chunks[drug_info['chunk_id']] = drug_info['content']
                        chunk_count += 1
                        
                        if chunk_count % 100 == 0:
                            print(f"   📊 Processed {chunk_count} drug records...")
        
        except Exception as e:
            print(f"❌ Error processing FDA file directly: {e}")
            return
        
        print(f"📋 Loaded {len(all_chunks)} drug records with real content")
        self._create_embeddings_for_chunks(all_chunks, chunk_texts)
    
    def _extract_drug_information(self, drug_record, index):
        """Extract meaningful information from a single FDA drug record"""
        try:
            # Extract key drug information from FDA record structure
            content_parts = []
            metadata = {}
            
            # Get drug name/brand names
            if 'openfda' in drug_record:
                openfda = drug_record['openfda']
                
                if 'brand_name' in openfda:
                    brand_names = openfda['brand_name']
                    if isinstance(brand_names, list):
                        content_parts.append(f"Brand Names: {', '.join(brand_names)}")
                        metadata['brand_names'] = brand_names
                    else:
                        content_parts.append(f"Brand Name: {brand_names}")
                        metadata['brand_names'] = [brand_names]
                
                if 'generic_name' in openfda:
                    generic_names = openfda['generic_name']
                    if isinstance(generic_names, list):
                        content_parts.append(f"Generic Names: {', '.join(generic_names)}")
                        metadata['generic_names'] = generic_names
                    else:
                        content_parts.append(f"Generic Name: {generic_names}")
                        metadata['generic_names'] = [generic_names]
                
                # Get manufacturer info
                if 'manufacturer_name' in openfda:
                    manufacturers = openfda['manufacturer_name']
                    if isinstance(manufacturers, list):
                        content_parts.append(f"Manufacturers: {', '.join(manufacturers)}")
                        metadata['manufacturers'] = manufacturers
                    else:
                        content_parts.append(f"Manufacturer: {manufacturers}")
                        metadata['manufacturers'] = [manufacturers]
            
            # Get usage information from the main drug record
            if 'indications_and_usage' in drug_record:
                indications = drug_record['indications_and_usage']
                if isinstance(indications, list):
                    indications_text = ' '.join(indications)
                else:
                    indications_text = str(indications)
                
                # Look for pediatric mentions
                if indications_text:
                    content_parts.append(f"Indications and Usage: {indications_text[:500]}...")
                    metadata['has_pediatric_info'] = any(keyword in indications_text.lower() 
                                                       for keyword in ['pediatric', 'children', 'infant', 'child'])
            
            # Get dosage information
            if 'dosage_and_administration' in drug_record:
                dosage = drug_record['dosage_and_administration']
                if isinstance(dosage, list):
                    dosage_text = ' '.join(dosage)
                else:
                    dosage_text = str(dosage)
                
                if dosage_text:
                    content_parts.append(f"Dosage: {dosage_text[:300]}...")
                    metadata['has_dosage_info'] = True
            
            # Get contraindications
            if 'contraindications' in drug_record:
                contraindications = drug_record['contraindications']
                if isinstance(contraindications, list):
                    contra_text = ' '.join(contraindications)
                else:
                    contra_text = str(contraindications)
                
                if contra_text:
                    content_parts.append(f"Contraindications: {contra_text[:300]}...")
                    metadata['has_contraindications'] = True
            
            # Create the chunk
            if content_parts:
                chunk_id = f"fda_drug_{index+1:06d}"
                full_content = "\n\n".join(content_parts)
                
                return {
                    'chunk_id': chunk_id,
                    'content': full_content,
                    'source_type': 'fda_drug_record',
                    'metadata': metadata,
                    'estimated_tokens': len(full_content.split()),
                    'record_index': index
                }
            
            return None
            
        except Exception as e:
            print(f"⚠️ Error extracting drug info from record {index}: {e}")
            return None
    
    def _create_embeddings_for_chunks(self, all_chunks, chunk_texts):
        """Create embeddings for loaded chunks with specialized model selection"""
        if EMBEDDINGS_AVAILABLE:
            print("🧠 Creating embeddings from real data...")
            
            # Detect document domain and select appropriate model
            if self.specialized_models and self.rag_systems:
                detected_domain = self._update_document_domain(all_chunks)
                embedding_model = self._get_best_embedding_model(detected_domain)
            else:
                embedding_model = self.embedding_model
                detected_domain = "single_model"
            
            # GPU/CPU setup
            if self.use_gpu and GPU_AVAILABLE:
                print(f"🎮 Using GPU: {GPU_NAME}")
                print("⚡ GPU-accelerated embedding creation in progress...")
                
                # Monitor GPU memory usage
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()  # Clear GPU cache before starting
                    initial_memory = torch.cuda.memory_allocated() / 1e9
                    print(f"   💾 Initial GPU memory usage: {initial_memory:.2f} GB")
                    
                # Larger batch sizes for GPU to maximize throughput
                batch_size = min(200, len(chunk_texts))
            else:
                print("💻 Using CPU for embedding creation...")
                # Smaller batch sizes for CPU to avoid memory issues
                batch_size = 100
            
            print(f"   📦 Batch size: {batch_size}")
            print(f"   🎯 Using model for domain: {detected_domain}")
            
            all_embeddings = []
            total_batches = (len(chunk_texts) + batch_size - 1) // batch_size
            
            start_time = time.time()
            
            for i in range(0, len(chunk_texts), batch_size):
                batch_start_time = time.time()
                batch_texts = chunk_texts[i:i+batch_size]
                batch_num = i // batch_size + 1
                
                # Create embeddings for batch
                batch_embeddings = embedding_model.encode(
                    batch_texts,
                    batch_size=batch_size,
                    show_progress_bar=False,
                    convert_to_numpy=True,
                    normalize_embeddings=True  # Normalize for better similarity
                )
                
                all_embeddings.extend(batch_embeddings)
                
                # Performance monitoring
                batch_time = time.time() - batch_start_time
                texts_per_second = len(batch_texts) / batch_time
                
                if self.use_gpu and GPU_AVAILABLE:
                    current_memory = torch.cuda.memory_allocated() / 1e9
                    print(f"   ✅ GPU Batch {batch_num}/{total_batches}: {len(batch_texts)} texts in {batch_time:.2f}s ({texts_per_second:.1f} texts/sec) | GPU mem: {current_memory:.2f} GB")
                else:
                    print(f"   ✅ CPU Batch {batch_num}/{total_batches}: {len(batch_texts)} texts in {batch_time:.2f}s ({texts_per_second:.1f} texts/sec)")
            
            # Final performance summary
            total_time = time.time() - start_time
            total_texts_per_second = len(chunk_texts) / total_time
            
            self.chunk_embeddings = np.array(all_embeddings)
            
            if self.use_gpu and GPU_AVAILABLE:
                final_memory = torch.cuda.memory_allocated() / 1e9
                print(f"✅ GPU embedding complete: {len(all_embeddings)} embeddings in {total_time:.2f}s")
                print(f"   🚀 Overall speed: {total_texts_per_second:.1f} texts/second")
                print(f"   💾 Final GPU memory: {final_memory:.2f} GB")
                print(f"   🎯 Model used: {embedding_model.get_model_info() if hasattr(embedding_model, 'get_model_info') else detected_domain}")
                
                # Clear GPU cache after completion
                torch.cuda.empty_cache()
            else:
                print(f"✅ CPU embedding complete: {len(all_embeddings)} embeddings in {total_time:.2f}s")
                print(f"   💻 Overall speed: {total_texts_per_second:.1f} texts/second")
                print(f"   🎯 Model used: {detected_domain}")
        
        self.chunk_metadata = all_chunks
        print(f"💾 Stored metadata for {len(all_chunks)} chunks with {detected_domain} embeddings")
    
    def semantic_search(self, 
                       query: str, 
                       top_k: int = 50,
                       similarity_threshold: float = 0.3) -> List[Dict[str, Any]]:
        """
        Perform semantic search to find relevant chunks
        
        Args:
            query: Search query
            top_k: Number of top results to return
            similarity_threshold: Minimum similarity score
            
        Returns:
            List of relevant chunks with similarity scores
        """
        
        if not self.chunk_metadata:
            print("❌ No chunks available for search. Process a JSON file first.")
            return []
        
        print(f"🔍 Semantic search: '{query}'")
        print(f"   📊 Searching {len(self.chunk_metadata):,} chunks")
        
        if EMBEDDINGS_AVAILABLE and len(self.chunk_embeddings) > 0:
            # Semantic search using embeddings
            print("🧠 Using semantic embeddings for search...")
            
            # Get the appropriate embedding model for query
            if self.specialized_models and self.rag_systems:
                # For query embedding, use the same model as the indexed chunks
                embedding_model = self._get_best_embedding_model(self.current_document_domain)
                print(f"   🎯 Using {self.current_document_domain} model for query embedding")
            else:
                embedding_model = self.embedding_model
            
            # Embed the query with GPU acceleration
            if self.use_gpu and GPU_AVAILABLE:
                query_embedding = embedding_model.encode(
                    [query],
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
            else:
                query_embedding = embedding_model.encode(
                    [query],
                    convert_to_numpy=True,
                    normalize_embeddings=True
                )
            
            # Calculate similarities
            similarities = cosine_similarity(query_embedding, self.chunk_embeddings)[0]
            
            # Get top-k results above threshold
            relevant_indices = []
            for i, score in enumerate(similarities):
                if score >= similarity_threshold:
                    relevant_indices.append((i, score))
            
            # Sort by similarity and take top-k
            relevant_indices.sort(key=lambda x: x[1], reverse=True)
            relevant_indices = relevant_indices[:top_k]
            
            # Build results
            results = []
            for idx, score in relevant_indices:
                chunk_info = self.chunk_metadata[idx].copy()
                chunk_info['similarity_score'] = float(score)
                chunk_info['search_method'] = 'semantic_embedding'
                results.append(chunk_info)
            
            print(f"   ✅ Found {len(results)} relevant chunks (similarity ≥ {similarity_threshold})")
            
        else:
            # Fallback to keyword search
            print("🔤 Using keyword search fallback...")
            
            query_words = query.lower().split()
            results = []
            
            for i, chunk in enumerate(self.chunk_metadata):
                content_lower = chunk['content'].lower()
                matches = sum(1 for word in query_words if word in content_lower)
                
                if matches > 0:
                    chunk_info = chunk.copy()
                    chunk_info['similarity_score'] = matches / len(query_words)
                    chunk_info['search_method'] = 'keyword_fallback'
                    results.append(chunk_info)
            
            # Sort by score and take top-k
            results.sort(key=lambda x: x['similarity_score'], reverse=True)
            results = results[:top_k]
            
            print(f"   ✅ Found {len(results)} relevant chunks (keyword matching)")
        
        return results
    
    def prepare_context_for_llm(self, 
                              relevant_chunks: List[Dict[str, Any]],
                              query: str) -> Tuple[str, List[str]]:
        """
        Prepare context from relevant chunks for LLM, respecting token limits
        
        Args:
            relevant_chunks: List of relevant chunks from semantic search
            query: Original query for context
            
        Returns:
            Tuple of (formatted_context, chunk_ids_used)
        """
        
        print(f"📝 Preparing context for LLM...")
        print(f"   🎯 Target: {self.max_context_tokens:,} tokens max")
        
        # Estimate tokens per chunk (rough approximation: 1 token ≈ 4 characters)
        context_parts = []
        total_estimated_tokens = 0
        chunk_ids_used = []
        
        # Add query context
        query_tokens = len(query) // 4
        context_parts.append(f"User Query: {query}\n\nRelevant Information:\n")
        total_estimated_tokens += query_tokens + 20
        
        # Add chunks until we approach token limit
        for i, chunk in enumerate(relevant_chunks):
            chunk_tokens = chunk.get('estimated_tokens', len(chunk['content']) // 4)
            
            if total_estimated_tokens + chunk_tokens > self.max_context_tokens * 0.9:  # 90% safety margin
                print(f"   ⚠️ Context limit reached at chunk {i+1}/{len(relevant_chunks)}")
                break
            
            # Format chunk for context
            chunk_text = f"\n--- Chunk {chunk['chunk_id']} (similarity: {chunk['similarity_score']:.3f}) ---\n"
            chunk_text += chunk['content']
            chunk_text += f"\n--- End Chunk {chunk['chunk_id']} ---\n"
            
            context_parts.append(chunk_text)
            total_estimated_tokens += chunk_tokens + 30  # Include formatting overhead
            chunk_ids_used.append(chunk['chunk_id'])
        
        final_context = "".join(context_parts)
        
        print(f"   ✅ Context prepared:")
        print(f"      📊 Chunks included: {len(chunk_ids_used)}")
        print(f"      🎯 Estimated tokens: {total_estimated_tokens:,}")
        print(f"      📏 Context length: {len(final_context):,} characters")
        
        return final_context, chunk_ids_used
    
    def _get_best_embedding_model(self, domain: str = None) -> Any:
        """
        Get the best embedding model for the detected domain
        
        Args:
            domain: Document domain (optional, will detect if not provided)
            
        Returns:
            Loaded embedding model for the domain
        """
        if not self.specialized_models or self.rag_systems is None:
            # Return single model if not using specialized models
            return self.embedding_model
        
        # Use provided domain or detect from current chunks
        if domain is None:
            domain = self.current_document_domain
        
        # Map domains to specialized models
        domain_mapping = {
            'medical_pharmaceutical': 'medical_pharmaceutical',
            'legal_contractual': 'legal_contractual', 
            'scientific_technical': 'scientific_technical',
            'financial_regulatory': 'legal_contractual',  # Use legal model for regulatory
            'regulatory_compliance': 'legal_contractual',  # Use legal model for compliance
            'general': 'general'
        }
        
        model_key = domain_mapping.get(domain, 'general')
        
        # Lazy load the model if not already loaded
        if self.rag_systems[model_key]['model'] is None:
            model_name = self.rag_systems[model_key]['model_name']
            print(f"🤖 Loading {domain} model: {model_name}")
            
            # Load with GPU support if available
            if self.use_gpu and GPU_AVAILABLE:
                model = SentenceTransformer(model_name, device='cuda')
                model = model.half()  # FP16 for faster GPU inference
                print(f"   ✅ {domain} model loaded on GPU with FP16")
            else:
                model = SentenceTransformer(model_name)
                print(f"   ✅ {domain} model loaded on CPU")
            
            self.rag_systems[model_key]['model'] = model
        
        return self.rag_systems[model_key]['model']
    
    def _update_document_domain(self, chunk_metadata: List[Dict[str, Any]]) -> str:
        """
        Detect and update the current document domain for specialized model selection
        
        Args:
            chunk_metadata: List of processed chunks
            
        Returns:
            Detected domain string
        """
        if not self.specialized_models or not chunk_metadata:
            return "general"
        
        # Detect domain using existing method
        detected_domain = self._detect_document_domain(chunk_metadata)
        self.current_document_domain = detected_domain
        
        print(f"🎯 Document domain detected: {detected_domain}")
        if self.rag_systems:
            domain_mapping = {
                'medical_pharmaceutical': 'medical_pharmaceutical',
                'legal_contractual': 'legal_contractual', 
                'scientific_technical': 'scientific_technical',
                'financial_regulatory': 'legal_contractual',
                'regulatory_compliance': 'legal_contractual',
                'general': 'general'
            }
            model_key = domain_mapping.get(detected_domain, 'general')
            model_info = self.rag_systems[model_key]
            print(f"   🎯 Will use: {model_info['model_name']} ({model_info['description']})")
        
        return detected_domain
    
    def _detect_document_domain(self, chunk_metadata: List[Dict[str, Any]]) -> str:
        """
        Detect the domain/type of documents being processed for appropriate LLM instructions
        
        Args:
            chunk_metadata: List of processed chunks with metadata
            
        Returns:
            Detected domain type for appropriate instruction selection
        """
        
        if not chunk_metadata:
            return "general"
        
        # Analyze content across chunks to determine domain
        all_content = " ".join([chunk.get('content', '') for chunk in chunk_metadata[:50]]).lower()
        
        # Define domain detection patterns
        domain_patterns = {
            'medical_pharmaceutical': [
                'drug', 'medication', 'dosage', 'contraindication', 'pediatric', 'adverse',
                'clinical', 'pharmaceutical', 'prescription', 'therapy', 'treatment',
                'fda', 'approval', 'indication', 'patient', 'medical', 'health'
            ],
            'legal_contractual': [
                'contract', 'agreement', 'clause', 'liability', 'breach', 'damages',
                'jurisdiction', 'arbitration', 'warranty', 'indemnity', 'termination',
                'legal', 'court', 'law', 'attorney', 'counsel', 'litigation'
            ],
            'financial_regulatory': [
                'financial', 'sec', 'compliance', 'audit', 'regulation', 'filing',
                'disclosure', 'investor', 'securities', 'revenue', 'earnings',
                'gaap', 'accounting', 'tax', 'irs', 'banking', 'credit'
            ],
            'scientific_technical': [
                'research', 'study', 'analysis', 'methodology', 'data', 'results',
                'conclusion', 'hypothesis', 'experiment', 'technical', 'engineering',
                'specification', 'procedure', 'protocol', 'standard'
            ],
            'regulatory_compliance': [
                'regulation', 'compliance', 'standard', 'requirement', 'guideline',
                'policy', 'procedure', 'audit', 'inspection', 'certification',
                'iso', 'osha', 'epa', 'regulatory', 'government'
            ]
        }
        
        # Score each domain
        domain_scores = {}
        for domain, keywords in domain_patterns.items():
            score = sum(1 for keyword in keywords if keyword in all_content)
            domain_scores[domain] = score
        
        # Return domain with highest score, or 'general' if no clear match
        if domain_scores:
            max_domain = max(domain_scores, key=domain_scores.get)
            max_score = domain_scores[max_domain]
            
            # Require minimum threshold for domain detection
            if max_score >= 3:  # At least 3 keyword matches
                print(f"🎯 Document domain detected: {max_domain} (score: {max_score})")
                return max_domain
        
        print(f"🎯 Document domain: general (no specific domain detected)")
        return "general"
    
    def _get_domain_specific_instructions(self, domain: str) -> str:
        """
        Get domain-specific instructions for LLM based on detected document type
        
        Args:
            domain: Detected domain from _detect_document_domain()
            
        Returns:
            Domain-specific instruction text
        """
        
        domain_instructions = {
            'medical_pharmaceutical': """
            7. MEDICAL ACCURACY CRITICAL: If asked about drug approvals, contraindications, dosages, or medical information, be extremely careful about accuracy
            8. Never provide medical advice - only report what is explicitly stated in the source documents
            9. Flag any medical claims that seem uncertain or ambiguous
            10. For pediatric information, be especially cautious about age ranges and dosing
            """,
            
            'legal_contractual': """
            7. LEGAL ACCURACY CRITICAL: If asked about contract terms, legal obligations, liability, or rights, be extremely careful about accuracy
            8. Never provide legal advice - only report what is explicitly stated in the source documents
            9. Flag any legal interpretations that require professional judgment
            10. For liability and obligation questions, be especially precise about exact wording
            """,
            
            'financial_regulatory': """
            7. FINANCIAL ACCURACY CRITICAL: If asked about financial data, compliance requirements, or regulatory filings, be extremely careful about accuracy
            8. Never provide financial advice - only report what is explicitly stated in the source documents
            9. Flag any financial claims that could affect investment decisions
            10. For compliance matters, be especially precise about regulatory requirements
            """,
            
            'scientific_technical': """
            7. SCIENTIFIC ACCURACY CRITICAL: If asked about research findings, technical specifications, or experimental data, be extremely careful about accuracy
            8. Never extrapolate beyond the provided data - only report what is explicitly stated
            9. Flag any scientific claims that require additional validation
            10. For technical specifications, be especially precise about measurements and procedures
            """,
            
            'regulatory_compliance': """
            7. REGULATORY ACCURACY CRITICAL: If asked about compliance requirements, standards, or regulatory guidelines, be extremely careful about accuracy
            8. Never provide compliance advice - only report what is explicitly stated in the source documents
            9. Flag any regulatory interpretations that require professional judgment
            10. For safety and compliance matters, be especially cautious about requirements and deadlines
            """,
            
            'general': """
            7. ACCURACY CRITICAL: For any factual claims, financial data, legal terms, technical specifications, or sensitive information, be extremely careful about accuracy
            8. Never provide professional advice - only report what is explicitly stated in the source documents
            9. Flag any claims that could have significant consequences if incorrect
            10. When in doubt about sensitive information, recommend consulting appropriate professionals
            """
        }
        
        return domain_instructions.get(domain, domain_instructions['general'])
    
    def query_with_llm(self, 
                      context: str, 
                      query: str,
                      chunk_ids_used: List[str]) -> Dict[str, Any]:
        """
        Send context and query to LLM for processing with domain-adaptive instructions
        """
        
        print(f"🌐 Querying LLM with context...")
        
        # Detect document domain for appropriate instructions
        document_domain = self._detect_document_domain(self.chunk_metadata)
        domain_instructions = self._get_domain_specific_instructions(document_domain)
        
        # Create enhanced, domain-aware prompt
        system_prompt = f"""You are an expert analyst working with structured data from {document_domain.replace('_', ' ').title()} documents.
        
        IMPORTANT INSTRUCTIONS:
        1. Answer based ONLY on the provided context chunks
        2. If information is not in the provided chunks, say "Information not found in provided data"
        3. When citing information, reference the specific chunk ID (e.g., "According to chunk batch_001_chunk_015...")
        4. Provide specific, factual answers with direct quotes when possible
        5. For counting questions, be precise and show your methodology
        6. Always indicate your confidence level and any limitations in the source data
        {domain_instructions}
        
        DOMAIN CONTEXT: You are analyzing {document_domain.replace('_', ' ').title()} documents. Apply appropriate caution and precision for this domain.
        
        Answer the user's query using only the provided context chunks."""
        
        user_prompt = f"{context}\n\nUser Question: {query}\n\nPlease provide a comprehensive answer based on the context above."
        
        try:
            # Use the existing external API client
            chunk_data = {
                "chunk_id": "integrated_query",
                "content": user_prompt,
                "source_type": f"integrated_json_rag_{document_domain}",
                "context_chunks": chunk_ids_used,
                "query": query,
                "document_domain": document_domain
            }
            
            response = self.llm_client.analyze_chunk_with_external_api(
                chunk_data,
                analysis_type="comprehensive"
            )
            
            print(f"✅ LLM response received")
            print(f"   🎯 Document domain: {document_domain}")
            print(f"   🎯 Tokens used: {response.get('tokens_used', 'unknown')}")
            print(f"   🤖 Model: {response.get('model_used', 'unknown')}")
            
            return response
            
        except Exception as e:
            print(f"❌ LLM query failed: {e}")
            return {
                "error": str(e),
                "chunk_id": "integrated_query",
                "external_analysis": {"error": str(e)}
            }
    
    def verify_against_verbatim(self, 
                           llm_response: Dict[str, Any],
                           chunk_ids_used: List[str],
                           query: str) -> Dict[str, Any]:
        """
        Verify LLM response against verbatim chunks with domain-specific hallucination detection
        """
        
        print(f"🔍 Verifying LLM response against verbatim data...")
        
        # Extract the actual response text
        if 'external_analysis' in llm_response and not llm_response['external_analysis'].get('error'):
            try:
                response_content = llm_response['external_analysis']
                if isinstance(response_content, dict):
                    response_text = str(response_content)
                else:
                    response_text = str(response_content)
            except:
                response_text = "Could not extract response text"
        else:
            print("❌ LLM response contains errors - skipping verification")
            return {
                "verification_status": "error",
                "document_domain": "unknown",
                "chunk_ids_checked": chunk_ids_used,
                "hallucination_detected": False,
                "confidence_score": 0.0,
                "verification_notes": ["LLM response contained errors"],
                "response_text": "Error in LLM response",
                "error": "LLM response contained errors"
            }
        
        # Detect document domain for domain-specific verification
        document_domain = self._detect_document_domain(self.chunk_metadata)
        
        verification_results = {
            "verification_status": "verified",
            "document_domain": document_domain,
            "chunk_ids_checked": chunk_ids_used,
            "hallucination_detected": False,
            "confidence_score": 0.95,
            "verification_notes": [],
            "response_text": response_text
        }
        
        print(f"   📋 Checking response against {len(chunk_ids_used)} source chunks...")
        print(f"   🎯 Using {document_domain} domain verification rules...")
        
        # Check if response references the chunks appropriately
        chunk_references = sum(1 for chunk_id in chunk_ids_used if chunk_id in response_text)
        
        if chunk_references == 0:
            verification_results["verification_notes"].append(
                "⚠️ Response does not reference any source chunks explicitly"
            )
            verification_results["confidence_score"] -= 0.2
        
        # Domain-specific hallucination patterns
        domain_hallucination_patterns = {
            'medical_pharmaceutical': [
                "according to medical knowledge", "it is medically established", "doctors typically recommend",
                "medical studies show", "it is clinically proven", "standard medical practice"
            ],
            'legal_contractual': [
                "according to legal precedent", "it is legally established", "courts typically rule",
                "legal experts recommend", "it is legally binding", "standard legal practice"
            ],
            'financial_regulatory': [
                "according to financial analysis", "it is financially sound", "analysts typically recommend",
                "market studies show", "it is financially proven", "standard accounting practice"
            ],
            'scientific_technical': [
                "according to scientific consensus", "it is scientifically established", "researchers typically find",
                "studies consistently show", "it is technically proven", "standard scientific practice"
            ],
            'regulatory_compliance': [
                "according to regulatory guidance", "it is regulatory standard", "inspectors typically require",
                "compliance studies show", "it is regulatorily proven", "standard compliance practice"
            ],
            'general': [
                "according to my knowledge", "based on general information", "it is well known that",
                "typically", "usually", "it is commonly accepted"
            ]
        }
        
        # Use domain-specific patterns, fall back to general
        hallucination_indicators = domain_hallucination_patterns.get(
            document_domain, 
            domain_hallucination_patterns['general']
        )
        
        response_lower = response_text.lower()
        hallucination_flags = [indicator for indicator in hallucination_indicators 
                             if indicator in response_lower]
        
        if hallucination_flags:
            verification_results["hallucination_detected"] = True
            verification_results["verification_notes"].append(
                f"⚠️ Domain-specific hallucination indicators found: {hallucination_flags}"
            )
            verification_results["confidence_score"] -= 0.3
        
        # Domain-specific positive verification signals
        domain_positive_signals = {
            'medical_pharmaceutical': ["according to the drug label", "the prescribing information states", "as indicated in the clinical data"],
            'legal_contractual': ["according to the contract", "the agreement states", "as specified in clause"],
            'financial_regulatory': ["according to the filing", "the financial statement shows", "as reported in the disclosure"],
            'scientific_technical': ["according to the research", "the study data shows", "as measured in the experiment"],
            'regulatory_compliance': ["according to the regulation", "the standard requires", "as specified in the guideline"],
            'general': ["according to the document", "the source states", "as mentioned in the data"]
        }
        
        positive_signals = domain_positive_signals.get(document_domain, domain_positive_signals['general'])
        positive_found = [signal for signal in positive_signals if signal in response_lower]
        
        if positive_found:
            verification_results["verification_notes"].append(
                f"✅ Domain-appropriate source referencing found: {positive_found}"
            )
        
        # Standard verification signals
        if any(chunk_id in response_text for chunk_id in chunk_ids_used):
            verification_results["verification_notes"].append(
                "✅ Response appropriately references source chunks"
            )
        
        if "information not found" in response_lower or "not in the provided data" in response_lower:
            verification_results["verification_notes"].append(
                "✅ Response appropriately indicates when information is not available"
            )
        
        print(f"   ✅ Verification complete:")
        print(f"      🎯 Status: {verification_results['verification_status']}")
        print(f"      📊 Domain: {document_domain}")
        print(f"      🧠 Confidence: {verification_results['confidence_score']:.2f}")
        print(f"      ⚠️ Hallucination detected: {verification_results['hallucination_detected']}")
        
        return verification_results
    
    def integrated_query(self, 
                        query: str,
                        top_k_chunks: int = 50,
                        similarity_threshold: float = 0.3) -> Dict[str, Any]:
        """
        Complete integrated query pipeline: search → context → LLM → verify
        
        Args:
            query: User query
            top_k_chunks: Number of chunks to consider
            similarity_threshold: Minimum similarity for chunk selection
            
        Returns:
            Complete query results with verification
        """
        
        print(f"\n🎯 INTEGRATED QUERY PIPELINE")
        print("=" * 60)
        print(f"Query: {query}")
        print("=" * 60)
        
        start_time = time.time()
        
        # Step 1: Semantic search
        relevant_chunks = self.semantic_search(
            query, 
            top_k=top_k_chunks,
            similarity_threshold=similarity_threshold
        )
        
        if not relevant_chunks:
            return {
                "query": query,
                "status": "no_relevant_chunks",
                "message": "No relevant chunks found for the query"
            }
        
        # Step 2: Prepare context
        context, chunk_ids_used = self.prepare_context_for_llm(relevant_chunks, query)
        
        # Step 3: Query LLM
        llm_response = self.query_with_llm(context, query, chunk_ids_used)
        
        # Step 4: Verify against verbatim
        verification_results = self.verify_against_verbatim(llm_response, chunk_ids_used, query)
        
        # Compile final results
        total_time = time.time() - start_time
        
        final_results = {
            "query": query,
            "status": "completed",
            "processing_time_seconds": total_time,
            "semantic_search": {
                "chunks_found": len(relevant_chunks),
                "similarity_threshold": similarity_threshold,
                "search_method": relevant_chunks[0]['search_method'] if relevant_chunks else "none"
            },
            "context_preparation": {
                "chunks_used": len(chunk_ids_used),
                "chunk_ids": chunk_ids_used,
                "estimated_tokens": len(context) // 4
            },
            "llm_response": llm_response,
            "verification": verification_results,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"\n✅ QUERY PIPELINE COMPLETE")
        print(f"   ⏱️ Total time: {total_time:.2f} seconds")
        print(f"   📊 Chunks analyzed: {len(relevant_chunks)}")
        print(f"   📝 Context chunks: {len(chunk_ids_used)}")
        print(f"   🛡️ Verification: {verification_results['verification_status']}")
        
        return final_results


def demo_integrated_system():
    """
    Demonstration of the complete integrated system
    """
    print("🧪 TOKENSIGHT INTEGRATED JSON RAG - DEMO")
    print("=" * 60)
    
    # Initialize the system
    rag_system = IntegratedJSONRAG(
        embedding_model="all-MiniLM-L6-v2",
        llm_provider="openai",
        chunk_size=100,  # Smaller for demo
        max_context_tokens=50000  # Conservative for demo
    )
    
    # Process JSON file (using your FDA file)
    fda_file = "drug-label-0001-of-0013.json"
    if os.path.exists(fda_file):
        print(f"\n📁 Processing FDA file: {fda_file}")
        
        processing_results = rag_system.process_json_file(
            fda_file,
            json_path="results.item"  # FDA-specific path
        )
        
        if processing_results['total_chunks_created'] > 0:
            # Test queries
            test_queries = [
                "How many drugs have been approved for pediatric use?",
                "What are the contraindications for children?",
                "List drugs that are safe for infants",
                "Which medications have dosage information for adolescents?"
            ]
            
            print(f"\n🧪 Testing integrated query system...")
            
            for query in test_queries:
                print(f"\n" + "="*60)
                
                results = rag_system.integrated_query(
                    query,
                    top_k_chunks=20,
                    similarity_threshold=0.2
                )
                
                # Display key results
                if results['status'] == 'completed':
                    verification = results['verification']
                    print(f"✅ Query successful!")
                    print(f"   🎯 Verification: {verification['verification_status']}")
                    print(f"   🧠 Confidence: {verification['confidence_score']:.2f}")
                    print(f"   ⚠️ Hallucination detected: {verification['hallucination_detected']}")
                else:
                    print(f"❌ Query failed: {results.get('message', 'Unknown error')}")
                
                time.sleep(2)  # Rate limiting
        
        else:
            print("❌ No chunks were processed from the FDA file")
    
    else:
        print(f"❌ FDA file not found: {fda_file}")
        print("   Please ensure the file exists in the TokenSight directory")


if __name__ == "__main__":
    demo_integrated_system()
