import json
from pathlib import Path

def save_json(table: json, path: str):
    '''
    Save table to json file
    '''
    Path(path).parent.mkdir(parents=True, exist_ok=True)  # ensure assets/{server} exists
    with open(path, "w", encoding="utf-8") as f:
        json.dump(table, f, ensure_ascii=False, indent=4)