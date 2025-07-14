import openai
import os
from PyPDF2 import PdfReader

openai.api_key = "Your API key here"

# === Simulated Long-Term Memory ===
memory = {}

# === Utility to chunk the task list ===
def chunk_list(items, chunk_size):
    return [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

# === File Reading Utilities ===
def read_txt_file(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        lines = [line.strip() for line in f if line.strip()]
    return lines

def read_pdf_file(file_path):
    reader = PdfReader(file_path)
    lines = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            lines.extend([line.strip() for line in text.split('\n') if line.strip()])
    return lines

# === GPT-powered summarizer ===
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

# === Main processing function ===
def process_chunk(chunk, chunk_id):
    print(f"\n🧠 Processing Chunk {chunk_id}: {chunk}")

    # Simulate confusion trigger
    if any("confusing" in item.lower() for item in chunk):
        print("❗ Agent is confused. Attempting to recall memory for help...")

        # Try recalling previous memory
        recalled_context = " ".join(list(memory.values())[-2:])  # Last 2 memory chunks
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

    # Normal summarization
    summary = summarize_chunk(chunk)
    memory[chunk_id] = summary
    print(f"✅ Summary stored in memory.")

# === Keyword-based Memory Search ===
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

# === Load content from file ===
file_path = "example.txt"  # Change this to a .pdf for testing
if file_path.endswith(".txt"):
    tasks = read_txt_file(file_path)
elif file_path.endswith(".pdf"):
    tasks = read_pdf_file(file_path)
else:
    raise ValueError("Unsupported file format. Use .txt or .pdf")

# === Chunk and process ===
chunks = chunk_list(tasks, chunk_size=5)

for i, chunk in enumerate(chunks):
    chunk_id = f"chunk_{i+1}"
    process_chunk(chunk, chunk_id)

# === Show memory log ===
print("\n🧠 Final Memory Log:")
for key, val in memory.items():
    print(f"{key}: {val[:80]}{'...' if len(val) > 80 else ''}")

# === Example Search ===
search_memory("quantum")
