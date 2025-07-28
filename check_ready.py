#!/usr/bin/env python3
"""
Quick startup check - runs before main.py to ensure everything is ready
"""

import time
import sys

def quick_check():
    """Quick dependency check with minimal output"""
    
    print("🔄 Quick system check...")
    
    try:
        # Test critical imports
        from sentence_transformers import SentenceTransformer
        from integrated_json_rag import IntegratedJSONRAG
        import fitz
        
        print("✅ System ready!")
        return True
        
    except Exception as e:
        print(f"❌ System not ready: {e}")
        print("💡 Run 'python startup.py' for full initialization")
        return False

if __name__ == "__main__":
    if not quick_check():
        print("\n🚨 Dependencies need initialization!")
        choice = input("Run full startup now? (y/n): ").lower().strip()
        if choice in ['y', 'yes']:
            print("Loading startup.py...")
            import startup
            startup.main()
        else:
            print("Please run 'python startup.py' before using main.py")
            sys.exit(1)
