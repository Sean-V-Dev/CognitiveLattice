# Standard library
import os
import difflib
import json
import sys
import tempfile
import requests

# Third-party libraries
import pdfplumber

# Local modules
from utils.dictionary_manager import expand_dictionary, clean_input
from encoder.text_to_image import encode_text_to_image
from decoder.image_to_text import decode_image_to_text

# === Simulated Long-Term Memory ===#
memory = {}

# === Utility to chunk the task list ===#
def chunk_list(items, chunk_size):
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

# === File Reading Utilities ====#
def read_txt_file(file_path):
    encodings = ['utf-8', 'windows-1252', 'utf-8-sig']
    for encoding in encodings:
        try:
            with open(file_path, 'r', encoding=encoding) as f:
                lines = [line.strip() for line in f if line.strip()]
            print(f"📄 Successfully read {file_path} with encoding: {encoding}")
            return lines
        except UnicodeDecodeError:
            print(f"⚠️ Failed with encoding: {encoding}")
    with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = [line.strip() for line in f if line.strip()]
    print(f"⚠️ Fallback read {file_path} with ignored errors")
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
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

def process_file(file_path):
    if file_path.endswith(".pdf"):
        sanitize_pdf(file_path, "cleaned_input.txt")
        return read_txt_file("cleaned_input.txt")
    elif file_path.endswith(".txt"):
        return read_txt_file(file_path)
    else:
        raise ValueError("Unsupported file format. Use .txt or .pdf")

# === LLaMA Inference Wrapper (HTTP version) ===#
def run_llama_inference(prompt):
    print("🔧 Sending prompt to llama-server...")
    try:
        response = requests.post(
            "http://localhost:8080/completion",
            headers={"Content-Type": "application/json"},
            json={
                "prompt": prompt,
                "n_predict": 256,
                "temperature": 0.7,
                "top_p": 0.95,
                "repeat_penalty": 1.1,
                "stream": False
            },
            timeout=120
        )
        response.raise_for_status()
        data = response.json()
        print("✅ LLaMA output:")
        print(data['content'])
        return data['content'].strip()
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        return "CONFUSED"

# === GPT-powered summarizer replacement with LLaMA ====#
def summarize_chunk(chunk):
    prompt = f"[INST] Read the following and summarize what you have read to the best of your ability:\n{', '.join(chunk)} [/INST]"
    return run_llama_inference(prompt)

# === Main processing function ====#
def process_chunk(chunk, chunk_id):
    print(f"\n🤪 Processing Chunk {chunk_id}: {chunk}")

    if any("confusing" in item.lower() for item in chunk):
        print("❗ Agent is confused. Attempting to recall memory for help...")
        recalled_context = " ".join(list(memory.values())[-2:])
        prompt = f"You are confused by this new chunk:\n{', '.join(chunk)}\n\nHere’s what you remember:\n{recalled_context}\n\nTry to understand it now."
        reply = run_llama_inference(prompt)
        print("✅ Memory-assisted reply:", reply)
        memory[chunk_id] = reply
        return

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
        print(f"\n🗎️ Found {len(results)} matching chunks:")
        for chunk_id, text in results:
            print(f"{chunk_id}: {text[:120]}{'...' if len(text) > 120 else ''}")
    else:
        print("🚛 No relevant memory found.")

with open("config/key.json", "r") as f:
    config = json.load(f)
    encryption_key = tuple(config["encryption_key"])


# === Ensure decoded.txt exists or create it ===#
decoded_path = "decoded.txt"
source_input = "chapter1.txt"  # or the original raw input

if not os.path.exists(decoded_path):
    print("🕒 decoded.txt not found. Running full encode-decode pipeline...")

    raw_lines = process_file(source_input)
    text = "\n".join(raw_lines)
    cleaned = clean_input(text)

    expand_dictionary(cleaned)
    img_path = "cache/decode_once.png"
    os.makedirs("cache", exist_ok=True)

    encode_text_to_image(cleaned, img_path, encryption_key)
    decode_image_to_text(img_path, decoded_path, encryption_key)

    print(f"✅ decoded.txt generated at: {decoded_path}")
else:
    print("🔁 Using existing decoded.txt")

# === Load content from decoded file ===#
tasks = process_file(decoded_path)
if not tasks:
    raise ValueError("No tasks found in file.")

# === Chunk and process ====#
chunks = chunk_list(tasks, chunk_size=30)

output_img_dir = "encoded_chunks"
output_txt_dir = "decoded_chunks"
os.makedirs(output_img_dir, exist_ok=True)
os.makedirs(output_txt_dir, exist_ok=True)



for i, chunk in enumerate(chunks):
    chunk_id = f"chunk_{i+1}"
    text = "\n".join(chunk)
    cleaned = clean_input(text)
    expand_dictionary(cleaned)
    img_path = os.path.join(output_img_dir, f"{chunk_id}.png")
    encode_text_to_image(cleaned, img_path, encryption_key)
    decoded_path = os.path.join(output_txt_dir, f"{chunk_id}.txt")
    decode_image_to_text(img_path, decoded_path, encryption_key)
    with open(decoded_path, encoding="utf-8") as f:
        decoded = f.read().strip()
    match_ratio = difflib.SequenceMatcher(None, cleaned, decoded).ratio()
    print(f"\n🤪 Chunk {chunk_id}")
    print(f"Decoded: {decoded}")
    print(f"✅ Fidelity: {round(match_ratio*100, 2)}%")
    if match_ratio < 0.9:
        differ = difflib.Differ()
        diff = list(differ.compare(cleaned.splitlines(), decoded.splitlines()))
        print(f"🚨 Differences:\n{' '.join(diff)}")
    process_chunk(chunk, chunk_id)

# === Show memory log ====#
print("\n🤪 Final Memory Log:")
for key, val in memory.items():
    print(f"{key}:\n{val}\n")


# === Example Search ====#
search_memory("quantum")
