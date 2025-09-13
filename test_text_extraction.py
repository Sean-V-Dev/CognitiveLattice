from bs4 import BeautifulSoup
import re

# Test the improved logic
def _norm_text(t: str) -> str:
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
        has_price_markers = any(marker in text for marker in ['$', '£', '€', '¥', 'cal', 'kcal'])
        if clean_ratio > 0.7 and not has_price_markers:
            return text
    
    # PRIORITY 3: Try to extract first meaningful part
    if text and len(text.strip()) > 50:
        first_part = text.split('.')[0].split('$')[0].split('\n')[0].strip()
        if 2 <= len(first_part) <= 30:
            return _norm_text(first_part)
    
    # PRIORITY 4: For messy text without data attributes, try to extract the first few words
    if text and len(text.strip()) > 20:  # Lower threshold
        # Look for the first 1-3 words that look like menu items
        words = text.split()
        if len(words) >= 2:
            # Try combinations of first few words
            for word_count in [2, 3, 1]:
                if word_count <= len(words):
                    candidate = ' '.join(words[:word_count])
                    # Check if this looks like a reasonable menu item name
                    if (2 <= len(candidate) <= 30 and 
                        not any(char in candidate for char in ['$', '℃', '%', 'cal']) and
                        not candidate.lower().startswith(('add', 'build', 'custom', 'order'))):
                        return _norm_text(candidate)
    
    return text if text else ''

# Test cases
test_cases = [
    # Case 1: Complex Chipotle container with data attribute
    '<div data-qa-item-name="Chicken">Chicken$2.00Responsibly raised220 calAdd</div>',
    # Case 2: Simple clean text
    '<button>Order Now</button>',
    # Case 3: Complex but no data attributes  
    '<div>Chicken Bowl $12.99 Build your own Customize</div>',
    # Case 4: Bowl selection (successful case)
    '<div class="top-level-menu">Burrito BowlOrder</div>'
]

for html in test_cases:
    soup = BeautifulSoup(html, 'html.parser')
    elem = soup.find()
    attrs = {k.lower(): v for k, v in (elem.attrs or {}).items()}
    
    raw_text = elem.get_text(strip=True)
    result = _extract_meaningful_text(raw_text, attrs)
    
    print(f'HTML: {html}')
    print(f'Raw text: {repr(raw_text)}')
    print(f'Extracted: {repr(result)}')
    print('---')
