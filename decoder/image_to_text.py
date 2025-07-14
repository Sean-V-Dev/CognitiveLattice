from PIL import Image
from config.dictionary import COLOR_TO_WORD
import numpy as np

def decode_image_to_text(image_path, output_path="decoded.txt"):
    image = Image.open(image_path).convert("RGB")
    pixels = np.array(image)
    background_color = (30, 30, 30)  # Default background color

    lines = []
    current_line = []
    for row in pixels:
        for pixel in row:
            color = tuple(pixel[:3])
            if color == background_color:
                continue  # Skip background pixels
            if color in COLOR_TO_WORD:
                word = COLOR_TO_WORD[color]
                if word == '\n':  # Handle single newline
                    lines.append("".join(current_line))
                    current_line = []
                elif word == '\n\n':  # Handle double newline
                    lines.append("".join(current_line))
                    lines.append("")  # Add empty line for \n\n
                    current_line = []
                else:
                    current_line.append(word)  # Preserve spaces, indentation, etc.
            else:
                print(f"⚠️ Color not in dictionary: {color}")
                # Skip missing colors entirely

    # Add the last line if any
    if current_line:
        lines.append("".join(current_line))

    # Join lines, preserving empty lines for double newlines
    decoded_text = "\n".join(lines).rstrip()

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(decoded_text)

    print(f"✅ Decoded text saved to {output_path}")