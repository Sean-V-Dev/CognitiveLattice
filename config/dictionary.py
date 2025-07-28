import json
import os

base_dir = os.path.dirname(os.path.abspath(__file__))
dict_path = os.path.join(base_dir, "dictionary.json")

with open(dict_path, "r", encoding="utf-8") as f:
    raw_dict = json.load(f)
    WORD_TO_COLOR = {k: tuple(v) for k, v in raw_dict.items()}


COLOR_TO_WORD = {v: k for k, v in WORD_TO_COLOR.items()}
