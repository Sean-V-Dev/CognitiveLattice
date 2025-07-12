from PIL import Image
import math
import hashlib

# === Build a dictionary that maps each word to a unique RGB value ===
def build_word_color_dict(words):
    word_to_rgb = {}
    for word in words:
        hash_digest = hashlib.md5(word.encode()).hexdigest()
        rgb = tuple(int(hash_digest[i:i+2], 16) for i in (0, 2, 4))
        word_to_rgb[word] = rgb
    return word_to_rgb

# === Encode a list of words into an image ===
def encode_text_to_image(text, output_path):
    words = text.split()
    word_to_rgb = build_word_color_dict(set(words))
    pixels = [word_to_rgb[word] for word in words]

    # Compute image dimensions
    width = math.ceil(math.sqrt(len(pixels)))
    height = math.ceil(len(pixels) / width)
    image = Image.new("RGB", (width, height), color=(255, 255, 255))

    # Fill in pixel data
    for i, pixel in enumerate(pixels):
        x = i % width
        y = i // width
        image.putpixel((x, y), pixel)

    image.save(output_path)
    print(f"✅ Encoded image saved to {output_path}")

# === Example usage ===
if __name__ == "__main__":
    sample_text = "Task 1: Research LLMs Task 2: Understand token compression Task 3: Plan encoding"
    encode_text_to_image(sample_text, "encoded_output.png")
