from src.api.constants import *
import json
import tempfile
import os
from src.api.utils import _atomic_write_json, _now_iso, _read_json

def read_voucher_data(workspace_name: str) -> dict:
    p = get_voucher_data_path(workspace_name)
    if not p.exists():
        return {"schema_version": 1, "updated_at": None, "entries": []}
    return json.loads(p.read_text(encoding="utf-8"))

def write_voucher_data(workspace_name: str, data: dict) -> None:
    """
    temp 파일에 쓰고 os.replace로 원자적 교체 → 부분쓰기/충돌 시 손상 방지
    """
    tgt = get_voucher_data_path(workspace_name)
    tgt.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", delete=False, dir=tgt.parent, encoding="utf-8") as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = tmp.name
    os.replace(tmp_path, tgt)  # atomic on POSIX/Windows(>=Py3.3)

class VoucherData:
    def __init__(self, workspace_name: str):
        self.workspace_name = workspace_name
        self.data = read_voucher_data(workspace_name)

    def get_data(self) -> dict:
        return self.data

    def set_data(self, data: dict) -> None:

# constant.py (추가)
def load_workspace_config(workspace_name: str) -> dict:
    """워크스페이스 config.json 없으면 기본 템플릿 생성."""
    p = get_workspace_config_path(workspace_name)
    if not p.exists():
        p.parent.mkdir(parents=True, exist_ok=True)
        base = {
            "schema_version": 1,
            "version": 1,
            "updated_at": _now_iso(),
            "transaction_types": [],
            "projects": []
        }
        _atomic_write_json(p, base)
        return base
    return _read_json(p)

def save_workspace_config(workspace_name: str, cfg: dict, *, if_match: int | None = None) -> dict:
    p = get_workspace_config_path(workspace_name)
    current = load_workspace_config(workspace_name)
    cur_ver = int(current.get("version", 1))
    if if_match is not None and if_match != cur_ver:
        raise RuntimeError(f"version_conflict: client={if_match}, server={cur_ver}")
    cfg = dict(cfg)
    cfg["version"] = cur_ver + 1
    cfg["updated_at"] = _now_iso()
    _atomic_write_json(p, cfg)
    return cfg