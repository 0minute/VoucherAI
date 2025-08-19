import json

def read_json(data:[str,dict]):
    if isinstance(data, str):
        with open(data, "r", encoding="utf-8") as f:
            return json.load(f)
    elif isinstance(data, dict):
        return data
    else:
        raise ValueError("data must be a string or a dictionary")

def save_json(data:dict, path:str):
        