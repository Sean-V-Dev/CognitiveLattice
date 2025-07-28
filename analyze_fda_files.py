"""
FDA File Analysis and Setup Script
=================================

This script helps analyze your massive FDA JSON files before processing
and provides setup guidance for optimal performance.

Usage:
    python analyze_fda_files.py --directory "path/to/fda/files"
    python analyze_fda_files.py --file "fda_file.json" --sample-size 100
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Any
import time

def analyze_file_structure(file_path: Path, sample_size: int = 50) -> Dict[str, Any]:
    """
    Analyze a single massive JSON file to understand its structure
    """
    print(f"🔍 Analyzing: {file_path.name}")
    
    analysis = {
        'file_path': str(file_path),
        'file_size_mb': file_path.stat().st_size / (1024 * 1024),
        'estimated_lines': 0,
        'sample_records': [],
        'common_fields': {},
        'structure_type': 'unknown',
        'recommended_settings': {}
    }
    
    # Quick line count estimate
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Count lines in first 1MB to estimate total
            sample_text = f.read(1024 * 1024)
            lines_in_sample = sample_text.count('\n')
            if lines_in_sample > 0:
                analysis['estimated_lines'] = int(lines_in_sample * analysis['file_size_mb'])
        
        print(f"   📏 Size: {analysis['file_size_mb']:.1f} MB")
        print(f"   📄 Estimated lines: {analysis['estimated_lines']:,}")
        
    except Exception as e:
        print(f"   ⚠️ Could not read file: {e}")
        return analysis
    
    # Analyze JSON structure
    try:
        import ijson
        
        with open(file_path, 'rb') as f:
            # Detect if it's array or object
            start_bytes = f.read(100).decode('utf-8', errors='ignore').strip()
            if start_bytes.startswith('['):
                analysis['structure_type'] = 'array'
                parser = ijson.items(f, 'item')
            elif start_bytes.startswith('{'):
                analysis['structure_type'] = 'object'
                # Try common patterns for API responses
                f.seek(0)
                try:
                    parser = ijson.items(f, 'results.item')  # Common pattern
                except:
                    try:
                        parser = ijson.items(f, 'data.item')  # Another common pattern
                    except:
                        parser = ijson.items(f, '*.item')  # Generic fallback
            else:
                print(f"   ❌ Unknown JSON structure")
                return analysis
            
            # Sample records
            record_count = 0
            field_frequency = {}
            
            for record in parser:
                if record_count >= sample_size:
                    break
                
                if isinstance(record, dict):
                    analysis['sample_records'].append(record)
                    
                    # Count field frequency
                    for field in record.keys():
                        field_frequency[field] = field_frequency.get(field, 0) + 1
                
                record_count += 1
            
            # Calculate common fields (appear in >50% of sample)
            threshold = record_count * 0.5
            analysis['common_fields'] = {
                field: freq for field, freq in field_frequency.items()
                if freq >= threshold
            }
            
            print(f"   📊 Sampled {record_count} records")
            print(f"   🔑 Common fields: {len(analysis['common_fields'])}")
            
    except ImportError:
        print("   ⚠️ ijson not available for structure analysis")
    except Exception as e:
        print(f"   ⚠️ Could not analyze JSON structure: {e}")
    
    # Generate recommendations
    analysis['recommended_settings'] = generate_processing_recommendations(analysis)
    
    return analysis

def generate_processing_recommendations(analysis: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate processing recommendations based on file analysis
    """
    size_mb = analysis['file_size_mb']
    estimated_lines = analysis.get('estimated_lines', 0)
    
    recommendations = {
        'chunk_size': 1000,
        'max_text_length': 5000,
        'processing_priority': 'medium',
        'estimated_processing_time_hours': 1,
        'memory_requirements_gb': 4,
        'special_considerations': []
    }
    
    # Adjust based on file size
    if size_mb < 100:  # Small files
        recommendations.update({
            'chunk_size': 2000,
            'max_text_length': 8000,
            'processing_priority': 'low',
            'estimated_processing_time_hours': 0.1,
            'memory_requirements_gb': 2
        })
    elif size_mb < 1000:  # Medium files (100MB - 1GB)
        recommendations.update({
            'chunk_size': 1000,
            'max_text_length': 6000,
            'processing_priority': 'medium',
            'estimated_processing_time_hours': 0.5,
            'memory_requirements_gb': 4
        })
    elif size_mb < 5000:  # Large files (1GB - 5GB)
        recommendations.update({
            'chunk_size': 500,
            'max_text_length': 4000,
            'processing_priority': 'high',
            'estimated_processing_time_hours': 2,
            'memory_requirements_gb': 8
        })
        recommendations['special_considerations'].append('Consider processing during off-peak hours')
    else:  # Massive files (>5GB)
        recommendations.update({
            'chunk_size': 250,
            'max_text_length': 3000,
            'processing_priority': 'critical',
            'estimated_processing_time_hours': estimated_lines / 10000,  # Rough estimate
            'memory_requirements_gb': 16
        })
        recommendations['special_considerations'].extend([
            'Process during dedicated time window',
            'Monitor system resources closely',
            'Consider splitting into smaller files if possible',
            'Enable all progress saving and recovery features'
        ])
    
    # Add line-based considerations
    if estimated_lines > 1000000:  # Over 1M lines
        recommendations['special_considerations'].append('Multi-million record dataset - expect long processing time')
        
    if estimated_lines > 10000000:  # Over 10M lines  
        recommendations['special_considerations'].append('Consider distributed processing if available')
    
    return recommendations

def analyze_directory(directory_path: Path, sample_size: int = 50) -> Dict[str, Any]:
    """
    Analyze all JSON files in a directory
    """
    print(f"📁 Analyzing directory: {directory_path}")
    
    json_files = list(directory_path.glob('*.json'))
    if not json_files:
        print("❌ No JSON files found in directory")
        return {}
    
    print(f"   Found {len(json_files)} JSON files")
    
    directory_analysis = {
        'directory_path': str(directory_path),
        'total_files': len(json_files),
        'individual_analyses': [],
        'overall_recommendations': {}
    }
    
    total_size_mb = 0
    total_estimated_lines = 0
    
    for i, file_path in enumerate(json_files, 1):
        print(f"\n[{i}/{len(json_files)}]", end=" ")
        
        file_analysis = analyze_file_structure(file_path, sample_size)
        directory_analysis['individual_analyses'].append(file_analysis)
        
        total_size_mb += file_analysis['file_size_mb']
        total_estimated_lines += file_analysis.get('estimated_lines', 0)
    
    # Generate overall recommendations
    directory_analysis['overall_recommendations'] = {
        'total_size_gb': total_size_mb / 1024,
        'total_estimated_lines': total_estimated_lines,
        'recommended_processing_order': 'smallest_first',
        'estimated_total_processing_time_hours': total_estimated_lines / 50000,  # Conservative estimate
        'system_requirements': {
            'minimum_ram_gb': 16,
            'recommended_ram_gb': 32,
            'disk_space_gb': total_size_mb / 1024 * 2,  # 2x for processing overhead
            'processing_cores': 'minimum 4, recommended 8+'
        },
        'batch_processing_recommendation': len(json_files) > 5
    }
    
    return directory_analysis

def print_analysis_summary(analysis: Dict[str, Any]):
    """
    Print a human-readable summary of the analysis
    """
    if 'total_files' in analysis:  # Directory analysis
        print(f"\n📊 DIRECTORY ANALYSIS SUMMARY")
        print("=" * 50)
        print(f"📁 Total files: {analysis['total_files']}")
        print(f"💾 Total size: {analysis['overall_recommendations']['total_size_gb']:.1f} GB")
        print(f"📄 Estimated total lines: {analysis['overall_recommendations']['total_estimated_lines']:,}")
        print(f"⏱️ Estimated processing time: {analysis['overall_recommendations']['estimated_total_processing_time_hours']:.1f} hours")
        
        print(f"\n💻 SYSTEM REQUIREMENTS:")
        req = analysis['overall_recommendations']['system_requirements']
        print(f"   RAM: {req['minimum_ram_gb']} GB minimum, {req['recommended_ram_gb']} GB recommended")
        print(f"   Disk space: {req['disk_space_gb']:.1f} GB")
        print(f"   CPU cores: {req['processing_cores']}")
        
        # Show largest files
        largest_files = sorted(analysis['individual_analyses'], 
                             key=lambda x: x['file_size_mb'], reverse=True)[:3]
        print(f"\n📈 LARGEST FILES:")
        for i, file_analysis in enumerate(largest_files, 1):
            print(f"   {i}. {Path(file_analysis['file_path']).name}: {file_analysis['file_size_mb']:.1f} MB")
    
    else:  # Single file analysis
        print(f"\n📊 FILE ANALYSIS SUMMARY")
        print("=" * 50)
        print(f"📁 File: {Path(analysis['file_path']).name}")
        print(f"💾 Size: {analysis['file_size_mb']:.1f} MB")
        print(f"📄 Estimated lines: {analysis.get('estimated_lines', 'unknown'):,}")
        print(f"🏗️ Structure: {analysis['structure_type']}")
        
        if analysis['common_fields']:
            print(f"\n🔑 COMMON FIELDS ({len(analysis['common_fields'])}):")
            for field, freq in list(analysis['common_fields'].items())[:10]:
                print(f"   • {field} (in {freq} records)")
        
        print(f"\n⚙️ RECOMMENDED SETTINGS:")
        rec = analysis['recommended_settings']
        print(f"   Chunk size: {rec['chunk_size']:,} records")
        print(f"   Max text length: {rec['max_text_length']:,} characters")
        print(f"   Processing priority: {rec['processing_priority']}")
        print(f"   Estimated time: {rec['estimated_processing_time_hours']:.1f} hours")
        print(f"   RAM requirement: {rec['memory_requirements_gb']} GB")
        
        if rec['special_considerations']:
            print(f"\n⚠️ SPECIAL CONSIDERATIONS:")
            for consideration in rec['special_considerations']:
                print(f"   • {consideration}")

def generate_processing_commands(analysis: Dict[str, Any]) -> List[str]:
    """
    Generate example processing commands based on analysis
    """
    commands = []
    
    if 'total_files' in analysis:  # Directory analysis
        directory_path = analysis['directory_path']
        
        # Basic directory processing
        commands.append(f'python fda_json_integration.py --directory "{directory_path}" --chunk-size 500')
        
        # Process largest file first
        if analysis['individual_analyses']:
            largest_file = max(analysis['individual_analyses'], key=lambda x: x['file_size_mb'])
            commands.append(f'python fda_json_integration.py --file "{largest_file["file_path"]}" --chunk-size 250')
        
    else:  # Single file analysis
        file_path = analysis['file_path']
        rec = analysis['recommended_settings']
        
        # Basic processing command
        commands.append(f'python fda_json_integration.py --file "{file_path}" --chunk-size {rec["chunk_size"]}')
        
        # Conservative processing command for very large files
        if analysis['file_size_mb'] > 1000:
            commands.append(f'python fda_json_integration.py --file "{file_path}" --chunk-size {rec["chunk_size"]//2}')
    
    return commands

def main():
    """
    Main analysis function
    """
    parser = argparse.ArgumentParser(description='Analyze massive FDA JSON files for optimal processing')
    parser.add_argument('--file', type=str, help='Single JSON file to analyze')
    parser.add_argument('--directory', type=str, help='Directory containing JSON files')
    parser.add_argument('--sample-size', type=int, default=50, help='Number of records to sample for analysis')
    parser.add_argument('--output', type=str, help='Save analysis results to JSON file')
    
    args = parser.parse_args()
    
    if not args.file and not args.directory:
        print("❌ Error: Must specify either --file or --directory")
        sys.exit(1)
    
    print("🔍 FDA File Analysis Tool")
    print("=" * 50)
    
    # Perform analysis
    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"❌ Error: File not found: {args.file}")
            sys.exit(1)
        
        analysis = analyze_file_structure(file_path, args.sample_size)
    
    elif args.directory:
        directory_path = Path(args.directory)
        if not directory_path.exists():
            print(f"❌ Error: Directory not found: {args.directory}")
            sys.exit(1)
        
        analysis = analyze_directory(directory_path, args.sample_size)
    
    # Print summary
    print_analysis_summary(analysis)
    
    # Generate processing commands
    print(f"\n🚀 SUGGESTED PROCESSING COMMANDS:")
    print("-" * 40)
    commands = generate_processing_commands(analysis)
    for i, command in enumerate(commands, 1):
        print(f"{i}. {command}")
    
    # Save results if requested
    if args.output:
        try:
            with open(args.output, 'w') as f:
                json.dump(analysis, f, indent=2, default=str)
            print(f"\n💾 Analysis results saved to: {args.output}")
        except Exception as e:
            print(f"⚠️ Could not save results: {e}")
    
    print(f"\n✅ Analysis complete!")
    print(f"💡 Next steps:")
    print(f"   1. Review system requirements and available resources")
    print(f"   2. Choose appropriate chunk size based on recommendations")
    print(f"   3. Run processing command with adequate time allocated")
    print(f"   4. Monitor progress and system resources during processing")

if __name__ == "__main__":
    main()
