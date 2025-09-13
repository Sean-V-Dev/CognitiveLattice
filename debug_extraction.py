def _norm_text(t: str) -> str:
    import re
    t = re.sub(r'\s+', ' ', (t or '')).strip()
    return t[:80]

def _extract_meaningful_text(raw_text: str, attrs: dict) -> str:
    # PRIORITY 1: Try data attributes first
    data_attrs_to_check = [
        'data-qa-item-name', 'data-qa-group-name', 'data-qa-name',
        'data-item-name', 'data-label', 'data-title', 'data-name'
    ]
    
    for attr_name in data_attrs_to_check:
        if attr_name in attrs and attrs[attr_name]:
            extracted = str(attrs[attr_name]).strip()
            if extracted and len(extracted) > 1:
                return _norm_text(extracted)
    
    # PRIORITY 2: If raw text is short and clean, use it
    text = _norm_text(raw_text)
    if text and len(text.strip()) >= 2 and len(text.strip()) <= 50:
        clean_ratio = len([c for c in text if c.isalnum() or c.isspace()]) / len(text)
        if clean_ratio > 0.7:
            return text
    
    # PRIORITY 3: Try to extract first meaningful part
    if text and len(text.strip()) > 50:
        first_part = text.split('.')[0].split('$')[0].split('\n')[0].strip()
        if 2 <= len(first_part) <= 30:
            return _norm_text(first_part)
    
    # PRIORITY 4: For messy text without data attributes, try to extract the first few words
    if text and len(text.strip()) > 20:
        print(f'DEBUG: Analyzing text: "{text}" (length {len(text)})')
        # Look for the first 1-3 words that look like menu items
        words = text.split()
        print(f'DEBUG: Words: {words}')
        if len(words) >= 2:
            # Try combinations of first few words
            for word_count in [2, 3, 1]:
                if word_count <= len(words):
                    candidate = ' '.join(words[:word_count])
                    has_bad_chars = any(char in candidate for char in ['$', '℃', '%', 'cal'])
                    starts_with_bad = candidate.lower().startswith(('add', 'build', 'custom', 'order'))
                    print(f'DEBUG: {word_count} words "{candidate}" - bad_chars={has_bad_chars}, bad_start={starts_with_bad}')
                    # Check if this looks like a reasonable menu item name
                    if (2 <= len(candidate) <= 30 and 
                        not has_bad_chars and
                        not starts_with_bad):
                        print(f'DEBUG: SELECTING: "{candidate}"')
                        return _norm_text(candidate)
    
    return text if text else ''

# Test problematic case
text = 'Chicken Bowl $12.99 Build your own Customize'
result = _extract_meaningful_text(text, {})
print(f'Final result: "{result}"')
