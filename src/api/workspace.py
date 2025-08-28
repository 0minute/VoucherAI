import json
from datetime import datetime
from typing import Dict, Any, Iterable
from pathlib import Path
from src.api.constants import *
import shutil
from src.api.utils import _atomic_write_json, _now_iso, _read_json

# 프런트 통신용 함수

# Workspace 관리
"""
모든 작업은 Workspace 단위로 이루어져야 함
아카이브 완료 시에는 중앙 DB에 저장됨.
"""

# 1. 워크스페이스 생성
"""
워크스페이스 폴더 하단에 워크스페이스 명으로 폴더를 생성한다
폴더 내부에는 아래의 파일이 필요하다
- setting : 대상 기간, 업로드된 파일 목록 및 경로, 분개 데이터 경로, 분개 라인수
- 업로드 파일 저장 폴더
- 결과 데이터 저장될 폴더(ocr 결과, llm 처리 결과, 분개 데이터)
- llm 처리 결과 데이터의 경우 사용자의 수정이 이루어질 수 있음.
- 사용자에게 반환할때 사용될 최종 분개 파일(xlsx, csv 형식)

"""
# === Workspace Setup ===
def ensure_workspace(workspace_name: str) -> dict:
    """
    주어진 워크스페이스 이름으로 필요한 폴더 구조를 자동 생성
    """
def ensure_workspace(workspace_name: str) -> dict:
    base = get_workspace_path(workspace_name)
    folders = [
        base / INPUT_FOLDER,
        base / INTERMEDIATE_FOLDER / OCR_FOLDER,
        base / INTERMEDIATE_FOLDER / LLM_FOLDER,
        base / INTERMEDIATE_FOLDER / JOURNAL_FOLDER,
        base / INTERMEDIATE_FOLDER / VISUALIZATION_FOLDER,
        base / FINAL_OUTPUT_FOLDER,
        base / LOGS_FOLDER,
        base / DB_FOLDER,  # ← 추가
    ]
    for f in folders:
        f.mkdir(parents=True, exist_ok=True)

    # setting.json 파일이 없으면 빈 템플릿 생성
    setting_file = get_setting_file(workspace_name)
    if not setting_file.exists():
        init_setting_file(workspace_name)


def init_setting_file(workspace_name: str) -> None:
    """
    최초 생성용 setting.json
    - 워크스페이스 ID와 폴더 경로만 기록
    - 파일/세부 메타는 빈 값으로 두고, 이후 update 함수로 누적
    """
    setting_file = get_setting_file(workspace_name)
    base_doc = {
        "workspace_name": workspace_name,
        "version": 1,  # 낙관적 잠금/감사를 위한 버전
        "created_at": datetime.utcnow().isoformat() + "Z",
        "updated_at": datetime.utcnow().isoformat() + "Z",
        "paths": {
            "input_dir": str(get_input_path(workspace_name)),
            "intermediate_dir": str(get_intermediate_path(workspace_name)),
            "ocr_dir": str(get_ocr_path(workspace_name)),
            "llm_dir": str(get_llm_path(workspace_name)),
            "journal_dir": str(get_journal_path(workspace_name)),
            "final_output_dir": str(get_final_output_path(workspace_name)),
            "logs_dir": str(get_logs_path(workspace_name)),
        },
        # 아래는 이후 update_*()로 채워질 필드
        "meta": {
            "target_period": "",
            "line_count": 0,
        },
        "files": {
            "uploaded": [],        # ex) ["input_files/a.pdf", ...]
            "ocr_results": [],     # ex) ["intermediate/ocr_results/a.json", ...]
            "llm_results": [],     # ex) ["intermediate/llm_results/a.json", ...]
            "visualization": {},    # ex) {"a.png": "intermediate/visualization/a.png", ...}
            "journal_drafts": [],  # ex) ["intermediate/journal_entries/journal_v1.csv"]
            "final_artifacts": []  # ex) [{"format":"xlsx","path":"...","version": 3}, ...]
        }
    }
    setting_file.write_text(json.dumps(base_doc, indent=2, ensure_ascii=False), encoding="utf-8")

# === Internal I/O ===
def _read_setting(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"setting.json not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))

def _write_setting(path: Path, data: Dict[str, Any]) -> None:
    data["updated_at"] = datetime.utcnow().isoformat() + "Z"
    # 자동 버전 증가
    data["version"] = int(data.get("version", 0)) + 1
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


# === Generic updater ===
def update_setting_file(workspace_name: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    임의의 dict patch를 머지하여 저장.
    안전하게 필요한 key만 덮어쓰기 위해 얕은/깊은 merge를 단순화.
    """
    sf = get_setting_file(workspace_name)
    data = _read_setting(sf)

    def deep_merge(dst: Dict[str, Any], src: Dict[str, Any]) -> Dict[str, Any]:
        for k, v in src.items():
            if isinstance(v, dict) and isinstance(dst.get(k), dict):
                dst[k] = deep_merge(dst[k], v)
            else:
                dst[k] = v
        return dst

    new_data = deep_merge(data, patch)
    _write_setting(sf, new_data)
    return new_data


# === Convenience updaters ===
def set_target_period(workspace_name: str, period_start: str, period_end: str) -> None:
    update_setting_file(workspace_name, {"meta": {"target_period": f"{period_start} ~ {period_end}"}})

def set_line_count(workspace_name: str, count: int) -> None:
    update_setting_file(workspace_name, {"meta": {"line_count": int(count)}})

def add_uploaded_files(workspace_name: str, paths: Iterable[str]) -> None:
    sf = get_setting_file(workspace_name)
    data = _read_setting(sf)
    current = set(data.get("files", {}).get("uploaded", []))
    current.update(paths)
    data["files"]["uploaded"] = sorted(current)
    _write_setting(sf, data)

def add_ocr_results(workspace_name: str, paths: Iterable[str]) -> None:
    sf = get_setting_file(workspace_name)
    data = _read_setting(sf)
    current = set(data.get("files", {}).get("ocr_results", []))
    current.update(paths)
    data["files"]["ocr_results"] = sorted(current)
    _write_setting(sf, data)

def add_llm_results(workspace_name: str, paths: Iterable[str]) -> None:
    sf = get_setting_file(workspace_name)
    data = _read_setting(sf)
    current = set(data.get("files", {}).get("llm_results", []))
    current.update(paths)
    data["files"]["llm_results"] = sorted(current)
    _write_setting(sf, data)

def add_visualization(workspace_name: str, img_dict: dict) -> None:
    sf = get_setting_file(workspace_name)
    data = _read_setting(sf)
    data["files"]["visualization"] = img_dict
    _write_setting(sf, data)

def add_journal_drafts(workspace_name: str, paths: Iterable[str]) -> None:
    sf = get_setting_file(workspace_name)
    data = _read_setting(sf)
    current = set(data.get("files", {}).get("journal_drafts", []))
    current.update(paths)
    data["files"]["journal_drafts"] = sorted(current)
    _write_setting(sf, data)

def add_final_artifact(workspace_name: str, path: str, fmt: str, produced_version: int | None = None) -> None:
    """
    최종 산출물 등록 (예: XLSX/CSV 등). produced_version은 데이터 기준 버전(옵션).
    """
    sf = get_setting_file(workspace_name)
    data = _read_setting(sf)
    entry = {"format": fmt, "path": path}
    if produced_version is not None:
        entry["produced_version"] = int(produced_version)
    artifacts = list(data.get("files", {}).get("final_artifacts", []))
    # 중복 경로 제거 후 append
    artifacts = [a for a in artifacts if a.get("path") != path]
    artifacts.append(entry)
    data["files"]["final_artifacts"] = artifacts
    _write_setting(sf, data)

if __name__ == "__main__":  
    ensure_workspace("ws_test")

# 2. 워크스페이스 삭제
"""
워크스페이스 폴더를 삭제함
"""

# def archive_workspace(workspace_name: str) -> Path:
#     """
#     워크스페이스를 archive/로 안전 이동(권장).
#     - setting.json 에 archived_at, status=archived 기록 추가
#     - 동일 이름 있으면 타임스탬프 suffix 추가
#     """
#     src = get_workspace_path(workspace_name).resolve()
#     if not src.exists():
#         raise FileNotFoundError(f"Workspace not found: {src}")

#     # 안전 가드: 반드시 WORKSPACE_ROOT 하위만 허용
#     if WORKSPACE_ROOT.resolve() not in src.parents:
#         raise PermissionError(f"Invalid workspace path: {src}")

#     # setting.json 업데이트 (archived 상태 반영)
#     try:
#         setting_file = get_setting_file(workspace_name)
#         if setting_file.exists():
#             data = _read_setting(setting_file)
#             data["status"] = "archived"
#             data["archived_at"] = datetime.utcnow().isoformat() + "Z"
#             _write_setting(setting_file, data)
#     except Exception as e:
#         print(f"[WARN] setting.json update 실패: {e}")

#     ARCHIVE_ROOT.mkdir(parents=True, exist_ok=True)
#     dst = ARCHIVE_ROOT / workspace_name
#     if dst.exists():
#         ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
#         dst = ARCHIVE_ROOT / f"{workspace_name}_{ts}"

#     shutil.move(str(src), str(dst))
#     return dst


def delete_workspace(workspace_name: str, *, permanent: bool = False, dry_run: bool = False) -> bool:
    """
    워크스페이스 폴더 삭제.
    - permanent=False: archive_workspace()로 이동(권장)
    - permanent=True : 실제 삭제(rmtree)
    - dry_run=True   : 실행하지 않고 경로만 검증
    """
    path = get_workspace_path(workspace_name).resolve()

    if not path.exists():
        # 이미 없음(멱등성 보장)
        return True

    # 안전 가드: 반드시 WORKSPACE_ROOT 하위만 허용
    if WORKSPACE_ROOT.resolve() not in path.parents:
        raise PermissionError(f"Refusing to delete outside WORKSPACE_ROOT: {path}")

    if dry_run:
        return True

    if not permanent:
        archive_workspace(workspace_name)
        return True

    # 영구 삭제
    shutil.rmtree(path)
    return True

# constant.py (추가)

def list_workspaces(include_archived: bool = False, with_status: bool = True) -> list[dict] | list[str]:
    """
    워크스페이스 목록 조회
    :param include_archived: True면 archive/ 폴더까지 포함
    :param with_status: True면 setting.json에서 status/updated_at 등 메타도 반환
    :return: 워크스페이스 이름 리스트 또는 상세정보 리스트
    """
    workspaces = []

    # 1) 활성 워크스페이스
    if WORKSPACE_ROOT.exists():
        for path in WORKSPACE_ROOT.iterdir():
            if path.name == DB_ROOT.name:
                continue
            if path.is_dir():
                if with_status:
                    info = _collect_workspace_info(path)
                    workspaces.append(info)
                else:
                    workspaces.append(path.name)

    # # 2) 아카이브 포함 옵션
    # if include_archived and ARCHIVE_ROOT.exists():
    #     for path in ARCHIVE_ROOT.iterdir():
    #         if path.is_dir():
    #             if with_status:
    #                 info = _collect_workspace_info(path, archived=True)
    #                 workspaces.append(info)
    #             else:
    #                 workspaces.append(path.name)

    return sorted(workspaces, key=lambda x: x["workspace_name"] if with_status else x)


def _collect_workspace_info(path: Path, archived: bool = False) -> dict:
    """
    내부 헬퍼: setting.json 로드 후 워크스페이스 메타 수집
    """
    setting_file = path / SETTING_FILE
    info = {
        "workspace_name": path.name,
        "path": str(path),
        "archived": archived,
        "status": "archived" if archived else "active",
        "updated_at": None,
        "created_at": None,
    }
    if setting_file.exists():
        try:
            data = _read_setting(setting_file)
            info["status"] = data.get("status", info["status"])
            info["updated_at"] = data.get("updated_at").strftime("%Y-%m-%d")
            info["created_at"] = data.get("created_at").strftime("%Y-%m-%d")
        except Exception:
            pass
    return info

def rename_workspace(old_name: str, new_name: str, include_archived: bool = False) -> Path:
    """
    워크스페이스 이름 변경 (폴더 rename + setting.json 업데이트)
    :param old_name: 기존 워크스페이스 이름
    :param new_name: 새 워크스페이스 이름
    :param include_archived: True면 archive/에서도 탐색
    :return: 변경된 새 경로
    """
    # 1) 현재 위치 탐색
    src = get_workspace_path(old_name)
    base_root = WORKSPACE_ROOT
    if not src.exists() and include_archived:
        src = ARCHIVE_ROOT / old_name
        base_root = ARCHIVE_ROOT

    if not src.exists():
        raise FileNotFoundError(f"Workspace not found: {old_name}")

    dst = base_root / new_name
    if dst.exists():
        raise FileExistsError(f"Target name already exists: {dst}")

    # 2) rename (폴더 이동)
    src.rename(dst)

    # 3) setting.json 업데이트
    setting_file = dst / SETTING_FILE
    if setting_file.exists():
        try:
            data = _read_setting(setting_file)
            data["workspace_name"] = new_name
            _write_setting(setting_file, data)
        except Exception as e:
            print(f"[WARN] setting.json 업데이트 실패: {e}")

    return dst

# 프로젝트명, 유형, 계정코드, 계정명 등 설정
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
            "projects": [],
            "chartofaccounts": {},

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

if __name__ == "__main__":
    print(list_workspaces())