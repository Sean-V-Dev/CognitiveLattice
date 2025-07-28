"""
Integration layer for TokenSight's new Bidirectional RAG System
Provides backward compatibility while enabling advanced multi-RAG capabilities
"""

from bidirectional_rag import BidirectionalRAGSystem, create_bidirectional_rag
from external_api_client import ExternalAPIClient
import json
import numpy as np
from typing import List, Dict, Any, Optional

class TokenSightAdvancedRAG:
    """
    Advanced RAG integration for TokenSight with multi-domain routing and audit
    """
    
    def __init__(self, enable_external_api: bool = True):
        # Initialize bidirectional RAG system
        self.rag_system = create_bidirectional_rag()
        
        # External API client for enhanced analysis
        self.external_client = None
        if enable_external_api:
            try:
                self.external_client = ExternalAPIClient(api_provider="openai")
                print("🌐 External API client initialized")
            except Exception as e:
                print(f"⚠️ External API not available: {e}")
        
        # Track processing history
        self.processing_history = []
    
    def process_document_chunks(self, chunks: List[Dict[str, Any]], 
                              document_info: Dict[str, Any] = None) -> None:
        """
        Process document chunks through the bidirectional RAG system
        """
        print(f"📄 Processing document with {len(chunks)} chunks...")
        
        # Add document info to chunks if provided
        if document_info:
            for chunk in chunks:
                chunk.update({
                    "document_source": document_info.get("source", "unknown"),
                    "document_type": document_info.get("type", "unknown"),
                    "processing_timestamp": document_info.get("timestamp", "now")
                })
        
        # Process through bidirectional RAG
        self.rag_system.add_document_chunks(chunks)
        
        print(f"✅ Document processed and indexed across specialized RAG systems")
    
    def enhanced_query(self, query: str, max_chunks: int = 5, 
                      enable_external_enhancement: bool = True,
                      safety_threshold: float = 0.7) -> Dict[str, Any]:
        """
        Enhanced query processing with external API enhancement and audit
        """
        print(f"🔍 Processing enhanced query: {query}")
        
        # Step 1: Query local RAG systems
        rag_results = self.rag_system.query_with_routing(query, max_chunks)
        
        if not rag_results["results"]:
            return {
                "query": query,
                "local_results": rag_results,
                "external_analysis": None,
                "audit_results": None,
                "status": "no_relevant_content_found"
            }
        
        # Step 2: External API enhancement (if enabled and available)
        external_analysis = None
        if enable_external_enhancement and self.external_client:
            try:
                # Prepare chunks for external analysis
                relevant_chunks = rag_results["results"]
                
                # Determine analysis type based on content
                analysis_type = self._determine_analysis_type(query, relevant_chunks)
                
                print(f"🌐 Sending to external API for {analysis_type} analysis...")
                external_analysis = self.external_client.analyze_multiple_chunks(
                    relevant_chunks, 
                    analysis_type=analysis_type
                )
                
            except Exception as e:
                print(f"⚠️ External API analysis failed: {e}")
                external_analysis = {"error": str(e)}
        
        # Step 3: Audit external response (if available)
        audit_results = None
        if external_analysis and not external_analysis.get("error"):
            # Extract response text from external analysis
            response_text = self._extract_response_text(external_analysis)
            
            if response_text:
                audit_results = self.rag_system.audit_external_response(
                    response_text, 
                    rag_results["results"], 
                    query
                )
                
                # Check if audit passes safety threshold
                if not audit_results.get("audit_passed", False):
                    print("⚠️ Response failed safety audit - flagging for review")
        
        # Compile complete response
        complete_response = {
            "query": query,
            "local_results": rag_results,
            "external_analysis": external_analysis,
            "audit_results": audit_results,
            "safety_status": self._determine_safety_status(audit_results, safety_threshold),
            "processing_timestamp": "now",
            "response_id": f"ts_{len(self.processing_history)}"
        }
        
        # Store in processing history
        self.processing_history.append(complete_response)
        
        return complete_response
    
    def _determine_analysis_type(self, query: str, chunks: List[Dict]) -> str:
        """Determine the best external analysis type based on content"""
        query_lower = query.lower()
        
        # Check for technical/procedural queries
        if any(word in query_lower for word in ["how to", "procedure", "install", "configure", "setup"]):
            return "technical"
        
        # Check for factual/data queries
        elif any(word in query_lower for word in ["what is", "definition", "specification", "dosage", "concentration"]):
            return "factual"
        
        # Check for visual/diagram queries
        elif any(word in query_lower for word in ["diagram", "figure", "chart", "image", "visual"]):
            return "visual"
        
        # Check chunk content for domain
        sample_content = " ".join([chunk.get("content", "")[:200] for chunk in chunks[:3]])
        content_lower = sample_content.lower()
        
        if any(word in content_lower for word in ["clinical", "pharmacology", "drug", "compound", "molecular"]):
            return "technical"  # Scientific/medical technical
        elif any(word in content_lower for word in ["regulation", "compliance", "guidance", "standard"]):
            return "comprehensive"  # Regulatory
        else:
            return "comprehensive"  # Default
    
    def _extract_response_text(self, external_analysis: List[Dict]) -> Optional[str]:
        """Extract response text from external analysis results"""
        if not external_analysis:
            return None
        
        response_parts = []
        for result in external_analysis:
            if isinstance(result, dict) and "external_analysis" in result:
                analysis = result["external_analysis"]
                if isinstance(analysis, dict):
                    # Extract text content from structured analysis
                    response_parts.append(json.dumps(analysis, indent=2))
                else:
                    response_parts.append(str(analysis))
            elif isinstance(result, dict):
                # Direct result format
                response_parts.append(json.dumps(result, indent=2))
            else:
                response_parts.append(str(result))
        
        return "\n\n".join(response_parts) if response_parts else None
    
    def _determine_safety_status(self, audit_results: Optional[Dict], threshold: float) -> str:
        """Determine overall safety status"""
        if not audit_results:
            return "not_audited"
        
        if audit_results.get("safety_audit", {}).get("risk_level") == "high":
            return "high_risk"
        elif not audit_results.get("audit_passed", False):
            return "audit_failed"
        elif audit_results.get("embedding_similarity", 0) < threshold:
            return "low_confidence"
        else:
            return "approved"
    
    def get_processing_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent processing history"""
        return self.processing_history[-limit:] if self.processing_history else []
    
    def save_audit_report(self, filepath: str = "tokensight_audit_report.json") -> None:
        """Save comprehensive audit report with JSON serialization handling"""
        try:
            # Convert numpy arrays to lists for JSON serialization
            def convert_numpy(obj):
                if hasattr(obj, 'tolist'):  # numpy array
                    return obj.tolist()
                elif hasattr(obj, 'item'):  # numpy scalar
                    return obj.item()
                elif isinstance(obj, (np.float32, np.float64)):
                    return float(obj)
                elif isinstance(obj, (np.int32, np.int64)):
                    return int(obj)
                return obj
            
            system_info = self.rag_system.get_system_info()
            
            report = {
                "system_info": system_info,
                "processing_history": self.get_processing_history(50),
                "audit_summary": self._generate_audit_summary(),
                "recommendations": self._generate_recommendations(),
                "timestamp": "now"
            }
            
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2, ensure_ascii=False, default=convert_numpy)
            
            print(f"📊 Audit report saved to {filepath}")
            
        except Exception as e:
            print(f"⚠️ Could not save full audit report: {e}")
            # Save a minimal report
            try:
                minimal_report = {
                    "timestamp": "now",
                    "error": str(e),
                    "processing_history_count": len(self.processing_history),
                    "audit_summary": self._generate_audit_summary()
                }
                with open(filepath, "w", encoding="utf-8") as f:
                    json.dump(minimal_report, f, indent=2, ensure_ascii=False)
                print(f"📋 Minimal audit report saved to {filepath}")
            except Exception as inner_e:
                print(f"❌ Could not save even minimal report: {inner_e}")
    
    def _generate_audit_summary(self) -> Dict[str, Any]:
        """Generate summary of audit results"""
        if not self.processing_history:
            return {"total_queries": 0}
        
        total_queries = len(self.processing_history)
        audited_queries = sum(1 for h in self.processing_history if h.get("audit_results"))
        high_risk_queries = sum(1 for h in self.processing_history 
                               if h.get("safety_status") == "high_risk")
        approved_queries = sum(1 for h in self.processing_history 
                              if h.get("safety_status") == "approved")
        
        return {
            "total_queries": total_queries,
            "audited_queries": audited_queries,
            "high_risk_queries": high_risk_queries,
            "approved_queries": approved_queries,
            "audit_rate": audited_queries / total_queries if total_queries > 0 else 0,
            "approval_rate": approved_queries / audited_queries if audited_queries > 0 else 0
        }
    
    def _generate_recommendations(self) -> List[str]:
        """Generate system recommendations based on usage patterns"""
        recommendations = []
        
        audit_summary = self._generate_audit_summary()
        
        if audit_summary.get("high_risk_queries", 0) > 0:
            recommendations.append("High-risk queries detected - consider implementing additional review processes")
        
        if audit_summary.get("audit_rate", 0) < 0.8:
            recommendations.append("Consider enabling external API auditing for more queries")
        
        if audit_summary.get("approval_rate", 1) < 0.9:
            recommendations.append("Low approval rate - review source document quality and chunking strategy")
        
        return recommendations


# Backward compatibility functions for existing TokenSight code
def process_chunks_advanced(chunks: List[Dict[str, Any]], 
                           document_info: Dict[str, Any] = None) -> TokenSightAdvancedRAG:
    """
    Process chunks through advanced RAG system (backward compatible)
    """
    advanced_rag = TokenSightAdvancedRAG()
    advanced_rag.process_document_chunks(chunks, document_info)
    return advanced_rag

def query_advanced_rag(rag_system: TokenSightAdvancedRAG, query: str, 
                      **kwargs) -> Dict[str, Any]:
    """
    Query the advanced RAG system (backward compatible)
    """
    return rag_system.enhanced_query(query, **kwargs)
