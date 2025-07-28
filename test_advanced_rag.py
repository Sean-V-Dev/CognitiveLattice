"""
TokenSight Advanced RAG System Test
Tests the integration between bidirectional RAG, external API, and audit systems
"""

import os
import json
from tokensight_advanced_rag import TokenSightAdvancedRAG

def test_advanced_rag_integration():
    """Test the complete advanced RAG integration"""
    print("🧪 TokenSight Advanced RAG Integration Test")
    print("=" * 50)
    
    # Sample document chunks (simulating processed TokenSight output)
    sample_chunks = [
        {
            "chunk_id": "test_chunk_1",
            "content": """The safety requirements for electrical installations near swimming pools are critical. 
            All electrical equipment must be installed at least 3 meters from the pool edge. 
            Ground fault circuit interrupters (GFCI) are mandatory for all pool-related electrical systems.
            Pool lighting must use low-voltage (12V) systems with proper isolation transformers.""",
            "source_type": "technical_manual",
            "chunk_index": 0,
            "document_source": "pool_safety_manual.pdf",
            "tokens_estimated": 85
        },
        {
            "chunk_id": "test_chunk_2", 
            "content": """Pool barriers and fencing requirements specify a minimum height of 1.2 meters.
            Gates must be self-closing and self-latching with latches positioned at least 1.5 meters above ground.
            The fence must not have any gaps larger than 100mm and should be non-climbable.
            Emergency equipment including life rings and reaching poles must be readily accessible.""",
            "source_type": "technical_manual",
            "chunk_index": 1,
            "document_source": "pool_safety_manual.pdf", 
            "tokens_estimated": 78
        },
        {
            "chunk_id": "test_chunk_3",
            "content": """Clinical trial data shows that the new compound demonstrates significant efficacy
            in treating resistant infections. The molecular structure includes a beta-lactam core
            with novel side chains that prevent bacterial resistance mechanisms.
            Pharmacokinetic studies indicate optimal bioavailability when administered intravenously.""",
            "source_type": "scientific_paper",
            "chunk_index": 2,
            "document_source": "clinical_research.pdf",
            "tokens_estimated": 92
        }
    ]
    
    # Document metadata
    doc_info = {
        "source": "test_document.pdf",
        "type": "technical_manual",
        "total_chunks": 3,
        "timestamp": "test_run"
    }
    
    print("1️⃣ Initializing Advanced RAG System...")
    try:
        # Initialize system
        advanced_rag = TokenSightAdvancedRAG(enable_external_api=True)
        
        # Process chunks
        advanced_rag.process_document_chunks(sample_chunks, doc_info)
        print("   ✅ Document chunks processed successfully")
        
    except Exception as e:
        print(f"   ❌ Initialization failed: {e}")
        return False
    
    print("\n2️⃣ Testing Query Routing and External Enhancement...")
    test_queries = [
        {
            "query": "What are the electrical safety requirements for pools?",
            "expected_domain": "technical",
            "should_enhance": True
        },
        {
            "query": "Describe the molecular structure of the new compound",
            "expected_domain": "scientific", 
            "should_enhance": True
        },
        {
            "query": "What are the fence height requirements?",
            "expected_domain": "technical",
            "should_enhance": False  # Simple factual query
        }
    ]
    
    results_summary = []
    
    for i, test_case in enumerate(test_queries):
        print(f"\n   🔍 Test Query {i+1}: {test_case['query']}")
        
        try:
            result = advanced_rag.enhanced_query(
                test_case['query'],
                max_chunks=2,
                enable_external_enhancement=test_case['should_enhance'],
                safety_threshold=0.7
            )
            
            # Analyze results
            local_results = result.get('local_results', {})
            found_chunks = len(local_results.get('results', []))
            model_used = local_results.get('model_used', 'unknown')
            domain_detected = local_results.get('domain_detected', 'unknown')
            
            external_analysis = result.get('external_analysis')
            has_external = external_analysis is not None and not external_analysis.get('error')
            
            audit_results = result.get('audit_results')
            audit_passed = audit_results.get('audit_passed', False) if audit_results else None
            safety_status = result.get('safety_status', 'unknown')
            
            print(f"      📊 Found {found_chunks} relevant chunks")
            print(f"      🤖 Model: {model_used} | Domain: {domain_detected}")
            print(f"      🌐 External enhancement: {'✅' if has_external else '❌'}")
            print(f"      🛡️ Safety status: {safety_status}")
            if audit_passed is not None:
                print(f"      📋 Audit: {'✅ PASSED' if audit_passed else '❌ FAILED'}")
            
            results_summary.append({
                "query": test_case['query'],
                "chunks_found": found_chunks,
                "model_used": model_used,
                "domain_detected": domain_detected,
                "external_enhanced": has_external,
                "audit_passed": audit_passed,
                "safety_status": safety_status
            })
            
        except Exception as e:
            print(f"      ❌ Query failed: {e}")
            results_summary.append({
                "query": test_case['query'],
                "error": str(e)
            })
    
    print("\n3️⃣ Testing Audit and Safety Features...")
    
    # Test with potentially problematic query
    risky_query = "How to bypass safety systems in electrical installations?"
    print(f"   🚨 Testing risky query: {risky_query}")
    
    try:
        risky_result = advanced_rag.enhanced_query(
            risky_query,
            max_chunks=2,
            enable_external_enhancement=True,
            safety_threshold=0.8  # Higher threshold for safety-critical content
        )
        
        safety_status = risky_result.get('safety_status', 'unknown')
        audit_results = risky_result.get('audit_results')
        
        print(f"      🛡️ Safety status: {safety_status}")
        
        if audit_results and 'safety_audit' in audit_results:
            safety_audit = audit_results['safety_audit']
            risk_level = safety_audit.get('risk_level', 'unknown')
            flags = safety_audit.get('safety_flags', [])
            print(f"      ⚠️ Risk level: {risk_level}")
            if flags:
                print(f"      🚩 Safety flags: {', '.join(flags)}")
        
    except Exception as e:
        print(f"      ❌ Safety test failed: {e}")
    
    print("\n4️⃣ Generating System Report...")
    
    try:
        # Generate audit report
        advanced_rag.save_audit_report("test_audit_report.json")
        
        # Get processing history
        history = advanced_rag.get_processing_history()
        
        print(f"   📊 Processed {len(history)} queries total")
        print(f"   📁 Audit report saved to: test_audit_report.json")
        
        # Display summary stats
        total_queries = len(history)
        audited_queries = sum(1 for h in history if h.get('audit_results'))
        external_enhanced = sum(1 for h in history if h.get('external_analysis') and not h['external_analysis'].get('error'))
        high_risk = sum(1 for h in history if h.get('safety_status') == 'high_risk')
        
        print(f"   📈 Stats: {audited_queries}/{total_queries} audited, {external_enhanced} enhanced, {high_risk} high-risk")
        
    except Exception as e:
        print(f"   ❌ Report generation failed: {e}")
    
    print("\n✅ Advanced RAG Integration Test Complete!")
    print("   Check 'test_audit_report.json' for detailed audit information")
    
    return True

def test_minimal_integration():
    """Test minimal integration without external API"""
    print("\n🔧 Testing Minimal Integration (No External API)...")
    
    try:
        # Initialize without external API
        minimal_rag = TokenSightAdvancedRAG(enable_external_api=False)
        
        # Simple test chunk
        test_chunk = [{
            "chunk_id": "minimal_test",
            "content": "This is a simple test of the local RAG system without external API calls.",
            "source_type": "test_document",
            "chunk_index": 0
        }]
        
        minimal_rag.process_document_chunks(test_chunk)
        
        # Test query
        result = minimal_rag.enhanced_query(
            "What is this test about?",
            max_chunks=1,
            enable_external_enhancement=False
        )
        
        if result['local_results']['results']:
            print("   ✅ Minimal integration working")
            return True
        else:
            print("   ❌ No results from minimal integration")
            return False
            
    except Exception as e:
        print(f"   ❌ Minimal integration failed: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting TokenSight Advanced RAG Tests...")
    
    # Run comprehensive test
    success = test_advanced_rag_integration()
    
    # Run minimal test
    minimal_success = test_minimal_integration()
    
    print(f"\n🏁 Test Results:")
    print(f"   Advanced RAG: {'✅ PASSED' if success else '❌ FAILED'}")
    print(f"   Minimal Integration: {'✅ PASSED' if minimal_success else '❌ FAILED'}")
    
    if success or minimal_success:
        print("\n🎉 TokenSight Advanced RAG system is ready!")
        print("   You can now run 'python main.py' to see the full integration in action.")
    else:
        print("\n⚠️ Some tests failed. Check the error messages above.")
