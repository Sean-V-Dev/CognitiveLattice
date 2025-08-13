#!/usr/bin/env python3
"""
DOM Skeleton Utility
===================

Creates cl    # Remove empty elements that don't contribute meaning
    # But preserve structural containers and interactive elements
    interactive_tags = {
        'a', 'button', 'input', 'select', 'textarea', 'label', 'form',
        'img', 'svg', 'canvas'  # Visual elements that may be clickable
    }
    
    structural_tags = {
        'div', 'span', 'section', 'article', 'nav', 'header', 'footer', 'main',
        'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'thead', 'tbody',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'
    }

    # Remove empty elements that aren't interactive or don't have important attributes
    elements_to_remove = []
    for tag in soup.find_all(True):
        try:
            # Skip elements that might have None attrs or are non-standard elements
            if not hasattr(tag, 'attrs') or tag.attrs is None or not hasattr(tag, 'name'):
                continue
                
            # Check if element should be removed
            has_important_attrs = False
            try:
                has_important_attrs = any(tag.get(attr) for attr in ['id', 'class', 'data-testid'])
            except (AttributeError, TypeError):
                has_important_attrs = False
                
            if (tag.name not in interactive_tags and 
                tag.name not in structural_tags and
                not tag.get_text(strip=True) and 
                not has_important_attrs):
                elements_to_remove.append(tag)
        except Exception:
            # Skip problematic elements
            continue
    
    # Remove the identified elements
    for tag in elements_to_remove:
        try:
            tag.decompose()
        except Exception:
            continue

    # STEP 5: Limit nesting depth to prevent token explosion
    tags_to_remove = [
        'script', 'style', 'meta', 'link', 'noscript', 
        'iframe', 'embed', 'object', 'param',
        'head', 'title'  # Usually not needed for interaction
    ]
    
    for tag_name in tags_to_remove:
        for tag in soup.find_all(tag_name):
            tag.decompose()  # Completely removes tag and contents

    # STEP 2: Remove HTML comments
    from bs4 import Comment
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    # STEP 3: Clean up attributes - keep only the important ones
    important_attributes = {
        'id', 'class', 'name', 'type', 'value', 'href', 'src', 'alt',
        'placeholder', 'title', 'aria-label', 'aria-expanded', 'aria-selected',
        'role', 'tabindex', 'disabled', 'checked', 'selected',
        # Data attributes are often crucial for modern web apps
        'data-testid', 'data-cy', 'data-test', 'data-automation-id',
        'data-v-*'  # Vue.js data attributes like in Chipotle example
    }
    
    for tag in soup.find_all(True):
        # Get current attributes
        current_attrs = list(tag.attrs.keys()) if tag.attrs else []
        
        # Remove unwanted attributes
        for attr in current_attrs:
            keep_attr = False
            
            # Keep if in important list
            if attr in important_attributes:
                keep_attr = True
            
            # Keep data-* attributes (very important for modern sites)
            elif attr.startswith('data-'):
                keep_attr = True
                
            # Keep aria-* attributes (accessibility/state info)
            elif attr.startswith('aria-'):
                keep_attr = True
            
            # Remove if not important
            if not keep_attr:
                del tag[attr]

    # STEP 4: Remove empty elements that don't contribute meaning
    # But preserve structural containers and interactive elements
    interactive_tags = {
        'a', 'button', 'input', 'select', 'textarea', 'label', 'form',
        'img', 'svg', 'canvas'  # Visual elements that may be clickable
    }
    
    structural_tags = {
        'div', 'span', 'section', 'article', 'nav', 'header', 'footer', 'main',
        'ul', 'ol', 'li', 'table', 'tr', 'td', 'th', 'thead', 'tbody',
        'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p'
    }

    # STEP 5: Limit nesting depth to prevent token explosion
    def limit_depth(element, current_depth=0):
        if current_depth > max_depth:
            # Replace deep elements with a placeholder
            element.clear()
            element.append(soup.new_string(f"[...content truncated at depth {max_depth}...]"))
            return
        
        for child in element.find_all(True, recursive=False):
            limit_depth(child, current_depth + 1)
    
    if soup.body:
        limit_depth(soup.body)
    else:
        limit_depth(soup)

    # STEP 6: Clean up whitespace in text content but preserve structure
    for text_node in soup.find_all(string=True):
        if text_node.parent.name not in ['pre', 'code', 'textarea']:
            # Normalize whitespace but keep single spaces
            cleaned = re.sub(r'\s+', ' ', text_node.strip())
            if cleaned != text_node:
                text_node.replace_with(cleaned)

    # STEP 7: Generate the clean skeleton
    # Only return body content, skip html/body wrapper tags for token efficiency
    if soup.body:
        result = ''.join(str(child) for child in soup.body.children)
    else:
        result = str(soup)

    return result.strip()


def get_skeleton_stats(skeleton_html: str) -> dict:
    """
    Analyze the DOM skeleton to provide token count estimates and element statistics.
    
    Args:
        skeleton_html: The cleaned DOM skeleton
        
    Returns:
        Dictionary with statistics about the skeleton
    """
    # Rough token count estimation (1 token ≈ 4 characters for HTML)
    estimated_tokens = len(skeleton_html) // 4
    
    # Count different element types
    soup = BeautifulSoup(skeleton_html, 'html.parser')
    
    interactive_count = len(soup.find_all(['a', 'button', 'input', 'select', 'textarea', 'form']))
    structural_count = len(soup.find_all(['div', 'span', 'section', 'ul', 'li']))
    total_elements = len(soup.find_all(True))
    
    return {
        'estimated_tokens': estimated_tokens,
        'character_count': len(skeleton_html),
        'total_elements': total_elements,
        'interactive_elements': interactive_count,
        'structural_elements': structural_count,
        'compression_ratio': f"{len(skeleton_html) / max(len(skeleton_html), 1):.1%}" if skeleton_html else "0%"
    }


def extract_clickable_elements(skeleton_html: str) -> List[dict]:
    """
    Extract all clickable/interactive elements from the DOM skeleton with their selectors.
    
    Args:
        skeleton_html: The cleaned DOM skeleton
        
    Returns:
        List of dictionaries containing element information
    """
    soup = BeautifulSoup(skeleton_html, 'html.parser')
    clickable_elements = []
    
    # Interactive element types
    interactive_selectors = [
        'a[href]',           # Links
        'button',            # Buttons  
        'input[type="button"]', 'input[type="submit"]', 'input[type="reset"]',
        'input[type="checkbox"]', 'input[type="radio"]',
        'select',            # Dropdowns
        'textarea',          # Text areas
        'input[type="text"]', 'input[type="email"]', 'input[type="password"]',
        '[role="button"]',   # ARIA buttons
        '[onclick]',         # Elements with click handlers
        '[tabindex]'         # Focusable elements
    ]
    
    for selector in interactive_selectors:
        elements = soup.select(selector)
        for elem in elements:
            # Build selector for this element
            css_selector = _build_css_selector(elem)
            
            # Extract text content
            text_content = elem.get_text(strip=True)
            
            # Get important attributes
            attrs = {}
            for attr in ['id', 'class', 'type', 'name', 'placeholder', 'aria-label', 'title']:
                if elem.get(attr):
                    attrs[attr] = elem.get(attr)
            
            clickable_elements.append({
                'tag': elem.name,
                'selector': css_selector,
                'text': text_content,
                'attrs': attrs,
                'element_html': str(elem)[:200] + "..." if len(str(elem)) > 200 else str(elem)
            })
    
    return clickable_elements


def _build_css_selector(element) -> str:
    """Build a CSS selector for the given BeautifulSoup element."""
    selectors = []
    
    # Start with tag name
    selectors.append(element.name)
    
    # Add ID if present (most specific)
    if element.get('id'):
        return f"#{element.get('id')}"
    
    # Add classes if present
    if element.get('class'):
        classes = element.get('class')
        if isinstance(classes, list):
            class_str = '.'.join(classes)
        else:
            class_str = classes
        selectors.append(f".{class_str}")
    
    # Add attribute selectors for uniqueness
    for attr in ['name', 'type', 'data-testid']:
        if element.get(attr):
            selectors.append(f"[{attr}='{element.get(attr)}']")
            break  # One attribute selector is usually enough
    
    return ''.join(selectors) if len(selectors) > 1 else selectors[0]


# Test function to validate the skeleton creation
def test_dom_skeleton():
    """Test the DOM skeleton functionality with a sample HTML."""
    sample_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Test Page</title>
        <style>.hidden { display: none; }</style>
        <script>console.log('test');</script>
    </head>
    <body>
        <div class="find-a-chipotle-container">
            <div class="find-a-chipotle-container-button d-flex text-no-decoration color-brown">
                <div class="find-a-chipotle d-inline-flex align-center transition">
                    <div alt="Find A Chipotle" tabindex="-1" role="img" class="icon mr-10px">
                        <svg width="24" height="24.17" viewBox="0 0 24 24.17">
                            <path fill="currentColor" d="M12 0a7.875..."></path>
                        </svg>
                    </div>
                    <span tabindex="0" role="link" class="text findChipotle-text">Find A Chipotle</span>
                </div>
            </div>
        </div>
        <button class="order-btn" id="order-now">Order Now</button>
        <input type="text" placeholder="Enter ZIP code" name="zipcode">
    </body>
    </html>
    """
    
    print("🧪 Testing DOM Skeleton Creation")
    print("=" * 40)
    
    # Create skeleton
    skeleton = create_dom_skeleton(sample_html)
    print("📋 DOM Skeleton:")
    print(skeleton)
    print()
    
    # Get statistics
    stats = get_skeleton_stats(skeleton)
    print("📊 Skeleton Statistics:")
    for key, value in stats.items():
        print(f"  {key}: {value}")
    print()
    
    # Extract clickable elements
    clickables = extract_clickable_elements(skeleton)
    print("🖱️ Clickable Elements Found:")
    for i, elem in enumerate(clickables, 1):
        print(f"  {i}. {elem['tag']} - {elem['selector']}")
        print(f"     Text: '{elem['text']}'")
        print(f"     Attrs: {elem['attrs']}")
        print()


if __name__ == "__main__":
    test_dom_skeleton()
