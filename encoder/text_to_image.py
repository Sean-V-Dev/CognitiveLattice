from PIL import Image
import math
import re
import json
from config.dictionary import WORD_TO_COLOR, COLOR_TO_WORD
from utils.dictionary_manager import expand_dictionary

def tokenize_text(text):
    # Match double newlines, single newlines, indentation (2+ spaces), words, punctuation
    return re.findall(r'\n\n|\n|[ ]{2,}|[ ]|[\w]+|[^\w\s]', text)

def normalize_token(token):
    # Separate trailing punctuation from the word
    match = re.match(r'^(\w+)([^\w]*)$', token)
    if match:
        core, punct = match.groups()
        tokens = [core]
        if punct:
            tokens.append(punct)
        return tokens
    return [token]

def encode_text_to_image(text, output_path, encryption_key=None):
    
    expand_dictionary(text)  # Ensure dictionary is updated  
    tokens = tokenize_text(text)
    pixels = []

    if encryption_key is None:
            with open("config/key.json", "r") as f:
                encryption_key = tuple(json.load(f)["encryption_key"])


    for token in tokens:
        for sub_token in normalize_token(token):
            if sub_token in WORD_TO_COLOR:
                pixels.append(WORD_TO_COLOR[sub_token])
            else:
                print(f"⚠️ Token not in dictionary: '{sub_token}'")
                pixels.append((255, 0, 0))

    # Compute image dimensions
    width = math.ceil(math.sqrt(len(pixels)))
    height = math.ceil(len(pixels) / width)
    image = Image.new("RGB", (width, height), color=(30, 30, 30))

    # Fill in pixel data
    for i, pixel in enumerate(pixels):
        x = i % width
        y = i // width
        image.putpixel((x, y), pixel)

    image.save(output_path)
    print(f"✅ Encoded image saved to {output_path}")