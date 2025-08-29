"""
CognitiveLattice FDA JSON Integration Script
=====================================

Integration script for processing massive FDA JSON API files with CognitiveLattice.
This script demonstrates how to use the MassiveJSONProcessor with real FDA-scale datasets.

USAGE EXAMPLES:
==============

1. Process single FDA file:
   python fda_json_integration.py --file "fda_api_data_1.json" --chunk-size 1000

2. Process all FDA files in directory:
   python fda_json_integration.py --directory "fda_data/" --chunk-size 500

3. Process with custom extraction config:
   python fda_json_integration.py --file "fda_data.json" --config "fda_extraction_config.json"

SECURITY NOTE:
=============
This script bypasses CognitiveLattice's encryption layer for proof-of-concept demonstration.
For production use with sensitive data, implement streaming-compatible encryption.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any, Optional

# Import our massive JSON processor
from experimental.massive_json_processor import MassiveJSONProcessor

# Import CognitiveLattice components if available
try:
    from CognitiveLattice_advanced_rag import CognitiveLatticeAdvancedRAG
    CognitiveLattice_AVAILABLE = True
except ImportError:
    print("⚠️ CognitiveLattice Advanced RAG not available - running in extraction-only mode")
    CognitiveLattice_AVAILABLE = False


class FDAJSONProcessor:
    """
    Specialized processor for FDA JSON API files
    Handles pharmaceutical/medical data extraction and safety considerations
    """
    
    def __init__(self, enable_CognitiveLattice_rag: bool = True):
        """Initialize FDA JSON processor"""
        
        # Initialize CognitiveLattice RAG with medical specialization if available
        self.CognitiveLattice_rag = None
        if enable_CognitiveLattice_rag and CognitiveLattice_AVAILABLE:
            try:
                # Use medical/scientific embeddings for pharmaceutical data
                self.CognitiveLattice_rag = CognitiveLatticeAdvancedRAG(
                    enable_external_api=True,
                    safety_threshold=0.8  # Higher safety threshold for medical data
                )
                print("✅ CognitiveLattice Advanced RAG initialized with medical specialization")
            except Exception as e:
                print(f"⚠️ Could not initialize CognitiveLattice RAG: {e}")
        
        # Initialize massive JSON processor
        self.processor = MassiveJSONProcessor(
            CognitiveLattice_rag=self.CognitiveLattice_rag,
            chunk_size=1000,  # Default for FDA data
            enable_progress_saving=True,
            temp_dir="fda_processing_temp"
        )
        
        print("🏥 FDA JSON Processor initialized")
    
    def get_fda_extraction_config(self) -> Dict[str, Any]:
        """
        Get extraction configuration optimized for FDA pharmaceutical data
        """
        return {
            # Primary fields likely to contain meaningful pharmaceutical information
            'primary_text_fields': [
                # Drug identification
                'brand_name', 'generic_name', 'active_ingredient', 'product_name',
                
                # Medical information  
                'indication', 'contraindications', 'warnings', 'precautions',
                'adverse_reactions', 'dosage_and_administration', 'clinical_pharmacology',
                
                # Pediatric-specific fields (for ELSA use case)
                'pediatric_use', 'pediatric_contraindications', 'pediatric_dosage',
                
                # General content fields
                'description', 'clinical_studies', 'mechanism_of_action',
                'pharmacokinetics', 'drug_interactions', 'overdosage',
                
                # Labeling information
                'boxed_warning', 'highlights', 'full_prescribing_information'
            ],
            
            # Metadata fields for pharmaceutical tracking
            'metadata_fields': [
                'ndc', 'application_number', 'product_id', 'route', 'dosage_form',
                'strength', 'manufacturer', 'approval_date', 'marketing_status',
                'therapeutic_equivalence_code', 'reference_drug', 'drug_class'
            ],
            
            # FDA-specific settings
            'concatenate_all_text': True,  # Capture all available medical info
            'max_text_length': 8000,  # Longer chunks for comprehensive medical info
            'include_structure_info': True,
            'preserve_original': False,  # Don't store full records (too large)
            
            # Medical data handling
            'extract_safety_warnings': True,
            'prioritize_pediatric_info': True,  # For ELSA use case
            'include_regulatory_metadata': True
        }
    
    def extract_fda_chunks(self, json_records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Extract chunks specifically optimized for FDA pharmaceutical data
        """
        extraction_config = self.get_fda_extraction_config()
        
        # Use the base extraction with FDA-specific config
        base_chunks = self.processor.extract_meaningful_chunks(json_records, extraction_config)
        
        # Add FDA-specific enhancements
        fda_enhanced_chunks = []
        
        for chunk in base_chunks:
            # Add pharmaceutical-specific metadata
            original_record = json_records[chunk['original_record_index']]
            
            # Extract drug classification
            drug_info = self._extract_drug_classification(original_record)
            chunk['drug_classification'] = drug_info
            
            # Flag pediatric-relevant content
            chunk['pediatric_relevant'] = self._is_pediatric_relevant(chunk['content'])
            
            # Extract safety level indicators
            chunk['safety_flags'] = self._extract_safety_flags(chunk['content'])
            
            # Estimate medical complexity
            chunk['medical_complexity'] = self._estimate_medical_complexity(chunk['content'])
            
            # Update source type to be more specific
            chunk['source_type'] = 'fda_pharmaceutical_database'
            
            fda_enhanced_chunks.append(chunk)
        
        print(f"🏥 Enhanced {len(fda_enhanced_chunks)} chunks with FDA-specific medical metadata")
        return fda_enhanced_chunks
    
    def _extract_drug_classification(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Extract drug classification information"""
        classification = {
            'therapeutic_class': 'unknown',
            'controlled_substance': False,
            'prescription_required': True,  # Default assumption for FDA data
            'drug_type': 'unknown'
        }
        
        # Look for classification indicators in various fields
        text_to_check = str(record).lower()
        
        # Therapeutic classes (simplified detection)
        if any(term in text_to_check for term in ['antibiotic', 'antimicrobial']):
            classification['therapeutic_class'] = 'antimicrobial'
        elif any(term in text_to_check for term in ['analgesic', 'pain', 'opioid']):
            classification['therapeutic_class'] = 'analgesic'
        elif any(term in text_to_check for term in ['antihistamine', 'allergy']):
            classification['therapeutic_class'] = 'antihistamine'
        elif any(term in text_to_check for term in ['vaccine', 'immunization']):
            classification['therapeutic_class'] = 'vaccine'
        
        # Controlled substance detection
        if any(term in text_to_check for term in ['controlled', 'schedule', 'dea']):
            classification['controlled_substance'] = True
        
        return classification
    
    def _is_pediatric_relevant(self, content: str) -> bool:
        """Check if content is relevant to pediatric use (for ELSA use case)"""
        pediatric_indicators = [
            'pediatric', 'child', 'children', 'infant', 'neonatal', 'adolescent',
            'age', 'years old', 'months old', 'pediatric use', 'safety in children',
            'contraindicated in children', 'not recommended for children'
        ]
        
        content_lower = content.lower()
        return any(indicator in content_lower for indicator in pediatric_indicators)
    
    def _extract_safety_flags(self, content: str) -> List[str]:
        """Extract safety warning flags from content"""
        safety_flags = []
        content_lower = content.lower()
        
        # Major safety indicators
        if any(term in content_lower for term in ['black box', 'boxed warning', 'contraindicated']):
            safety_flags.append('high_risk')
        
        if any(term in content_lower for term in ['warning', 'caution', 'adverse']):
            safety_flags.append('warnings_present')
        
        if any(term in content_lower for term in ['death', 'fatal', 'life-threatening']):
            safety_flags.append('serious_adverse_events')
        
        if any(term in content_lower for term in ['pregnancy', 'lactation', 'breastfeeding']):
            safety_flags.append('reproductive_concerns')
        
        return safety_flags
    
    def _estimate_medical_complexity(self, content: str) -> str:
        """Estimate the medical complexity of the content"""
        # Simple heuristic based on medical terminology density
        medical_terms = [
            'pharmacokinetics', 'bioavailability', 'metabolism', 'clearance',
            'half-life', 'cytochrome', 'enzyme', 'receptor', 'mechanism',
            'contraindication', 'pharmacodynamics', 'therapeutic', 'clinical'
        ]
        
        content_lower = content.lower()
        term_count = sum(1 for term in medical_terms if term in content_lower)
        
        if term_count >= 5:
            return 'high'
        elif term_count >= 2:
            return 'medium'
        else:
            return 'low'
    
    def process_fda_files(self, file_paths: List[str], 
                         chunk_size: Optional[int] = None,
                         custom_config: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process FDA JSON files with pharmaceutical-specific handling
        """
        if chunk_size:
            self.processor.chunk_size = chunk_size
        
        print(f"🏥 Processing {len(file_paths)} FDA JSON files")
        print(f"📊 Chunk size: {self.processor.chunk_size:,} records per batch")
        print("⚠️ MEDICAL DATA: Enhanced safety processing enabled")
        print()
        
        # Override the chunk extraction method to use FDA-specific logic
        original_extract_method = self.processor.extract_meaningful_chunks
        self.processor.extract_meaningful_chunks = self.extract_fda_chunks
        
        try:
            # Process files using the enhanced extraction
            results = self.processor.process_multiple_files(
                file_paths,
                extraction_config=custom_config or self.get_fda_extraction_config(),
                save_intermediate=True
            )
            
            # Add FDA-specific summary information
            results['fda_processing_summary'] = {
                'pediatric_relevant_chunks': 0,  # Would need to count from actual processing
                'high_risk_medications': 0,
                'controlled_substances': 0,
                'total_safety_flags': 0
            }
            
            return results
            
        finally:
            # Restore original method
            self.processor.extract_meaningful_chunks = original_extract_method


def main():
    """Command-line interface for FDA JSON processing"""
    parser = argparse.ArgumentParser(description='Process massive FDA JSON files with CognitiveLattice')
    
    parser.add_argument('--file', type=str, help='Single FDA JSON file to process')
    parser.add_argument('--directory', type=str, help='Directory containing FDA JSON files')
    parser.add_argument('--chunk-size', type=int, default=1000, help='Records per processing batch')
    parser.add_argument('--config', type=str, help='Custom extraction configuration JSON file')
    parser.add_argument('--no-rag', action='store_true', help='Disable CognitiveLattice RAG integration')
    parser.add_argument('--output', type=str, default='fda_processing_results.json', help='Output results file')
    
    args = parser.parse_args()
    
    # Validate arguments
    if not args.file and not args.directory:
        print("❌ Error: Must specify either --file or --directory")
        sys.exit(1)
    
    # Get list of files to process
    files_to_process = []
    
    if args.file:
        if not os.path.exists(args.file):
            print(f"❌ Error: File not found: {args.file}")
            sys.exit(1)
        files_to_process.append(args.file)
    
    if args.directory:
        directory = Path(args.directory)
        if not directory.exists():
            print(f"❌ Error: Directory not found: {args.directory}")
            sys.exit(1)
        
        json_files = list(directory.glob('*.json'))
        if not json_files:
            print(f"❌ Error: No JSON files found in {args.directory}")
            sys.exit(1)
        
        files_to_process.extend([str(f) for f in json_files])
    
    print(f"📁 Found {len(files_to_process)} JSON files to process")
    
    # Load custom config if provided
    custom_config = None
    if args.config:
        try:
            with open(args.config, 'r') as f:
                custom_config = json.load(f)
            print(f"📋 Loaded custom extraction config from {args.config}")
        except Exception as e:
            print(f"⚠️ Warning: Could not load config file {args.config}: {e}")
    
    # Initialize FDA processor
    try:
        processor = FDAJSONProcessor(enable_CognitiveLattice_rag=not args.no_rag)
        
        # Process the files
        results = processor.process_fda_files(
            files_to_process,
            chunk_size=args.chunk_size,
            custom_config=custom_config
        )
        
        # Save results
        with open(args.output, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        print(f"\n💾 Complete results saved to: {args.output}")
        
        # Display summary
        print(f"\n📊 Final Summary:")
        print(f"   ✅ Files processed: {results['successful_files']}/{results['total_files_attempted']}")
        print(f"   🧩 Total chunks created: {results['total_chunks_created']:,}")
        print(f"   ⏱️ Processing time: {results['total_processing_time_minutes']:.1f} minutes")
        print(f"   🚀 Processing rate: {results['processing_rate_chunks_per_minute']:.1f} chunks/minute")
        
    except Exception as e:
        print(f"❌ Processing failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
