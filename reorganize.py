"""
TokenSight Framework Reorganization Script
Helps organize the current messy structure into a clean MVP-ready layout
"""

import os
import shutil
from pathlib import Path


def create_directory_structure():
    """Create the recommended directory structure"""
    
    directories = [
        # Core framework
        "tokensight/core",
        "tokensight/processing", 
        "tokensight/handlers",
        "tokensight/rag",
        "tokensight/tools",
        "tokensight/utils",
        
        # Applications (specific use cases)
        "applications/medical",
        "applications/document_analysis", 
        "applications/demos",
        
        # Testing
        "tests/unit",
        "tests/integration",
        "tests/performance",
        
        # Configuration and data
        "config",
        "data/samples",
        "data/cache",
        "data/output",
        
        # Documentation
        "docs/api",
        "docs/tutorials",
        "docs/examples",
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"📁 Created: {directory}")


def suggest_file_moves():
    """Suggest where files should be moved for better organization"""
    
    move_suggestions = {
        # Core framework files
        "tokensight/core/": [
            "core/cognitive_lattice.py",  # Already created
            "external_api_client.py",
            "memory_manager.py"
        ],
        
        "tokensight/processing/": [
            "processing/document_processor.py",  # Already created
            "file_handler.py",
            "text_processor.py", 
            "encoder/",
            "decoder/",
            "page_extractor.py"
        ],
        
        "tokensight/handlers/": [
            "handlers/intent_handlers.py",  # Already created
            "llama_client.py"
        ],
        
        "tokensight/rag/": [
            "tokensight_advanced_rag.py",
            "bidirectional_rag.py",
            "integrated_json_rag.py",
            "rag_engine.py"
        ],
        
        "tokensight/tools/": [
            "tool_manager.py",
            "tools/"  # Entire directory
        ],
        
        "tokensight/utils/": [
            "utils/",  # Entire directory
            "cost_analysis.py",
            "check_usage.py",
            "check_ready.py",
            "check_key.py",
            "cleanup_analysis.py"
        ],
        
        # Applications (specific use cases)
        "applications/medical/": [
            "fda_json_integration.py",
            "analyze_fda_files.py", 
            "search_fda.py",
            "massive_json_processor.py",
            "test_pediatric_query.py"
        ],
        
        "applications/document_analysis/": [
            "extract_all_visuals.py"
        ],
        
        "applications/demos/": [
            "demo_smart_router.py"
        ],
        
        # Testing
        "tests/integration/": [
            "test_advanced_rag.py",
            "test_specialized_models.py",
            "test_flight_tools.py",
            "test_fda_simple.py",
            "test_model_names.py"
        ],
        
        "tests/performance/": [
            "tests/stress_test.py"
        ],
        
        # Data
        "data/samples/": [
            "example.txt",
            "example.pdf",
            "chapter1.txt", 
            "*.json"  # Sample data files
        ],
        
        "data/cache/": [
            "cache/",
            "__pycache__/",
            "*_temp/",
            "encoded_chunks/",
            "decoded_chunks/"
        ]
    }
    
    print("\n📋 Suggested File Organization:")
    print("=" * 50)
    
    for target_dir, files in move_suggestions.items():
        print(f"\n📁 {target_dir}")
        for file in files:
            if os.path.exists(file):
                status = "✅ EXISTS"
            else:
                status = "❓ NOT FOUND"
            print(f"   {status} {file}")


def create_package_init_files():
    """Create __init__.py files to make directories proper Python packages"""
    
    package_dirs = [
        "tokensight",
        "tokensight/core", 
        "tokensight/processing",
        "tokensight/handlers",
        "tokensight/rag",
        "tokensight/tools",
        "tokensight/utils",
        "applications",
        "applications/medical",
        "applications/document_analysis",
        "applications/demos"
    ]
    
    for pkg_dir in package_dirs:
        init_file = os.path.join(pkg_dir, "__init__.py")
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write(f'"""TokenSight {pkg_dir.replace("/", ".")} package"""\n')
            print(f"📦 Created package: {init_file}")


def create_setup_py():
    """Create a setup.py for the package"""
    
    setup_content = '''"""
TokenSight Framework Setup
"""

from setuptools import setup, find_packages

setup(
    name="tokensight",
    version="0.1.0",
    description="Advanced Document Processing with Cognitive Lattice Architecture",
    author="Sean V",
    packages=find_packages(),
    install_requires=[
        "sentence-transformers>=2.2.0",
        "torch>=1.9.0",
        "faiss-cpu>=1.7.0",
        "numpy>=1.21.0",
        "Pillow>=8.3.0",
        "requests>=2.25.0",
        "openai>=1.0.0"
    ],
    extras_require={
        "dev": [
            "pytest>=6.0.0",
            "black>=21.0.0",
            "flake8>=3.9.0",
            "mypy>=0.900"
        ],
        "medical": [
            "pandas>=1.3.0",
            "scikit-learn>=1.0.0"
        ]
    },
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    entry_points={
        "console_scripts": [
            "tokensight=tokensight.main:main",
        ],
    },
)
'''
    
    with open("setup.py", 'w') as f:
        f.write(setup_content)
    print("📦 Created setup.py for package installation")


def create_requirements_files():
    """Create requirements files for different environments"""
    
    # Base requirements
    base_requirements = """
# Core dependencies
sentence-transformers>=2.2.0
torch>=1.9.0
faiss-cpu>=1.7.0
numpy>=1.21.0
Pillow>=8.3.0
requests>=2.25.0
openai>=1.0.0
"""
    
    # Development requirements 
    dev_requirements = """
# Development dependencies
pytest>=6.0.0
black>=21.0.0
flake8>=3.9.0
mypy>=0.900
jupyter>=1.0.0
"""
    
    # Medical application requirements
    medical_requirements = """
# Medical application dependencies
pandas>=1.3.0
scikit-learn>=1.0.0
matplotlib>=3.4.0
seaborn>=0.11.0
"""
    
    requirements_files = {
        "requirements.txt": base_requirements,
        "requirements-dev.txt": dev_requirements,
        "requirements-medical.txt": medical_requirements
    }
    
    for filename, content in requirements_files.items():
        with open(filename, 'w') as f:
            f.write(content.strip())
        print(f"📋 Created {filename}")


def main():
    """Run the reorganization helper"""
    
    print("🏗️ TokenSight Framework Reorganization Helper")
    print("=" * 50)
    
    print("\n1. Creating recommended directory structure...")
    create_directory_structure()
    
    print("\n2. Creating package __init__.py files...")
    create_package_init_files()
    
    print("\n3. Creating setup.py...")
    create_setup_py()
    
    print("\n4. Creating requirements files...")
    create_requirements_files()
    
    print("\n5. File organization suggestions...")
    suggest_file_moves()
    
    print(f"\n✅ Reorganization helper complete!")
    print(f"\n🎯 Next Steps for MVP:")
    print(f"   1. Move files according to suggestions above")
    print(f"   2. Update import statements in moved files")
    print(f"   3. Test the refactored main_refactored.py")
    print(f"   4. Create a simple CLI interface")
    print(f"   5. Write basic documentation")
    print(f"   6. Package for distribution")


if __name__ == "__main__":
    main()
