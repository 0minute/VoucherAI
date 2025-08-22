import os
DATA_DIR = "data"
EXTRACTED_JSON_DIR = os.path.join(DATA_DIR, "extracted_json")
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
LLM_MODEL_NAME = "gpt4o_latest"
OVERLAY_DIR = os.path.join(DATA_DIR, "overlay")
THUMBNAIL_DIR = os.path.join(DATA_DIR, "thumbnails")
VENDOR_TABLE_PATH = os.path.join(DATA_DIR, "vendor_table.json")