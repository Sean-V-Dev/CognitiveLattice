"""
Bidirectional RAG System for CognitiveLattice
Multi-specialized embedding models with intelligent routing and audit capabilities
Designed for high-stakes technical documents requiring precision and auditability
"""

import os
import json
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional, Tuple
import torch

class SpecializedRAG:
    """
    Individual RAG system with specialized embedding model
    """
    
    def __init__(self, model_name: str, domain: str, vector_dim: int = None):
        self.model_name = model_name
        self.domain = domain
        self.model = None  # Lazy loading
        self.vector_dim = vector_dim
        self.index = None
        self.chunk_metadata = []
        self.embeddings_cache = {}
        
    def _initialize_model(self):
        """Lazy load the embedding model"""
        if self.model is None:
            print(f"🤖 Loading {self.domain} model: {self.model_name}")
            self.model = SentenceTransformer(self.model_name)
            
            # Use GPU if available
            if torch.cuda.is_available():
                self.model = self.model.to('cuda')
                print(f"   ✅ {self.domain} model loaded on GPU")
            else:
                print(f"   ✅ {self.domain} model loaded on CPU")
                
            # Initialize vector dimensions
            if self.vector_dim is None:
                # Get dimensions from model
                test_embedding = self.model.encode(["test"])
                self.vector_dim = test_embedding.shape[1]
                
            # Initialize FAISS index
            self.index = faiss.IndexFlatL2(self.vector_dim)
            
    def embed_text(self, text: str) -> np.ndarray:
        """Embed a single text"""
        self._initialize_model()
        return self.model.encode(text, convert_to_tensor=False)
    
    def embed_batch(self, texts: List[str], batch_size: int = 32) -> List[np.ndarray]:
        """Embed multiple texts efficiently"""
        self._initialize_model()
        embeddings = []
        
        for i in range(0, len(texts), batch_size):
            batch = texts[i:i+batch_size]
            batch_embeddings = self.model.encode(
                batch,
                convert_to_tensor=False,
                batch_size=batch_size,
                show_progress_bar=len(texts) > 100
            )
            embeddings.extend(batch_embeddings)
            
        return embeddings
    
    def add_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """Add chunks to this specialized RAG index"""
        self._initialize_model()
        
        # Extract text content for embedding
        texts = [chunk.get('content', '') for chunk in chunks]
        
        # Generate embeddings
        embeddings = self.embed_batch(texts)
        
        # Add to FAISS index
        embeddings_array = np.array(embeddings).astype('float32')
        self.index.add(embeddings_array)
        
        # Store metadata with embeddings
        for i, chunk in enumerate(chunks):
            chunk_with_embedding = chunk.copy()
            chunk_with_embedding['embedding'] = embeddings[i]
            chunk_with_embedding['rag_domain'] = self.domain
            self.chunk_metadata.append(chunk_with_embedding)
            
        print(f"📚 Added {len(chunks)} chunks to {self.domain} RAG")
    
    def find_similar_chunks(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """Find most similar chunks for a query"""
        if not self.chunk_metadata:
            return []
            
        self._initialize_model()
        
        # Embed query
        query_embedding = self.embed_text(query)
        
        # Search FAISS index
        distances, indices = self.index.search(
            np.array([query_embedding]).astype('float32'), 
            min(k, len(self.chunk_metadata))
        )
        
        # Return chunks with similarity scores
        results = []
        for i, idx in enumerate(indices[0]):
            if idx < len(self.chunk_metadata):
                chunk = self.chunk_metadata[idx].copy()
                chunk['similarity_score'] = float(1.0 / (1.0 + distances[0][i]))  # Convert distance to similarity
                chunk['search_rank'] = i + 1
                results.append(chunk)
                
        return results


class DocumentTypeDetector:
    """
    Detects document type and routes to appropriate RAG system
    """
    
    def __init__(self):
        self.type_keywords = {
            "scientific": [
                "clinical trial", "pharmacokinetics", "pharmacodynamics", "bioavailability",
                "mechanism of action", "molecular structure", "compound", "dose-response",
                "efficacy", "safety profile", "adverse events", "contraindications",
                "drug interaction", "metabolism", "elimination", "half-life"
            ],
            "regulatory": [
                "compliance", "regulation", "guidance", "submission", "approval",
                "labeling", "indication", "prescribing information", "risk evaluation",
                "post-market", "surveillance", "quality control", "validation",
                "standard operating procedure", "good manufacturing practice"
            ],
            "technical": [
                "specification", "procedure", "installation", "maintenance", "operation",
                "troubleshooting", "calibration", "performance", "testing", "measurement",
                "equipment", "system", "configuration", "parameter", "protocol"
            ]
        }
    
    def detect_document_type(self, text: str, chunk_metadata: List[Dict] = None) -> str:
        """
        Detect the primary document type based on content analysis
        """
        text_lower = text.lower()
        
        # Score each document type
        scores = {}
        for doc_type, keywords in self.type_keywords.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            # Weight by keyword frequency
            for keyword in keywords:
                score += text_lower.count(keyword) * 0.5
            scores[doc_type] = score
        
        # Check chunk metadata for additional context
        if chunk_metadata:
            for chunk in chunk_metadata[:5]:  # Check first few chunks
                source_type = chunk.get('source_type', '').lower()
                if 'scientific' in source_type or 'research' in source_type:
                    scores['scientific'] = scores.get('scientific', 0) + 2
                elif 'regulatory' in source_type or 'compliance' in source_type:
                    scores['regulatory'] = scores.get('regulatory', 0) + 2
                elif 'technical' in source_type or 'manual' in source_type:
                    scores['technical'] = scores.get('technical', 0) + 2
        
        # Return highest scoring type, default to technical
        if not scores or max(scores.values()) == 0:
            return "technical"
        
        return max(scores, key=scores.get)


class SafetyAuditor:
    """
    Audits responses for potential safety issues and hallucinations
    """
    
    def __init__(self):
        self.high_risk_keywords = [
            "dosage", "dose", "mg", "ml", "units", "administration", "contraindicated",
            "adverse", "toxicity", "overdose", "interaction", "side effect", "warning",
            "pregnancy", "pediatric", "geriatric", "renal", "hepatic", "cardiac"
        ]
        
        self.verification_required_phrases = [
            "recommended dose", "maximum dose", "contraindicated in", "not recommended",
            "should not be used", "avoid in patients", "caution in", "monitor for"
        ]
    
    def audit_response(self, response: str, source_chunks: List[Dict[str, Any]], 
                      similarity_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Audit a response against source chunks for safety and accuracy
        """
        response_lower = response.lower()
        
        # Check for high-risk content
        high_risk_score = sum(1 for keyword in self.high_risk_keywords 
                             if keyword in response_lower)
        
        # Check for verification-required phrases
        verification_needed = any(phrase in response_lower 
                                for phrase in self.verification_required_phrases)
        
        # Calculate content similarity to source chunks
        source_content = " ".join([chunk.get('content', '') for chunk in source_chunks])
        
        # Simple overlap-based similarity (could be enhanced with embeddings)
        response_words = set(response_lower.split())
        source_words = set(source_content.lower().split())
        
        if response_words:
            content_overlap = len(response_words.intersection(source_words)) / len(response_words)
        else:
            content_overlap = 0.0
        
        # Determine risk level
        risk_level = "low"
        if high_risk_score > 3 or verification_needed:
            risk_level = "high" if content_overlap < similarity_threshold else "medium"
        elif high_risk_score > 1:
            risk_level = "medium" if content_overlap < similarity_threshold else "low"
        
        return {
            "risk_level": risk_level,
            "high_risk_keywords_found": high_risk_score,
            "verification_required": verification_needed,
            "content_similarity": content_overlap,
            "audit_passed": risk_level == "low" and content_overlap >= similarity_threshold,
            "source_chunks_count": len(source_chunks),
            "recommendations": self._generate_recommendations(risk_level, content_overlap)
        }
    
    def _generate_recommendations(self, risk_level: str, similarity: float) -> List[str]:
        """Generate audit recommendations"""
        recommendations = []
        
        if risk_level == "high":
            recommendations.append("CRITICAL: Response contains high-risk medical information")
            recommendations.append("Require expert review before use")
        elif risk_level == "medium":
            recommendations.append("CAUTION: Response may require additional verification")
        
        if similarity < 0.5:
            recommendations.append("WARNING: Low similarity to source material detected")
            recommendations.append("Potential hallucination risk - verify independently")
        elif similarity < 0.7:
            recommendations.append("Moderate similarity to source - consider additional context")
        
        return recommendations


class BidirectionalRAGSystem:
    """
    Main system managing multiple specialized RAG models with routing and audit
    """
    
    def __init__(self):
        # Initialize specialized RAG systems
        self.rag_systems = {
            "scientific": SpecializedRAG("allenai/specter", "scientific", 768),
            "regulatory": SpecializedRAG("sentence-transformers/all-mpnet-base-v2", "regulatory", 768),
            "technical": SpecializedRAG("sentence-transformers/all-MiniLM-L12-v2", "technical", 384)
        }
        
        # Initialize routing and audit systems
        self.document_detector = DocumentTypeDetector()
        self.safety_auditor = SafetyAuditor()
        
        # Track all processed chunks for audit
        self.all_chunks = []
        
    def add_document_chunks(self, chunks: List[Dict[str, Any]]) -> None:
        """
        Process and route document chunks to appropriate RAG systems
        """
        if not chunks:
            return
            
        print(f"🔄 Processing {len(chunks)} chunks for multi-RAG indexing...")
        
        # Detect primary document type
        sample_text = " ".join([chunk.get('content', '')[:500] for chunk in chunks[:3]])
        primary_doc_type = self.document_detector.detect_document_type(sample_text, chunks)
        
        print(f"📋 Detected primary document type: {primary_doc_type}")
        
        # Store all chunks for audit purposes
        self.all_chunks.extend(chunks)
        
        # Add to primary RAG system
        if primary_doc_type in self.rag_systems:
            self.rag_systems[primary_doc_type].add_chunks(chunks)
        
        # For high-stakes documents, also add to general technical RAG as backup
        if primary_doc_type != "technical":
            self.rag_systems["technical"].add_chunks(chunks)
            print(f"🔄 Also indexed in technical RAG as backup")
    
    def query_with_routing(self, query: str, max_chunks: int = 5, 
                          preferred_domain: str = None) -> Dict[str, Any]:
        """
        Query the system with automatic routing to best RAG
        """
        print(f"🔍 Processing query: {query[:100]}...")
        
        # Determine which RAG system to use
        if preferred_domain and preferred_domain in self.rag_systems:
            primary_rag = preferred_domain
        else:
            # Detect query type based on content
            query_type = self.document_detector.detect_document_type(query)
            primary_rag = query_type if query_type in self.rag_systems else "technical"
        
        print(f"🎯 Routing to {primary_rag} RAG system")
        
        # Get results from primary RAG
        primary_results = self.rag_systems[primary_rag].find_similar_chunks(query, max_chunks)
        
        # If primary results are insufficient, try backup systems
        backup_results = []
        if len(primary_results) < max_chunks:
            remaining_slots = max_chunks - len(primary_results)
            
            for rag_name, rag_system in self.rag_systems.items():
                if rag_name != primary_rag and remaining_slots > 0:
                    backup_chunks = rag_system.find_similar_chunks(query, remaining_slots)
                    # Filter out duplicates
                    for chunk in backup_chunks:
                        if not any(c.get('chunk_id') == chunk.get('chunk_id') for c in primary_results):
                            backup_results.append(chunk)
                            remaining_slots -= 1
                            if remaining_slots <= 0:
                                break
        
        # Combine and rank results
        all_results = primary_results + backup_results
        all_results.sort(key=lambda x: x.get('similarity_score', 0), reverse=True)
        
        return {
            "query": query,
            "primary_rag_used": primary_rag,
            "model_used": self.rag_systems[primary_rag].model_name,
            "domain_detected": primary_rag,
            "results": all_results[:max_chunks],
            "total_results_found": len(all_results),
            "routing_info": {
                "primary_results": len(primary_results),
                "backup_results": len(backup_results)
            }
        }
    
    def audit_external_response(self, response: str, source_chunks: List[Dict[str, Any]], 
                               query: str) -> Dict[str, Any]:
        """
        Audit an external API response against source chunks
        """
        print(f"🔍 Auditing external response...")
        
        # Perform safety audit
        safety_audit = self.safety_auditor.audit_response(response, source_chunks)
        
        # Additional embedding-based similarity check (using technical RAG as baseline)
        technical_rag = self.rag_systems["technical"]
        if technical_rag.model is not None:
            response_embedding = technical_rag.embed_text(response)
            
            # Compare with source chunk embeddings
            chunk_similarities = []
            for chunk in source_chunks:
                if 'embedding' in chunk:
                    chunk_embedding = np.array(chunk['embedding'])
                    similarity = np.dot(response_embedding, chunk_embedding) / (
                        np.linalg.norm(response_embedding) * np.linalg.norm(chunk_embedding)
                    )
                    chunk_similarities.append(similarity)
            
            avg_similarity = np.mean(chunk_similarities) if chunk_similarities else 0.0
        else:
            avg_similarity = safety_audit['content_similarity']
        
        # Combine audit results
        audit_result = {
            "query": query,
            "response_length": len(response),
            "source_chunks_count": len(source_chunks),
            "safety_audit": safety_audit,
            "embedding_similarity": float(avg_similarity),
            "overall_confidence": self._calculate_confidence(safety_audit, avg_similarity),
            "timestamp": "now",  # You'd use actual timestamp
            "audit_passed": safety_audit["audit_passed"] and avg_similarity > 0.6
        }
        
        return audit_result
    
    def _calculate_confidence(self, safety_audit: Dict, embedding_similarity: float) -> str:
        """Calculate overall confidence in the response"""
        if safety_audit["risk_level"] == "high":
            return "low"
        elif safety_audit["risk_level"] == "medium" or embedding_similarity < 0.5:
            return "medium"
        elif embedding_similarity > 0.8 and safety_audit["audit_passed"]:
            return "high"
        else:
            return "medium"
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get information about the RAG system status"""
        info = {
            "rag_systems": {},
            "total_chunks": len(self.all_chunks),
            "system_ready": True
        }
        
        for name, rag in self.rag_systems.items():
            info["rag_systems"][name] = {
                "model": rag.model_name,
                "chunks_indexed": len(rag.chunk_metadata),
                "vector_dimension": rag.vector_dim,
                "model_loaded": rag.model is not None
            }
        
        return info


# Factory function for easy initialization
def create_bidirectional_rag() -> BidirectionalRAGSystem:
    """Create and return a configured bidirectional RAG system"""
    return BidirectionalRAGSystem()
