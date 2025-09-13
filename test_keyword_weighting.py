# Test the new weighted keyword scoring
goal = "Select the 'Build Your Own' option for a bowl"
goal_lower = goal.lower()
goal_words = goal_lower.split()

print(f'Goal: "{goal}"')
print(f'Goal words: {goal_words}')

# Skip words and action words
skip_words = {'the', 'a', 'an', 'to', 'for', 'of', 'in', 'on', 'at', 'by', 'with', 'from', 'up', 'about', 'into', 'through', 'during', 'before', 'after', 'above', 'below', 'over', 'under', 'between', 'among', 'through', 'during', 'before', 'after', 'above', 'below', 'is', 'are', 'was', 'were', 'be', 'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'must', 'shall', 'and', 'or', 'but', 'nor', 'so', 'yet', 'as', 'if', 'then', 'than', 'when', 'where', 'while', 'how', 'why', 'what', 'which', 'who', 'whom', 'whose', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my', 'your', 'his', 'her', 'its', 'our', 'their', 'mine', 'yours', 'his', 'hers', 'ours', 'theirs', 'myself', 'yourself', 'himself', 'herself', 'itself', 'ourselves', 'yourselves', 'themselves'}

action_words = {'select', 'choose', 'pick', 'click', 'build', 'your', 'own', 'option', 'as', 'type', 'order', 'get', 'go', 'find', 'then', 'me'}

# Separate keywords
target_keywords = []  
general_keywords = []  

for word in goal_words:
    clean_word = word.strip('.,!?;:"()[]{}').lower()
    if len(clean_word) >= 2 and clean_word not in skip_words:
        if clean_word in action_words:
            general_keywords.append(clean_word)
        else:
            target_keywords.append(clean_word)

print(f'Target keywords (high value): {target_keywords}')
print(f'General keywords (low value): {general_keywords}')

# Test elements
elements = [
    ("Build Your Own", {'class': 'display-name mealBuild'}),
    ("Burrito Bowl", {'class': 'top-level-menu', 'data-qa-group-name': 'Burrito Bowl'}),
    ("Lifestyle Bowl", {'class': 'top-level-menu'})
]

print('\n--- Element Scoring ---')
for text, attrs in elements:
    text_lower = text.lower()
    
    # Count matches
    target_matches = sum(1 for kw in target_keywords if kw in text_lower)
    general_matches = sum(1 for kw in general_keywords if kw in text_lower)
    
    # Calculate boost
    total_boost = 0
    if target_matches > 0:
        target_boost = target_matches * 3.0
        total_boost += target_boost
        
    if general_matches > 0:
        general_boost = general_matches * 0.5
        total_boost += general_boost
    
    # Check for high-value attributes
    high_value_attrs = ['data-qa-group-name', 'data-menu-item', 'data-item-name', 'data-testid', 'data-track']
    has_high_value_attr = any(attr_name in attrs for attr_name in high_value_attrs)
    
    final_boost = total_boost * 3.0 if has_high_value_attr else total_boost
    
    print(f'"{text}":')
    print(f'  Target matches: {target_matches} (+{target_matches * 3.0:.1f})')
    print(f'  General matches: {general_matches} (+{general_matches * 0.5:.1f})')
    print(f'  High-value attrs: {has_high_value_attr}')
    print(f'  Final boost: +{final_boost:.1f}')
    print()
