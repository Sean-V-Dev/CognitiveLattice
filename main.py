# Standard library
import os
import difflib

# Third-party libraries
import openai
import pdfplumber
from dotenv import load_dotenv


# Local modules
from utils.dictionary_manager import expand_dictionary, clean_input
from encoder.text_to_image import encode_text_to_image
from decoder.image_to_text import decode_image_to_text

# === Load environment variables === #
load_dotenv()
api_key = os.getenv("OPENAI_API_KEY")
openai.api_key = api_key

# === Simulated Long-Term Memory ===#
memory = {}

# === Utility to chunk the task list ===#
def chunk_list(items, chunk_size):
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

# === File Reading Utilities ====#
def read_txt_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines

def read_pdf_file(file_path):
    lines = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend([line.strip() for line in text.split('\n') if line.strip()])
    return lines

def sanitize_pdf(file_path, output_path="cleaned_input.txt"):
    lines = []
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                lines.extend([line.strip() for line in text.split('\n') if line.strip()])
    cleaned_text = "\n".join(lines)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(cleaned_text)

def process_file(file_path):
    if file_path.endswith(".pdf"):
        sanitize_pdf(file_path, "cleaned_input.txt")
        return read_txt_file("cleaned_input.txt")
    elif file_path.endswith(".txt"):
        return read_txt_file(file_path)
    else:
        raise ValueError("Unsupported file format. Use .txt or .pdf")

# === GPT-powered summarizer ====#
def summarize_chunk(chunk):
    prompt = f"Summarize these tasks in 1-2 sentences:\n{', '.join(chunk)}"

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant summarizing task batches."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.4
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print("⚠️ GPT Error:", e)
        return "CONFUSED"

# === Main processing function ====#
def process_chunk(chunk, chunk_id):
    print(f"\n🧠 Processing Chunk {chunk_id}: {chunk}")

    # Simulate confusion trigger=#
    if any("confusing" in item.lower() for item in chunk):
        print("❗ Agent is confused. Attempting to recall memory for help...")

        # Try recalling previous memory=#
        recalled_context = " ".join(list(memory.values())[-2:])
        prompt = f"You are confused by this new chunk:\n{', '.join(chunk)}\n\nHere’s what you remember:\n{recalled_context}\n\nTry to understand it now."

        try:
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You use past memory to help understand new confusing input."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.4
            )
            reply = response['choices'][0]['message']['content']
            print("✅ Memory-assisted reply:", reply)
            memory[chunk_id] = reply
            return
        except Exception as e:
            print("⚠️ Recall Error:", e)
            print("☕ Taking a break with haiku...\nStill mind wandering\nConfusion meets reflection\nResume with fresh eyes\n")
            return

    # Normal summarization=#
    summary = summarize_chunk(chunk)
    memory[chunk_id] = summary
    print(f"✅ Summary stored in memory.")

# === Keyword-based Memory Search ====#
def search_memory(keyword):
    print(f"\n🔍 Searching for: '{keyword}'")
    results = []
    for chunk_id, summary in memory.items():
        if keyword.lower() in summary.lower():
            results.append((chunk_id, summary))

    if results:
        print(f"\n🔎 Found {len(results)} matching chunks:")
        for chunk_id, text in results:
            print(f"{chunk_id}: {text[:120]}{'...' if len(text) > 120 else ''}")
    else:
        print("🚫 No relevant memory found.")

# === Load content from file ====#
file_path = "example.pdf"
tasks = process_file(file_path)
if not tasks:
    raise ValueError("No tasks found in file.")

# === Chunk and process ====#
chunks = chunk_list(tasks, chunk_size=5)

output_img_dir = "encoded_chunks"
output_txt_dir = "decoded_chunks"
os.makedirs(output_img_dir, exist_ok=True)
os.makedirs(output_txt_dir, exist_ok=True)

for i, chunk in enumerate(chunks):
    chunk_id = f"chunk_{i+1}"
    text = "\n".join(chunk)
    cleaned = clean_input(text)

    # 🔍 Semantic expansion
    expand_dictionary(cleaned)

    # 🖼️ Encode
    img_path = f"{output_img_dir}/{chunk_id}.png"
    encode_text_to_image(cleaned, img_path)

    # 📄 Decode
    decoded_path = f"{output_txt_dir}/{chunk_id}.txt"
    decode_image_to_text(img_path, decoded_path)

    # 📊 Fidelity check
    with open(decoded_path, encoding="utf-8") as f:
        decoded = f.read().strip()
    match_ratio = difflib.SequenceMatcher(None, cleaned.split(), decoded.split()).ratio()

    print(f"\n🧠 Chunk {chunk_id}")
    print(f"Decoded : {decoded}")
    print(f"✅ Fidelity: {round(match_ratio*100, 2)}%")

    if match_ratio < 0.9:
        missing = set(cleaned.split()) - set(decoded.split())
        print(f"🚨 Missing words: {missing}")

    # 🤖 GPT summary as usual
    process_chunk(chunk, chunk_id)

# === Show memory log ====#
print("\n🧠 Final Memory Log:")
for key, val in memory.items():
    print(f"{key}: {val[:80]}{'...' if len(val) > 80 else ''}")

# === Example Search ====#
search_memory("quantum")

# === Move this later ==== move to before the chunk process on line 107 to match actual pipeline behavior=#

with open("example.txt", "r", encoding="utf-8") as f:
    raw_text = f.read()
encode_text_to_image(raw_text, output_path="encoded.png")

#testing the decoder=#

from decoder.image_to_text import decode_image_to_text

decode_image_to_text("encoded.png", "decoded.txt")





