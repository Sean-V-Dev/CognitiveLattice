"""
Integration layer for TokenSight's new Bidirectional RAG        # 1. Find relevant chunks using the bidirectional RAG system
        local_search_results = self.bidirectional_rag.search(
            query, 
            top_k=max_chunks,
            similarity_threshold=0.2  # Adjust as needed
        )m
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
        Enhanced query processing with bidirectional RAG and external API integration
        """
        print(f"🔍 Processing enhanced query: {query}")
        
        # 1. Find relevant chunks using the bidirectional RAG system
        local_search_results = self.rag_system.query_with_routing(
            query, 
            max_chunks=10 # Increased from 5 to 10
            # similarity_threshold parameter not available in this method
        )
        relevant_chunks = local_search_results.get("results", [])
        
        if not relevant_chunks:
            print("⚠️ No relevant local chunks found.")
            return {
                "query": query,
                "local_results": local_search_results,
                "external_analysis": {"error": "No local content to analyze."},
                "safety_status": "not_applicable",
                "audit_results": None
            }

        # 2. If external enhancement is enabled, send relevant chunks to the API
        external_analysis = None
        if enable_external_enhancement and self.external_client:
            analysis_type = self._determine_analysis_type(query, relevant_chunks)
            print(f"🌐 Sending to external API for {analysis_type} analysis...")
            # This call returns a list of results, one for each chunk
            external_analysis_results = self.external_client.analyze_multiple_chunks(
                relevant_chunks, 
                analysis_type=analysis_type
            )
            # Synthesize a single, user-friendly answer from all chunk analyses
            if external_analysis_results:
                print(f"✅ Completed external analysis of {len(external_analysis_results)} chunks")
                summary_result = self.external_client.summarize_analyses(external_analysis_results, query)
                summary_text = summary_result.get("summary_text")
                # Combine audit results from all chunks (as before)
                final_audit = {"audit_passed": True, "safety_audit": {"risk_level": "low", "details": []}}
                for res in external_analysis_results:
                    audit = res.get('audit_results', {})
                    if not audit.get('audit_passed', True):
                        final_audit['audit_passed'] = False
                    if audit.get('safety_audit', {}).get('risk_level') == 'high':
                        final_audit['safety_audit']['risk_level'] = 'high'
                external_analysis = {
                    "enhanced_answer": summary_text,
                    "audit_results": final_audit,
                    "raw_results": external_analysis_results,
                    "summary_result": summary_result
                }
            else:
                print("⚠️ External analysis returned no results.")
                external_analysis = {"error": "No results from external API."}

        # 3. Final response construction
        final_response = {
            "query": query,
            "local_results": local_search_results,
            "external_analysis": external_analysis,
            "safety_status": "safe",  # Default, can be updated by audit
            "audit_results": None # This will be populated by the final audit
        }

        # 4. Perform safety audit on the final combined response
        if external_analysis and not external_analysis.get("error"):
            # Use the aggregated audit results from the external analysis
            final_response["audit_results"] = external_analysis.get("audit_results")
            if final_response["audit_results"] and not final_response["audit_results"].get("audit_passed"):
                final_response["safety_status"] = "failed_audit"
        
        # Fallback audit if external analysis failed or was disabled
        if not final_response.get("audit_results"):
            # Create a synthesized answer from local results if no external answer exists
            synthesized_answer = " ".join([chunk.get('content', '') for chunk in relevant_chunks])
            
            # Safely extract the enhanced answer with null checks
            external_analysis = final_response.get("external_analysis") or {}
            enhanced_answer = external_analysis.get("enhanced_answer") if isinstance(external_analysis, dict) else None
            
            final_response["audit_results"] = self.rag_system.safety_auditor.audit_response(
                enhanced_answer or synthesized_answer,  # response (string)
                relevant_chunks  # source_chunks (list of dicts)
            )
            if not final_response["audit_results"]["audit_passed"]:
                final_response["safety_status"] = "failed_audit"
                
        return final_response
    
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
