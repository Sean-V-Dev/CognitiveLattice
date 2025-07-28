"""
File Handling Module for TokenSight
Handles PDF and text file reading, processing, and sanitization
"""

import pdfplumber


def read_txt_file(file_path):
    """
    Read text file with multiple encoding fallbacks.
    
    Args:
        file_path: Path to text file
        
    Returns:
        List of non-empty lines
    """
    encodings = ['utf-8', 'windows-1252', 'utf-8-sig']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                lines = [line.strip() for line in f if line.strip()]
            print(f"📄 Successfully read {file_path} with encoding: {encoding}")
            return lines
        except UnicodeDecodeError:
            print(f"⚠️ Failed with encoding: {encoding}")
    
    # Fallback with error ignoring
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [line.strip() for line in f if line.strip()]
    print(f"⚠️ Fallback read {file_path} with ignored errors")
    return lines


def read_pdf_file(file_path):
    """
    Extract text lines from PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        List of non-empty text lines
    """
    lines = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend([line.strip() for line in text.split('\n') if line.strip()])
    return lines


def sanitize_pdf(file_path, output_path="cleaned_input.txt"):
    """
    Extract PDF text and save to clean text file.
    
    Args:
        file_path: Path to PDF file
        output_path: Path to output text file
    """
    lines = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend([line.strip() for line in text.split('\n') if line.strip()])
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


def process_file(file_path, enable_multimodal=True):
    """
    Process PDF or text file and return text lines.
    
    Args:
        file_path: Path to input file
        enable_multimodal: Whether to enable multimodal features (unused in current implementation)
        
    Returns:
        List of text lines
        
    Raises:
        ValueError: If file format is not supported
    """
    if file_path.endswith(".pdf"):
        # Use traditional text-only extraction
        sanitize_pdf(file_path, "cleaned_input.txt")
        return read_txt_file("cleaned_input.txt")
    elif file_path.endswith(".txt"):
        return read_txt_file(file_path)
    else:
        raise ValueError("Unsupported file format. Use .txt or .pdf")
