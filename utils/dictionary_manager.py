from config.dictionary import WORD_TO_COLOR
import random
import json
import unicodedata
import re

def normalize_text(text):
    return unicodedata.normalize("NFKC", text)

def scrub_text(text):
    normalized = unicodedata.normalize("NFKD", text)
    return ''.join(c for c in normalized if not unicodedata.combining(c))

def clean_input(text):
    return scrub_text(normalize_text(text))

def generate_unique_rgb():
    existing_colors = set(WORD_TO_COLOR.values())
    while True:
        rgb = tuple(random.randint(0, 255) for _ in range(3))
        if rgb not in existing_colors:
            return rgb

def expand_dictionary(text):
    tokens = re.findall(r'\n\n|\n|[ ]{2,}|[ ]|[\w]+|[^\w\s]', text)  # Align with text_to_image.py
    print(f"🔍 Tokens found: {tokens}")
    for token in tokens:
        if token not in WORD_TO_COLOR:
            rgb = generate_unique_rgb()
            WORD_TO_COLOR[token] = rgb
            print(f"🆕 Learned '{token}' → {rgb}")
    # Add single space and newline explicitly if not present
    if ' ' not in WORD_TO_COLOR:
        WORD_TO_COLOR[' '] = generate_unique_rgb()
        print(f"🆕 Learned ' ' → {WORD_TO_COLOR[' ']}")
    if '\n' not in WORD_TO_COLOR:
        WORD_TO_COLOR['\n'] = generate_unique_rgb()
        print(f"🆕 Learned '\\n' → {WORD_TO_COLOR['\n']}")
    if '\n\n' not in WORD_TO_COLOR:
        WORD_TO_COLOR['\n\n'] = generate_unique_rgb()
        print(f"🆕 Learned '\\n\\n' → {WORD_TO_COLOR['\n\n']}")
    save_dictionary()

def save_dictionary(path="config/dictionary.json"):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(WORD_TO_COLOR, f, indent=2)
    print(f"💾 Dictionary saved to {path}")