"""
Session-based RAG system manager for CognitiveLattice
Handles storage and retrieval of RAG systems without JSON serialization issues
"""

from typing import Dict, Any, Optional
from datetime import datetime
import os

class RAGSystemManager:
    """
    Manages RAG systems in memory during the session to avoid JSON serialization issues
    """
    
    def __init__(self):
        self.active_rag_systems = {}  # document_id -> rag_system
        self.rag_metadata = {}  # document_id -> metadata
    
    def store_rag_system(self, document_id: str, rag_system, metadata: Dict[str, Any]) -> bool:
        """
        Store a RAG system with its metadata
        
        Args:
            document_id: Unique identifier for the document (e.g., file path + timestamp)
            rag_system: The CognitiveLatticeAdvancedRAG instance
            metadata: Serializable metadata about the RAG system
        
        Returns:
            bool: Success status
        """
        try:
            self.active_rag_systems[document_id] = rag_system
            self.rag_metadata[document_id] = {
                **metadata,
                "stored_at": datetime.now().isoformat(),
                "status": "active"
            }
            return True
        except Exception as e:
            print(f"⚠️ Failed to store RAG system: {e}")
            return False
    
    def get_rag_system(self, document_id: str = None):
        """
        Retrieve a RAG system
        
        Args:
            document_id: Specific document ID, or None for most recent
        
        Returns:
            RAG system instance or None
        """
        if document_id is None:
            # Return the most recent RAG system
            if not self.active_rag_systems:
                return None
            latest_id = max(self.rag_metadata.keys(), 
                           key=lambda k: self.rag_metadata[k].get('stored_at', ''))
            return self.active_rag_systems.get(latest_id)
        else:
            return self.active_rag_systems.get(document_id)
    
    def get_metadata(self, document_id: str = None) -> Optional[Dict[str, Any]]:
        """
        Get metadata for a RAG system
        
        Args:
            document_id: Specific document ID, or None for most recent
        
        Returns:
            Metadata dict or None
        """
        if document_id is None:
            if not self.rag_metadata:
                return None
            latest_id = max(self.rag_metadata.keys(), 
                           key=lambda k: self.rag_metadata[k].get('stored_at', ''))
            return self.rag_metadata.get(latest_id)
        else:
            return self.rag_metadata.get(document_id)
    
    def list_available_documents(self) -> Dict[str, Dict[str, Any]]:
        """
        List all available RAG systems with their metadata
        
        Returns:
            Dict mapping document_id to metadata
        """
        return self.rag_metadata.copy()
    
    def cleanup_old_systems(self, max_systems: int = 5):
        """
        Clean up old RAG systems to prevent memory bloat
        
        Args:
            max_systems: Maximum number of systems to keep
        """
        if len(self.active_rag_systems) <= max_systems:
            return
        
        # Sort by timestamp and keep only the most recent
        sorted_ids = sorted(self.rag_metadata.keys(), 
                           key=lambda k: self.rag_metadata[k].get('stored_at', ''),
                           reverse=True)
        
        to_remove = sorted_ids[max_systems:]
        for doc_id in to_remove:
            self.active_rag_systems.pop(doc_id, None)
            self.rag_metadata.pop(doc_id, None)
        
        print(f"🧹 Cleaned up {len(to_remove)} old RAG systems")

# Global instance for the session
_global_rag_manager = None

def get_rag_manager() -> RAGSystemManager:
    """Get the global RAG system manager instance"""
    global _global_rag_manager
    if _global_rag_manager is None:
        _global_rag_manager = RAGSystemManager()
    return _global_rag_manager
