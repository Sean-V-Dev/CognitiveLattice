"""
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
