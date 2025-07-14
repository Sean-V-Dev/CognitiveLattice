import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from utils.dictionary_manager import expand_dictionary, clean_input


from encoder.text_to_image import encode_text_to_image
from decoder.image_to_text import decode_image_to_text
from config.dictionary import WORD_TO_COLOR
import difflib
import os

def stress_test(text_inputs, image_dir="stress_images", decoded_dir="stress_decoded"):
    os.makedirs(image_dir, exist_ok=True)
    os.makedirs(decoded_dir, exist_ok=True)

    for idx, input_text in enumerate(text_inputs):
        img_path = f"{image_dir}/chunk_{idx}.png"
        decoded_path = f"{decoded_dir}/decoded_{idx}.txt"
        cleaned = clean_input(input_text)

        expand_dictionary(cleaned)


        # Encode
        encode_text_to_image(cleaned, img_path)
        # decode
        decode_image_to_text(img_path, decoded_path)

        # Fidelity check
        with open(decoded_path, encoding="utf-8") as f:
            decoded = f.read().strip()

        original_words = cleaned.split()
        decoded_words = decoded.split()
        match_ratio = difflib.SequenceMatcher(None, original_words, decoded_words).ratio()

        print(f"\n🧠 Chunk {idx}")
        print(f"Original: {input_text}")
        print(f"Decoded : {decoded}")
        print(f"✅ Fidelity: {round(match_ratio*100, 2)}%")

        if match_ratio < 0.9:
            missing = set(original_words) - set(decoded_words)
            print(f"🚨 Missing words: {missing}")

if __name__ == "__main__":
    inputs = [
        "Install firmware into unit seven then reboot for diagnostics.",
        "Quantum node Alpha-7 failed to emit entangled signal.",
        "Characters like Zephyrus and Nyx aren’t in standard dictionaries."
    ]
    stress_test(inputs)
      