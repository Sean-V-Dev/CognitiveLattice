from PIL import Image
from config.dictionary import COLOR_TO_WORD
import numpy as np
import json
import os
import time

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

    # Ensure output directory exists and normalize path
    output_path = os.path.normpath(os.path.abspath(output_path))
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # Try to save with retry mechanism for Windows file locking issues
    max_retries = 3
    for attempt in range(max_retries):
        try:
            # If file exists, try to remove it first (Windows file locking)
            if os.path.exists(output_path):
                try:
                    os.remove(output_path)
                except PermissionError:
                    # File is locked, wait a moment
                    time.sleep(0.1)
            
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(decoded_text)
            
            print(f"✅ Decoded text saved to {output_path}")
            break
        except (OSError, PermissionError) as e:
            if attempt < max_retries - 1:
                print(f"⚠️ Attempt {attempt + 1} failed, retrying in 0.5s: {e}")
                time.sleep(0.5)
            else:
                print(f"❌ Failed to save decoded text after {max_retries} attempts: {e}")
                print(f"   Output path: {output_path}")
                print(f"   Directory exists: {os.path.exists(os.path.dirname(output_path))}")
                print(f"   Path length: {len(output_path)}")
                raise