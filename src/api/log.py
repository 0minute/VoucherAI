from datetime import datetime
from src.api.constants import *
import json

def append_edit_log(workspace_name: str, action: str, payload: dict) -> None:
    logp = get_edits_log_path(workspace_name)
    logp.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "ts": datetime.utcnow().isoformat() + "Z",
        "action": action,          # e.g., "add", "update", "delete"
        "payload": payload         # diff or row id
    }
    with open(logp, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n