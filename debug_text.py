text = 'Chicken Bowl$12.99Build your ownCustomize'
print('Length:', len(text))
print('Words:', text.split())
print('Has $ sign:', '$' in text)

words = text.split()
for word_count in [2, 3, 1]:
    if word_count <= len(words):
        candidate = ' '.join(words[:word_count])
        has_bad_chars = any(char in candidate for char in ['$', '℃', '%', 'cal'])
        starts_with_bad = candidate.lower().startswith(('add', 'build', 'custom', 'order'))
        print(f'{word_count} words: "{candidate}" - bad_chars={has_bad_chars}, bad_start={starts_with_bad}')
        
        if (2 <= len(candidate) <= 30 and 
            not has_bad_chars and
            not starts_with_bad):
            print(f'  -> WOULD SELECT: "{candidate}"')
