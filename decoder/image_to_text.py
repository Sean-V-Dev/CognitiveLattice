from PIL import Image
from config.dictionary import COLOR_TO_WORD
import numpy as np
import json

def decode_image_to_text(image_path, output_path="decoded.txt", encryption_key=None):
    image = Image.open(image_path).convert("RGB")
    pixels = np.array(image)
    background_color = (30, 30, 30)  # Default background color

    lines = []
    current_line = []
    
    if encryption_key is None:
        with open("config/key.json", "r") as f:
            encryption_key = tuple(json.load(f)["encryption_key"])
    
    for row in pixels:
        for pixel in row:
            color = tuple(pixel[:3])
            if color == background_color:
                continue
            
            decrypted_color = (
                color[0] ^ encryption_key[0],
                color[1] ^ encryption_key[1],
                color[2] ^ encryption_key[2]
            )
            if color in COLOR_TO_WORD:
                word = COLOR_TO_WORD[color]
                if word == '\n':  
                    lines.append("".join(current_line))
                    current_line = []
                elif word == '\n\n':  
                    lines.append("".join(current_line))
                    lines.append("")  
                    current_line = []
                else:
                    current_line.append(word)  
            else:
                print(f"⚠️ Color not in dictionary: {decrypted_color}")
                # Skip missing colors entirely

    # Add the last line if any
    if current_line:
        lines.append("".join(current_line))

    # Join lines, preserving empty lines for double newlines
    decoded_text = "\n".join(lines).rstrip()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(decoded_text)

    print(f"✅ Decoded text saved to {output_path}")