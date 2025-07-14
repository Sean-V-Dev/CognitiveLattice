import json

with open("config/dictionary.json", "r", encoding="utf-8") as f:
    raw_dict = json.load(f)
    WORD_TO_COLOR = {k: tuple(v) for k, v in raw_dict.items()}


COLOR_TO_WORD = {v: k for k, v in WORD_TO_COLOR.items()}
