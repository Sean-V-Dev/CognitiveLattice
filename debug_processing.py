#!/usr/bin/env python3

import sys
import os
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_document_processing():
    try:
        print("🔧 Testing document processing pipeline...")
        
        # Test imports
        from processing.document_processor import run_document_pipeline
        print("✅ Successfully imported run_document_pipeline")
        
        # Load encryption key
        key_path = os.path.join('config', 'key.json')
        with open(key_path, 'r') as f:
            config = json.load(f)
            encryption_key = tuple(config['encryption_key'])
        print(f"✅ Loaded encryption key with {len(encryption_key)} items")
        
        # Test processing
        print("🚀 Running document processing on example.txt...")
        result = run_document_pipeline('example.txt', encryption_key)
        
        print("\n📊 PROCESSING RESULTS:")
        print(f"   Processing Success: {result.get('processing_success', False)}")
        print(f"   Total Chunks: {result.get('total_chunks', 0)}")
        print(f"   Source File: {result.get('source_file', 'N/A')}")
        print(f"   Doc Type: {result.get('doc_type', 'N/A')}")
        
        if not result.get('processing_success', False):
            print(f"❌ Error: {result.get('error', 'Unknown error')}")
        else:
            print("✅ Processing completed successfully!")
            
        # Test tool import
        from tools.document_processor_tool import document_processor
        print("✅ Successfully imported document_processor tool")
        
        # Test tool execution
        print("\n🔧 Testing tool execution...")
        tool_result = document_processor(
            source_file='example.txt',
            processing_mode='full',
            enable_external_api=True,
            session_manager=None
        )
        
        print("\n📊 TOOL RESULTS:")
        print(f"   Status: {tool_result.get('status', 'unknown')}")
        print(f"   Total Chunks: {tool_result.get('total_chunks', 0)}")
        print(f"   Processing Mode: {tool_result.get('processing_mode', 'N/A')}")
        
        if tool_result.get('status') != 'success':
            print(f"❌ Tool Error: {tool_result.get('message', 'Unknown error')}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_document_processing()
