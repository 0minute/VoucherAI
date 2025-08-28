from pathlib import Path

# === Root Path ===
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent  # project_root/ 기준

# === Top-level directories ===
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"
ARCHIVE_ROOT = PROJECT_ROOT / "archive"
DB_ROOT = WORKSPACE_ROOT / "central_db"

# === Default subfolder names ===
INPUT_FOLDER = "input_files"
INTERMEDIATE_FOLDER = "intermediate"
FINAL_OUTPUT_FOLDER = "final_output"
LOGS_FOLDER = "logs"
DB_FOLDER = "db"

# === Intermediate sub-subfolders ===
OCR_FOLDER = "ocr_results"
LLM_FOLDER = "llm_results"
JOURNAL_FOLDER = "journal_entries"
VISUALIZATION_FOLDER = "visualization"

# === Default file names ===
SETTING_FILE = "setting.json"
FINAL_XLSX = "journal_entries.xlsx"
FINAL_CSV = "journal_entries.csv"
VOUCHER_DATA_FILE = "voucher_data.json"
EDITS_LOG_FILE = "edits.log.jsonl"  # 선택
UPLOADS_INDEX_FILE = "uploads_index.json"
WS_CONFIG_FILE = "config.json"
# === Path Helpers ===

def get_central_db_path() -> Path:
    return DB_ROOT

def get_workspace_path(workspace_name: str) -> Path:
    return WORKSPACE_ROOT / workspace_name

def get_setting_file(workspace_name: str) -> Path:
    return get_workspace_path(workspace_name) / SETTING_FILE

def get_input_path(workspace_name: str) -> Path:
    return get_workspace_path(workspace_name) / INPUT_FOLDER

def get_intermediate_path(workspace_name: str) -> Path:
    return get_workspace_path(workspace_name) / INTERMEDIATE_FOLDER

def get_ocr_path(workspace_name: str) -> Path:
    return get_intermediate_path(workspace_name) / OCR_FOLDER

def get_llm_path(workspace_name: str) -> Path:
    return get_intermediate_path(workspace_name) / LLM_FOLDER

def get_visualization_path(workspace_name: str) -> Path:
    return get_intermediate_path(workspace_name) / VISUALIZATION_FOLDER

def get_journal_path(workspace_name: str) -> Path:
    return get_intermediate_path(workspace_name) / JOURNAL_FOLDER

def get_final_output_path(workspace_name: str) -> Path:
    return get_workspace_path(workspace_name) / FINAL_OUTPUT_FOLDER

def get_logs_path(workspace_name: str) -> Path:
    return get_workspace_path(workspace_name) / LOGS_FOLDER

def get_final_xlsx(workspace_name: str) -> Path:
    return get_final_output_path(workspace_name) / FINAL_XLSX

def get_final_csv(workspace_name: str) -> Path:
    return get_final_output_path(workspace_name) / FINAL_CSV

def get_db_dir(workspace_name: str) -> Path:
    return get_workspace_path(workspace_name) / DB_FOLDER

# def get_voucher_data_path(workspace_name: str) -> Path:
#     return get_db_dir(workspace_name) / VOUCHER_DATA_FILE

def get_edits_log_path(workspace_name: str) -> Path:
    return get_db_dir(workspace_name) / EDITS_LOG_FILE

def get_uploads_index_path(workspace_name: str) -> Path:
    return get_db_dir(workspace_name) / UPLOADS_INDEX_FILE

def get_workspace_config_path(workspace_name: str) -> Path:
    return DB_ROOT / WS_CONFIG_FILE

def get_voucher_db_path(workspace_name: str) -> Path:
    return get_db_dir(workspace_name) / VOUCHER_DATA_FILE

DEFAULT_ALLOWED_EXT = (".png",".jpg",".jpeg")


