"""
TokenSight Massive JSON Processor
==================================

Specialized streaming processor for gigantic JSON API files (multi-million line datasets)
This module handles large-scale structured data ingestion that would otherwise cause memory overflow.

IMPORTANT SECURITY NOTE:
========================
This processor bypasses TokenSight's standard encryption/encoding pipeline for PROOF OF CONCEPT ONLY.
The steganographic encoding layer is skipped due to:
1. Scale limitations (1.4M+ lines per file would overwhelm current encoding pipeline)
2. JSON structure preservation requirements 
3. Performance optimization for streaming processing

PRODUCTION CONSIDERATIONS:
=========================
- For production deployments with adequate system resources, the full encryption pipeline should be used
- Users with sufficient memory/processing power can route gigantic files through standard TokenSight pipeline
- This bypass is a temporary architectural decision for demonstration purposes
- Future versions should include streaming-compatible encryption options

Author: TokenSight Framework
Date: July 2025
Purpose: Handle FDA-scale JSON datasets and similar massive structured data
"""

import json
import ijson
import os
import sys
from typing import Dict, List, Any, Iterator, Optional, Union
from pathlib import Path
import time
from datetime import datetime

# TokenSight core imports
try:
    from tokensight_advanced_rag import TokenSightAdvancedRAG
    from memory_manager import initialize_memory
    TOKENSIGHT_AVAILABLE = True
except ImportError as e:
    print(f"⚠️ TokenSight core modules not available: {e}")
    print("   Running in standalone mode...")
    TOKENSIGHT_AVAILABLE = False


class MassiveJSONProcessor:
    """
    Streaming processor for gigantic JSON files that bypass standard TokenSight encryption
    
    Features:
    - Memory-efficient streaming JSON parsing
    - Configurable chunk size and batch processing  
    - Integration with TokenSight RAG systems
    - Progress tracking and recovery for long-running jobs
    - Flexible JSON structure detection and extraction
    """
    
    def __init__(self, 
                 tokensight_rag: Optional['TokenSightAdvancedRAG'] = None,
                 chunk_size: int = 1000,
                 enable_progress_saving: bool = True,
                 temp_dir: str = "massive_json_temp"):
        """
        Initialize the massive JSON processor
        
        Args:
            tokensight_rag: TokenSight RAG system for processing chunks
            chunk_size: Number of JSON records to process in each batch
            enable_progress_saving: Save progress periodically for recovery
            temp_dir: Directory for temporary files and progress tracking
        """
        self.tokensight_rag = tokensight_rag
        self.chunk_size = chunk_size
        self.enable_progress_saving = enable_progress_saving
        self.temp_dir = Path(temp_dir)
        self.temp_dir.mkdir(exist_ok=True)
        
        # Processing statistics
        self.stats = {
            'total_files_processed': 0,
            'total_records_processed': 0,
            'total_chunks_created': 0,
            'processing_start_time': None,
            'current_file': None,
            'errors': []
        }
        
        # Progress tracking
        self.progress_file = self.temp_dir / "processing_progress.json"
        self.load_progress()
        
        print("🔧 MassiveJSONProcessor initialized")
        print(f"   📊 Chunk size: {chunk_size:,} records per batch")
        print(f"   💾 Progress saving: {'enabled' if enable_progress_saving else 'disabled'}")
        print(f"   🗂️ Temp directory: {temp_dir}")
        print()
        print("⚠️  SECURITY NOTICE: Encryption bypassed for proof-of-concept")
        print("   → Production deployments should evaluate full encryption pipeline")
        print("   → This bypass is for demonstration of massive-scale JSON processing")
        print()
    
    def load_progress(self):
        """Load previous processing progress if available"""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    saved_progress = json.load(f)
                self.stats.update(saved_progress)
                print(f"📂 Loaded previous progress: {self.stats['total_records_processed']:,} records processed")
            except Exception as e:
                print(f"⚠️ Could not load progress file: {e}")
    
    def save_progress(self):
        """Save current processing progress"""
        if not self.enable_progress_saving:
            return
            
        try:
            progress_data = {
                **self.stats,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.progress_file, 'w') as f:
                json.dump(progress_data, f, indent=2, default=str)
        except Exception as e:
            print(f"⚠️ Could not save progress: {e}")
    
    def detect_json_structure(self, file_path: Union[str, Path], sample_size: int = 100) -> Dict[str, Any]:
        """
        Analyze JSON file structure to determine optimal parsing strategy
        
        Args:
            file_path: Path to the JSON file
            sample_size: Number of records to sample for structure analysis
            
        Returns:
            Dictionary with structure information and parsing recommendations
        """
        file_path = Path(file_path)
        print(f"🔍 Analyzing JSON structure: {file_path.name}")
        
        structure_info = {
            'file_size_mb': file_path.stat().st_size / (1024 * 1024),
            'estimated_records': 0,
            'root_structure': 'unknown',
            'sample_keys': set(),
            'nested_levels': 0,
            'recommended_chunk_size': self.chunk_size,
            'parsing_strategy': 'items'
        }
        
        try:
            with open(file_path, 'rb') as file:
                # Try to detect if it's an array of objects or object with array property
                file_start = file.read(1024).decode('utf-8', errors='ignore')
                
                if file_start.strip().startswith('['):
                    structure_info['root_structure'] = 'array'
                    structure_info['parsing_strategy'] = 'item'
                elif file_start.strip().startswith('{'):
                    structure_info['root_structure'] = 'object'
                    structure_info['parsing_strategy'] = 'items'  # Will need to adjust based on actual structure
                
                # Sample some records to understand structure
                file.seek(0)
                try:
                    if structure_info['root_structure'] == 'array':
                        parser = ijson.items(file, 'item')
                    else:
                        # For objects, we'll need to detect the array property
                        # This is a simplified approach - may need adjustment for specific APIs
                        parser = ijson.items(file, '*.item')
                    
                    sample_count = 0
                    for record in parser:
                        if isinstance(record, dict):
                            structure_info['sample_keys'].update(record.keys())
                            # Estimate nesting level
                            max_depth = self._calculate_dict_depth(record)
                            structure_info['nested_levels'] = max(structure_info['nested_levels'], max_depth)
                        
                        sample_count += 1
                        if sample_count >= sample_size:
                            break
                    
                    structure_info['estimated_records'] = sample_count * (structure_info['file_size_mb'] / 10)  # Rough estimate
                    
                except Exception as parsing_error:
                    print(f"⚠️ Could not parse sample records: {parsing_error}")
                    structure_info['parsing_strategy'] = 'fallback'
        
        except Exception as e:
            print(f"❌ Error analyzing file structure: {e}")
            return structure_info
        
        # Convert set to list for JSON serialization
        structure_info['sample_keys'] = list(structure_info['sample_keys'])
        
        print(f"📊 Structure Analysis Results:")
        print(f"   📁 File size: {structure_info['file_size_mb']:.1f} MB")
        print(f"   🔢 Estimated records: {structure_info['estimated_records']:,.0f}")
        print(f"   🏗️ Root structure: {structure_info['root_structure']}")
        print(f"   🔑 Sample keys: {', '.join(list(structure_info['sample_keys'])[:10])}")
        print(f"   📐 Max nesting depth: {structure_info['nested_levels']}")
        print(f"   ⚙️ Parsing strategy: {structure_info['parsing_strategy']}")
        print()
        
        return structure_info
    
    def _calculate_dict_depth(self, d: Dict[str, Any], current_depth: int = 0) -> int:
        """Calculate maximum nesting depth of a dictionary"""
        if not isinstance(d, dict):
            return current_depth
        
        max_depth = current_depth
        for value in d.values():
            if isinstance(value, dict):
                depth = self._calculate_dict_depth(value, current_depth + 1)
                max_depth = max(max_depth, depth)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                depth = self._calculate_dict_depth(value[0], current_depth + 1)
                max_depth = max(max_depth, depth)
        
        return max_depth
    
    def stream_json_chunks(self, file_path: Union[str, Path], 
                          json_path: str = 'item',
                          progress_callback: Optional[callable] = None) -> Iterator[List[Dict[str, Any]]]:
        """
        Stream parse massive JSON file into manageable chunks
        
        Args:
            file_path: Path to the JSON file
            json_path: JSONPath for parsing (e.g., 'item' for arrays, 'data.item' for nested)
            progress_callback: Optional callback function for progress updates
            
        Yields:
            Lists of JSON records (chunks)
        """
        file_path = Path(file_path)
        print(f"🌊 Starting streaming parse: {file_path.name}")
        print(f"   📍 JSON path: {json_path}")
        print(f"   📦 Chunk size: {self.chunk_size:,} records")
        
        chunk = []
        record_count = 0
        start_time = time.time()
        
        try:
            with open(file_path, 'rb') as file:
                parser = ijson.items(file, json_path)
                
                for record in parser:
                    chunk.append(record)
                    record_count += 1
                    
                    # Yield chunk when it reaches target size
                    if len(chunk) >= self.chunk_size:
                        elapsed = time.time() - start_time
                        rate = record_count / elapsed if elapsed > 0 else 0
                        
                        print(f"   📊 Processed {record_count:,} records ({rate:.1f} records/sec)")
                        
                        if progress_callback:
                            progress_callback(record_count, len(chunk))
                        
                        yield chunk
                        chunk = []
                
                # Yield final chunk if it has records
                if chunk:
                    print(f"   📦 Final chunk: {len(chunk)} records")
                    yield chunk
                    
        except Exception as e:
            error_msg = f"Error streaming {file_path}: {e}"
            print(f"❌ {error_msg}")
            self.stats['errors'].append({
                'file': str(file_path),
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })
            raise
        
        total_time = time.time() - start_time
        rate = record_count / total_time if total_time > 0 else 0
        print(f"✅ Streaming complete: {record_count:,} records in {total_time:.1f}s ({rate:.1f} records/sec)")
    
    def extract_meaningful_chunks(self, json_records: List[Dict[str, Any]], 
                                 extraction_config: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """
        Convert raw JSON records into meaningful text chunks for TokenSight processing
        
        Args:
            json_records: List of JSON record dictionaries
            extraction_config: Configuration for field extraction and text generation
            
        Returns:
            List of structured chunks suitable for TokenSight RAG processing
        """
        if extraction_config is None:
            # Default extraction config - attempts to handle generic JSON structures
            extraction_config = {
                'primary_text_fields': ['name', 'title', 'description', 'content', 'text', 'summary'],
                'metadata_fields': ['id', 'type', 'category', 'date', 'author', 'source'],
                'concatenate_all_text': True,  # If no primary fields found, concatenate all string values
                'max_text_length': 5000,  # Limit text length per chunk
                'include_structure_info': True  # Include info about JSON structure
            }
        
        meaningful_chunks = []
        
        for i, record in enumerate(json_records):
            try:
                chunk_text_parts = []
                metadata = {}
                
                # Extract primary text content
                for field in extraction_config['primary_text_fields']:
                    if field in record and isinstance(record[field], str):
                        chunk_text_parts.append(f"{field.title()}: {record[field]}")
                
                # Extract metadata
                for field in extraction_config['metadata_fields']:
                    if field in record:
                        metadata[field] = record[field]
                
                # If no primary text found, concatenate all string values
                if not chunk_text_parts and extraction_config.get('concatenate_all_text', True):
                    for key, value in record.items():
                        if isinstance(value, str) and len(value.strip()) > 0:
                            chunk_text_parts.append(f"{key}: {value}")
                        elif isinstance(value, (int, float)):
                            chunk_text_parts.append(f"{key}: {value}")
                
                # Combine text parts
                full_text = "\n".join(chunk_text_parts)
                
                # Truncate if too long
                if len(full_text) > extraction_config['max_text_length']:
                    full_text = full_text[:extraction_config['max_text_length']] + "... [truncated]"
                
                # Create TokenSight-compatible chunk
                chunk_data = {
                    "chunk_id": f"json_record_{self.stats['total_records_processed'] + i + 1}",
                    "content": full_text,
                    "source_type": "structured_json",
                    "original_record_index": i,
                    "metadata": metadata,
                    "processing_method": "json_streaming_extraction",
                    "encryption_bypassed": True,  # Flag for audit trail
                    "original_record": record if extraction_config.get('preserve_original', False) else None
                }
                
                # Add structure information
                if extraction_config.get('include_structure_info', True):
                    chunk_data['json_structure_info'] = {
                        'total_fields': len(record),
                        'field_types': {k: type(v).__name__ for k, v in record.items()},
                        'estimated_tokens': len(full_text.split())
                    }
                
                meaningful_chunks.append(chunk_data)
                
            except Exception as e:
                error_msg = f"Error extracting chunk from record {i}: {e}"
                print(f"⚠️ {error_msg}")
                self.stats['errors'].append({
                    'record_index': i,
                    'error': error_msg,
                    'timestamp': datetime.now().isoformat()
                })
                continue
        
        print(f"🔧 Extracted {len(meaningful_chunks)} meaningful chunks from {len(json_records)} JSON records")
        return meaningful_chunks
    
    def process_single_file(self, file_path: Union[str, Path], 
                           json_path: str = 'item',
                           extraction_config: Optional[Dict[str, Any]] = None,
                           save_intermediate: bool = True) -> Dict[str, Any]:
        """
        Process a single massive JSON file through the complete pipeline
        
        Args:
            file_path: Path to the JSON file
            json_path: JSONPath for parsing
            extraction_config: Configuration for chunk extraction
            save_intermediate: Save intermediate results for recovery
            
        Returns:
            Processing results and statistics
        """
        file_path = Path(file_path)
        
        print(f"📁 Processing massive JSON file: {file_path.name}")
        print("=" * 60)
        
        self.stats['current_file'] = str(file_path)
        self.stats['processing_start_time'] = datetime.now().isoformat()
        
        # Analyze file structure
        structure_info = self.detect_json_structure(file_path)
        
        # Adjust JSON path based on structure analysis
        if json_path == 'item' and structure_info['parsing_strategy'] != 'item':
            json_path = structure_info['parsing_strategy']
            print(f"🔄 Adjusted JSON path to: {json_path}")
        
        total_chunks_processed = 0
        batch_count = 0
        
        try:
            # Stream process the file
            for json_chunk in self.stream_json_chunks(file_path, json_path):
                batch_count += 1
                print(f"\n📦 Processing batch {batch_count}...")
                
                # Extract meaningful chunks
                meaningful_chunks = self.extract_meaningful_chunks(json_chunk, extraction_config)
                
                if not meaningful_chunks:
                    print("⚠️ No meaningful chunks extracted from this batch")
                    continue
                
                # Process through TokenSight RAG if available
                if self.tokensight_rag and TOKENSIGHT_AVAILABLE:
                    try:
                        doc_info = {
                            "source": str(file_path),
                            "type": "massive_json_dataset",
                            "batch_number": batch_count,
                            "structure_info": structure_info,
                            "processing_method": "streaming_bypass",
                            "encryption_bypassed": True
                        }
                        
                        self.tokensight_rag.process_document_chunks(meaningful_chunks, doc_info)
                        print(f"   ✅ Added {len(meaningful_chunks)} chunks to TokenSight RAG")
                        
                    except Exception as e:
                        print(f"   ⚠️ TokenSight RAG processing error: {e}")
                        # Continue processing even if RAG fails
                
                # Save intermediate results
                if save_intermediate and batch_count % 10 == 0:  # Save every 10 batches
                    intermediate_file = self.temp_dir / f"{file_path.stem}_batch_{batch_count}.json"
                    try:
                        with open(intermediate_file, 'w') as f:
                            json.dump({
                                'batch_number': batch_count,
                                'chunks_processed': len(meaningful_chunks),
                                'timestamp': datetime.now().isoformat(),
                                'file_source': str(file_path)
                            }, f, indent=2)
                        print(f"   💾 Saved intermediate results to {intermediate_file.name}")
                    except Exception as e:
                        print(f"   ⚠️ Could not save intermediate results: {e}")
                
                total_chunks_processed += len(meaningful_chunks)
                self.stats['total_records_processed'] += len(json_chunk)
                self.stats['total_chunks_created'] += len(meaningful_chunks)
                
                # Save progress periodically
                if batch_count % 5 == 0:
                    self.save_progress()
        
        except Exception as e:
            error_msg = f"Critical error processing {file_path}: {e}"
            print(f"❌ {error_msg}")
            self.stats['errors'].append({
                'file': str(file_path),
                'error': error_msg,
                'timestamp': datetime.now().isoformat()
            })
            raise
        
        # Update statistics
        self.stats['total_files_processed'] += 1
        
        # Final results
        results = {
            'file_processed': str(file_path),
            'batches_processed': batch_count,
            'total_chunks_created': total_chunks_processed,
            'structure_analysis': structure_info,
            'processing_time': datetime.now().isoformat(),
            'errors': len([e for e in self.stats['errors'] if e.get('file') == str(file_path)])
        }
        
        print(f"\n✅ File processing complete!")
        print(f"   📊 Batches processed: {batch_count}")
        print(f"   🧩 Total chunks created: {total_chunks_processed:,}")
        print(f"   ⚠️ Errors encountered: {results['errors']}")
        
        return results
    
    def process_multiple_files(self, file_paths: List[Union[str, Path]], 
                              **kwargs) -> Dict[str, Any]:
        """
        Process multiple massive JSON files sequentially
        
        Args:
            file_paths: List of paths to JSON files
            **kwargs: Arguments passed to process_single_file
            
        Returns:
            Comprehensive processing results
        """
        print(f"🚀 Starting massive JSON processing pipeline")
        print(f"📁 Files to process: {len(file_paths)}")
        print("=" * 60)
        
        all_results = []
        overall_start_time = time.time()
        
        for i, file_path in enumerate(file_paths, 1):
            print(f"\n🎯 Processing file {i}/{len(file_paths)}: {Path(file_path).name}")
            print("-" * 40)
            
            try:
                result = self.process_single_file(file_path, **kwargs)
                all_results.append(result)
                
                # Progress update
                elapsed_time = time.time() - overall_start_time
                avg_time_per_file = elapsed_time / i
                remaining_files = len(file_paths) - i
                estimated_remaining_time = remaining_files * avg_time_per_file
                
                print(f"📈 Overall Progress: {i}/{len(file_paths)} files complete")
                print(f"⏱️ Estimated time remaining: {estimated_remaining_time/60:.1f} minutes")
                
            except Exception as e:
                print(f"❌ Failed to process {file_path}: {e}")
                all_results.append({
                    'file_processed': str(file_path),
                    'error': str(e),
                    'failed': True
                })
                continue
        
        # Final summary
        total_time = time.time() - overall_start_time
        successful_files = len([r for r in all_results if not r.get('failed', False)])
        total_chunks = sum(r.get('total_chunks_created', 0) for r in all_results)
        
        summary = {
            'total_files_attempted': len(file_paths),
            'successful_files': successful_files,
            'failed_files': len(file_paths) - successful_files,
            'total_chunks_created': total_chunks,
            'total_processing_time_minutes': total_time / 60,
            'average_time_per_file_minutes': (total_time / len(file_paths)) / 60,
            'processing_rate_chunks_per_minute': total_chunks / (total_time / 60) if total_time > 0 else 0,
            'individual_results': all_results,
            'final_stats': self.stats
        }
        
        print(f"\n🎉 MASSIVE JSON PROCESSING COMPLETE!")
        print("=" * 60)
        print(f"✅ Successfully processed: {successful_files}/{len(file_paths)} files")
        print(f"🧩 Total chunks created: {total_chunks:,}")
        print(f"⏱️ Total processing time: {total_time/60:.1f} minutes")
        print(f"🚀 Processing rate: {summary['processing_rate_chunks_per_minute']:.1f} chunks/minute")
        
        # Save final results
        results_file = self.temp_dir / f"massive_json_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        try:
            with open(results_file, 'w') as f:
                json.dump(summary, f, indent=2, default=str)
            print(f"💾 Complete results saved to: {results_file}")
        except Exception as e:
            print(f"⚠️ Could not save final results: {e}")
        
        return summary


def main():
    """
    Demo/test function for the massive JSON processor
    """
    print("🧪 TokenSight Massive JSON Processor - Demo Mode")
    print("=" * 60)
    
    # Initialize processor
    processor = MassiveJSONProcessor(
        chunk_size=500,  # Smaller chunks for demo
        enable_progress_saving=True
    )
    
    # Example: Create a sample large JSON file for testing
    demo_file = "demo_massive_data.json"
    if not os.path.exists(demo_file):
        print("📝 Creating demo JSON file...")
        sample_data = []
        for i in range(10000):  # 10K records for demo
            sample_data.append({
                "id": f"record_{i+1}",
                "name": f"Sample Record {i+1}",
                "description": f"This is a sample description for record {i+1} with some meaningful content.",
                "category": f"category_{(i % 10) + 1}",
                "value": i * 1.5,
                "metadata": {
                    "created": f"2025-01-{(i % 28) + 1:02d}",
                    "tags": [f"tag_{j}" for j in range(i % 5)]
                }
            })
        
        with open(demo_file, 'w') as f:
            json.dump(sample_data, f)
        print(f"✅ Created {demo_file} with {len(sample_data)} records")
    
    # Process the demo file
    try:
        results = processor.process_single_file(
            demo_file,
            json_path='item',  # Since we created an array
            save_intermediate=True
        )
        
        print("\n📊 Demo Results:")
        print(f"   Batches processed: {results['batches_processed']}")
        print(f"   Chunks created: {results['total_chunks_created']}")
        print(f"   Structure detected: {results['structure_analysis']['root_structure']}")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
