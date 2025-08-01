"""
Text Processing Module for CognitiveLattice
Handles text chunking, paragraph extraction, and sentence splitting
"""

import re


def extract_paragraphs(lines):
    """Extract paragraphs from lines of text."""
    text = "\n".join(lines)
    raw_paras = re.split(r'\n\s*\n', text)
    return [p.replace("\n", " ").strip() for p in raw_paras if p.strip()]


def split_into_sentences(text):
    """Split text into sentences using basic punctuation."""
    return re.split(r'(?<=[.!?])\s+', text)


def chunk_paragraphs(paragraphs, max_tokens=450, flex_factor=1.5):
    """
    Intelligent paragraph chunking with flexible token limits.
    
    Args:
        paragraphs: List of paragraph strings
        max_tokens: Target maximum tokens per chunk
        flex_factor: Flexibility multiplier for hard limit
        
    Returns:
        List of chunks, where each chunk is a list of paragraphs/sentences
    """
    chunks, current, cur_tokens = [], [], 0
    hard_limit = int(max_tokens * flex_factor)

    for para in paragraphs:
        words = para.split()
        count = len(words)

        # 1. Paragraph fits comfortably
        if cur_tokens + count <= max_tokens:
            current.append(para)
            cur_tokens += count

        # 2. Paragraph alone fits within flex limit
        elif count <= hard_limit and cur_tokens == 0:
            chunks.append([para])
            cur_tokens = 0

        # 3. Paragraph too big – split into sentences
        else:
            if current:
                chunks.append(current)
                current, cur_tokens = [], 0

            if count > hard_limit:
                temp, temp_tokens = [], 0
                for sent in split_into_sentences(para):
                    toks = len(sent.split())
                    if temp_tokens + toks > max_tokens:
                        chunks.append(temp)
                        temp, temp_tokens = [sent], toks
                    else:
                        temp.append(sent)
                        temp_tokens += toks
                if temp:
                    chunks.append(temp)
            else:
                current = [para]
                cur_tokens = count

    if current:
        chunks.append(current)

    return chunks
