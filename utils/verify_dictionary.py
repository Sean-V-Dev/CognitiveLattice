import json

def check_duplicates(dictionary_path="config/dictionary.json"):
    with open(dictionary_path, "r", encoding="utf-8") as f:
        raw_dict = json.load(f)
        rgb_values = [tuple(v) for v in raw_dict.values()]
        duplicates = set([rgb for rgb in rgb_values if rgb_values.count(rgb) > 1])
        if duplicates:
            print(f"⚠️ Duplicate RGB values found: {duplicates}")
        else:
            print("✅ No duplicate RGB values found.")

if __name__ == "__main__":
    check_duplicates()