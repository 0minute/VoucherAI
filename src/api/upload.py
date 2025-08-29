from src.api.workspace import (ensure_workspace, 
get_setting_file, 
init_setting_file, 
add_uploaded_files, 
_read_setting,
_write_setting)

from src.api.constants import *
from pathlib import Path
from typing import Union, Iterable
import shutil
import zipfile
import tempfile
import os
import json
import mimetypes
from datetime import datetime
from src.api.utils import _now_iso

DEFAULT_ALLOWED_EXT = (".png",".jpg",".jpeg",".pdf")

#===보조함수===
def _to_iter(items: Union[str, Path, Iterable[Union[str, Path]]]) -> list[Path]:
    if items is None:
        return []
    if isinstance(items, (str, Path)):
        return [Path(items)]
    return [Path(x) for x in items]

def _unique_dest_path(dest_dir: Path, name: str) -> Path:
    """
    dest_dir/name 이 이미 있으면 'name (1).ext', 'name (2).ext'...로 유니크 보장
    """
    base = Path(name).stem
    ext = Path(name).suffix
    candidate = dest_dir / name
    i = 1
    while candidate.exists():
        candidate = dest_dir / f"{base} ({i}){ext}"
        i += 1
    return candidate


def _unique_dest_path(dest_dir: Path, name: str) -> Path:
    base = Path(name).stem
    ext = Path(name).suffix
    candidate = dest_dir / name
    i = 1
    while candidate.exists():
        candidate = dest_dir / f"{base} ({i}){ext}"
        i += 1
    return candidate

def _is_within(parent: Path, child: Path) -> bool:
    parent = parent.resolve(); child = child.resolve()
    return parent == child or parent in child.parents

def _best_effort_korean_name(zinfo: zipfile.ZipInfo) -> str:
    """
    ZIP 엔트리 이름 한글 복원:
    - UTF-8 플래그가 있으면 그대로 사용
    - 아니면 파이썬이 cp437로 디코드한 문자열을 다시 cp437로 '재-인코드'해 원시 바이트를 얻고,
      cp949 -> euc-kr -> mbcs(Windows) -> utf-8 순으로 복원 시도
    """
    name = zinfo.filename
    # 디렉토리 구분자 통일
    name = name.replace("\\", "/")

    # UTF-8 플래그
    if (zinfo.flag_bits & 0x800) != 0:
        return name

    # legacy: python은 cp437로 디코드해줌 → raw bytes 복원
    try:
        raw = name.encode("cp437", errors="strict")
    except Exception:
        # 실패 시 그냥 반환
        return name

    for enc in ("cp949", "euc-kr", "mbcs", "utf-8"):
        try:
            decoded = raw.decode(enc)
            return decoded.replace("\\", "/")
        except Exception:
            continue
    # 마지막으로 원본 반환
    return name

#===메인 함수===

def upload_images_to_workspace(
    workspace_name: str,
    image_paths: Union[str, Path, Iterable[Union[str, Path]]],
    *,
    rename_on_conflict: bool = True,
    allowed_ext: Iterable[str] = DEFAULT_ALLOWED_EXT,
) -> dict:
    """
    이미지 파일을 선택 워크스페이스의 input_files 폴더로 복사하고,
    add_uploaded_files()로 setting.json에 반영합니다.

    :param workspace_name: 워크스페이스 이름
    :param image_paths: 업로드할 파일(단일 경로 또는 리스트)
    :param rename_on_conflict: True면 동일 파일명이 있을 때 자동으로 (1), (2) 붙임. False면 덮어쓰기
    :param allowed_ext: 허용 확장자 리스트(소문자 비교)
    :return: {"copied": [str...], "skipped": [str...], "errors": [{"path": str, "reason": str}, ...]}
    """
    # 워크스페이스/폴더 보장 및 setting.json 최소 초기화
    sf = get_setting_file(workspace_name)
    if not sf.exists():
        init_setting_file(workspace_name)

    dest_dir = get_input_path(workspace_name)
    dest_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    skipped: list[str] = []
    errors: list[dict] = []

    allowed = {ext.lower() for ext in allowed_ext}
    for p in _to_iter(image_paths):
        try:
            if not p.exists() or not p.is_file():
                errors.append({"path": str(p), "reason": "file_not_found"})
                continue

            ext = p.suffix.lower()
            if allowed and ext not in allowed:
                skipped.append(str(p))
                continue

            target = dest_dir / p.name
            if target.exists() and rename_on_conflict:
                target = _unique_dest_path(dest_dir, p.name)

            # 복사 (메타데이터 유지)
            shutil.copy2(str(p), str(target))
            # setting.json 반영 (프로젝트 루트 기준 상대 경로로 저장)
            try:
                rel = str(target.resolve().relative_to(PROJECT_ROOT.resolve()))
            except Exception:
                # 상대 변환 실패 시 절대경로로 저장
                rel = str(target.resolve())

            copied.append(rel)

        except Exception as e:
            errors.append({"path": str(p), "reason": f"{type(e).__name__}: {e}"})

    return {"copied": copied, "skipped": skipped, "errors": errors}


def extract_zip_to_workspace(
    workspace_name: str,
    zip_path: Union[str, Path],
    *,
    preserve_dirs: bool = True,           # True면 ZIP 내부 디렉토리 구조 유지, False면 평탄화
    rename_on_conflict: bool = True,
    allowed_ext: Iterable[str] = DEFAULT_ALLOWED_EXT,  # None이면 모든 확장자 허용
) -> dict:
    """
    ZIP을 해제하여 선택 워크스페이스의 input_files/ 하위로 복사.
    - 한글 파일명 복원
    - Zip Slip 방지
    - 파일명 충돌 시 고유화
    - allowed_ext 필터

    return:
      {
        "copied_abs": [...],
        "copied_rel": [...],   # PROJECT_ROOT 기준 상대경로 (setting.json에 쓰기 좋음)
        "skipped":   [{"name": "a.txt", "reason": "ext_denied"}, ...],
        "errors":    [{"name": "??", "reason": "..."}, ...]
      }
    """
    ensure_workspace(workspace_name)
    sf = get_setting_file(workspace_name)
    if not sf.exists():
        init_setting_file(workspace_name)

    dest_root = get_input_path(workspace_name)
    dest_root.mkdir(parents=True, exist_ok=True)

    copied_abs, copied_rel, skipped, errors = [], [], [], []
    allowed = set(e.lower() for e in allowed_ext) if allowed_ext else None

    zp = Path(zip_path)
    if not zp.exists() or not zp.is_file():
        return {
            "copied_abs": [], "copied_rel": [],
            "skipped": [], "errors": [{"name": str(zp), "reason": "zip_not_found"}]
        }

    if not zipfile.is_zipfile(str(zp)):
        return {
            "copied_abs": [], "copied_rel": [],
            "skipped": [], "errors": [{"name": str(zp), "reason": "not_a_zip"}]
        }

    try:
        with zipfile.ZipFile(str(zp), "r") as zf:
            for zinfo in zf.infolist():
                if zinfo.is_dir():
                    # 디렉토리는 필요 시 생성만
                    if preserve_dirs:
                        decoded = _best_effort_korean_name(zinfo).strip("/ ")
                        if not decoded:
                            continue
                        target_dir = dest_root / decoded
                        # Zip Slip 방지
                        if not _is_within(dest_root, target_dir):
                            skipped.append({"name": decoded, "reason": "path_traversal_blocked"})
                            continue
                        target_dir.mkdir(parents=True, exist_ok=True)
                    continue

                decoded = _best_effort_korean_name(zinfo)
                # 경로 정규화
                parts = [p for p in decoded.split("/") if p not in ("", ".", "..")]
                if not parts:
                    continue

                filename = parts[-1] if preserve_dirs else "/".join(parts).split("/")[-1]
                subdir = (Path(*parts[:-1]) if preserve_dirs and len(parts) > 1 else Path(""))
                target_dir = dest_root / subdir
                target_dir.mkdir(parents=True, exist_ok=True)

                target = target_dir / filename

                # 확장자 필터
                ext = target.suffix.lower()
                if allowed is not None and ext not in allowed:
                    skipped.append({"name": decoded, "reason": "ext_denied"})
                    continue

                # Zip Slip 방지
                if not _is_within(dest_root, target_dir):
                    skipped.append({"name": decoded, "reason": "path_traversal_blocked"})
                    continue

                # 파일명 충돌 처리
                if target.exists() and rename_on_conflict:
                    target = _unique_dest_path(target_dir, filename)

                # 실제 복사
                try:
                    with zf.open(zinfo, "r") as src:
                        # tmp 파일로 쓴 후 원자적 교체
                        with tempfile.NamedTemporaryFile("wb", delete=False, dir=target_dir) as tmp:
                            while True:
                                chunk = src.read(1024 * 1024)
                                if not chunk:
                                    break
                                tmp.write(chunk)
                            tmp.flush()
                            os.fsync(tmp.fileno())
                            tmp_path = tmp.name
                    os.replace(tmp_path, target)
                    abs_p = str(target.resolve())
                    copied_abs.append(abs_p)
                    try:
                        rel = str(target.resolve().relative_to(PROJECT_ROOT.resolve()))
                    except Exception:
                        rel = abs_p
                    copied_rel.append(rel)
                except Exception as e:
                    errors.append({"name": decoded, "reason": f"{type(e).__name__}: {e}"})
                    # tmp 파일 청소
                    try:
                        if 'tmp_path' in locals() and os.path.exists(tmp_path):
                            os.remove(tmp_path)
                    except Exception:
                        pass

    except Exception as e:
        errors.append({"name": str(zp), "reason": f"{type(e).__name__}: {e}"})

    return {
        "copied_abs": copied_abs,
        "copied_rel": copied_rel,
        "skipped": skipped,
        "errors": errors
    }


# 업로드된 파일 리스트 읽기
def list_uploaded_files(workspace_name: str) -> list[str]:
    # uploads_index = get_uploads_index_path(workspace_name)
    uploads_index = _read_uploads_index(workspace_name)
    files_list = uploads_index["files"]
    return files_list



# 파일 삭제 처리 함수 > 정리 필요

def _normalize_rel(path: str | Path, project_root: Path = PROJECT_ROOT) -> str:
    """PROJECT_ROOT 기준 상대경로 (POSIX 문자열)로 표준화"""
    if isinstance(path, str):
        path = Path(path)

    try:
        # 절대경로화 후 PROJECT_ROOT 기준 상대경로 계산
        rel = path.resolve().relative_to(project_root.resolve())
    except Exception:
        # relative_to 실패하면 그냥 파일명만 사용 (fallback)
        rel = path.name

    # 항상 POSIX 스타일 문자열 반환
    return rel.as_posix()

def get_excluded_files(workspace_name: str) -> set[str]:
    sf = get_setting_file(workspace_name)
    data = _read_setting(sf)
    return set(data.get("files", {}).get("excluded", []))

def set_files_excluded(workspace_name: str, paths: list[str], excluded: bool, client_version: int | None = None) -> dict:
    sf = get_setting_file(workspace_name)
    data = _read_setting(sf)
    cur_ver = int(data.get("version", 0))
    if client_version is not None and client_version != cur_ver:
        raise RuntimeError(f"version_conflict: client={client_version}, server={cur_ver}")

    uploaded = set(data.get("files", {}).get("uploaded", []))
    ex = set(data.get("files", {}).get("excluded", []))
    # 표준화 + 업로드된 파일에 한정
    norm = {_normalize_rel(Path(p)) for p in paths if p}
    norm &= uploaded
    if excluded:
        ex |= norm
    else:
        ex -= norm

    data.setdefault("files", {})
    data["files"]["excluded"] = sorted(ex)
    _write_setting(sf, data)

    read_index = _read_uploads_index(workspace_name)
    read_index["files"] = [f for f in read_index["files"] if f["rel"] not in norm]
    _write_uploads_index(workspace_name, read_index)

    return list_uploads_state(workspace_name)

# --- 현재 업로드 상태(프런트에 바로 주기 좋음) ---
def list_uploads_state(workspace_name: str) -> dict:
    sf = get_setting_file(workspace_name)
    data = _read_setting(sf)
    uploaded = list(data.get("files", {}).get("uploaded", []))
    excluded = set(data.get("files", {}).get("excluded", []))
    effective = [p for p in uploaded if p not in excluded]
    return {
        "version": data.get("version"),
        "uploaded": uploaded,
        "excluded": sorted(excluded),
        "effective": effective,
    }


def _read_uploads_index(workspace_name: str) -> dict:
    p = get_uploads_index_path(workspace_name)
    if not p.exists():
        return {"version": 1, "updated_at": _now_iso(), "files": []}
    return json.loads(p.read_text(encoding="utf-8"))

def get_uploaded_files_path(workspace_name: str) -> list[str]:
    # uploads_index = get_uploads_index_path(workspace_name)
    uploads_index = _read_uploads_index(workspace_name)
    uploaded_files = uploads_index.get("files", [])
    return [os.path.join(PROJECT_ROOT, file.get("rel")) for file in uploaded_files]

def _write_uploads_index(workspace_name: str, data: dict) -> None:
    p = get_uploads_index_path(workspace_name)
    p.parent.mkdir(parents=True, exist_ok=True)
    data["version"] = int(data.get("version", 0)) + 1
    data["updated_at"] = _now_iso()
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, p)

def _file_record(rel: str) -> dict:
    # 기본 레코드 스키마(필요 시 확장: owner, notes, labels 등)
    abs_p = (PROJECT_ROOT / rel).resolve()
    size = abs_p.stat().st_size if abs_p.exists() else None
    mime = mimetypes.guess_type(abs_p.name)[0]
    now = _now_iso()
    return {
        "rel": rel,              # PROJECT_ROOT 기준 상대경로
        "project": None,         # 프런트에서 설정하는 값
        "labels": [],            # 선택: 다중 태그용
        "excluded": False,       # setting.json의 excluded와 중복이지만 캐시용 필드(선택)
        "size": size,
        "mime": mime,
        "created_at": now,
        "updated_at": now,
    }

def sync_uploads_index_from_settings(workspace_name: str) -> dict:
    """
    setting.json의 uploaded/excluded를 기준으로 uploads_index.json을 보정.
    - 신규 업로드 파일: 인덱스에 추가
    - 삭제된 파일: 인덱스에서 제거
    - excluded 상태: (선택) 캐시 갱신
    return: uploads_index 최신 스냅샷
    """
    sf = _read_setting(get_setting_file(workspace_name))
    uploaded = set(sf.get("files", {}).get("uploaded", []))
    excluded = set(sf.get("files", {}).get("excluded", []))

    idx = _read_uploads_index(workspace_name)
    prev = {f["rel"]: f for f in idx.get("files", [])}

    # add / update
    merged = []
    for rel in uploaded:
        rec = prev.get(rel) or _file_record(rel)
        # (선택) excluded 캐시 반영
        rec["excluded"] = (rel in excluded)
        rec["updated_at"] = _now_iso()
        merged.append(rec)

    # remove: uploaded에 없는 레코드는 드롭
    idx["files"] = merged
    _write_uploads_index(workspace_name, idx)
    return idx

def list_uploads_with_projects(workspace_name: str) -> dict:
    """
    프런트로 반환하기 좋은 통합 뷰
    """
    sf = _read_setting(get_setting_file(workspace_name))
    idx = _read_uploads_index(workspace_name)
    uploaded = sf.get("files", {}).get("uploaded", [])
    excluded = set(sf.get("files", {}).get("excluded", []))
    # 인덱스 맵
    meta = {f["rel"]: f for f in idx.get("files", [])}
    # effective = uploaded - excluded
    effective = [rel for rel in uploaded if rel not in excluded]
    # 응답 레코드 조합
    records = []
    for rel in uploaded:
        r = meta.get(rel, _file_record(rel))
        records.append({
            "rel": rel,
            "project": r.get("project"),
            "labels": r.get("labels", []),
            "excluded": (rel in excluded),
            "size": r.get("size"),
            "mime": r.get("mime"),
            "updated_at": r.get("updated_at"),
        })
    return {
        "version": sf.get("version"),
        "index_version": idx.get("version"),
        "uploaded": uploaded,
        "excluded": sorted(excluded),
        "effective": effective,
        "records": records,  # 행별 메타 포함
    }

def set_file_project(
    workspace_name: str,
    rel_path: str,
    project: str | None,
    *,
    if_match_index_version: int | None = None
) -> dict:
    """
    단일 파일의 프로젝트명 설정/해제(None).
    - if_match_index_version: uploads_index.json 낙관적 잠금
    """
    idx = _read_uploads_index(workspace_name)
    # cur_ver = int(idx.get("version", 0))
    # if if_match_index_version is not None and if_match_index_version != cur_ver:
    #     raise RuntimeError(f"version_conflict: client={if_match_index_version}, server={cur_ver}")

    # 존재 보장 및 동기화
    # sf = _read_setting(get_setting_file(workspace_name))
    # uploaded = set(sf.get("files", {}).get("uploaded", []))
    # if rel_path not in uploaded:
    #     raise FileNotFoundError(f"not_uploaded: {rel_path}")

    found = False
    for rec in idx.get("files", []):
        if rec["rel"] == rel_path:
            rec["project"] = project
            rec["updated_at"] = _now_iso()
            found = True
            break
    if not found:
        rec = _file_record(rel_path)
        rec["project"] = project
        idx["files"].append(rec)

    _write_uploads_index(workspace_name, idx)
    return list_uploads_with_projects(workspace_name)

def bulk_set_file_project(
    workspace_name: str,
    mapping: dict[str, str | None],
    *,
    if_match_index_version: int | None = None
) -> dict:
    """
    여러 파일의 프로젝트명을 한 번에 설정/해제
    mapping: { rel_path: project | None }
    """
    idx = _read_uploads_index(workspace_name)
    cur_ver = int(idx.get("version", 0))
    if if_match_index_version is not None and if_match_index_version != cur_ver:
        raise RuntimeError(f"version_conflict: client={if_match_index_version}, server={cur_ver}")

    sf = _read_setting(get_setting_file(workspace_name))
    uploaded = set(sf.get("files", {}).get("uploaded", []))
    rec_map = {f["rel"]: f for f in idx.get("files", [])}

    for rel, proj in mapping.items():
        if rel not in uploaded:
            # 업로드 외 항목은 무시 또는 예외 처리(여기선 무시)
            continue
        rec = rec_map.get(rel)
        if not rec:
            rec = _file_record(rel); rec_map[rel] = rec
        rec["project"] = proj
        rec["updated_at"] = _now_iso()

    idx["files"] = list(rec_map.values())
    _write_uploads_index(workspace_name, idx)
    return list_uploads_with_projects(workspace_name)

def remove_uploaded_files_setting(workspace_name: str, paths: Iterable[str]) -> None:
    """
    setting.json 의 files.uploaded 에서 주어진 경로들을 제거
    - paths 는 PROJECT_ROOT 기준 상대경로 문자열 권장
    """
    sf = get_setting_file(workspace_name)
    data = _read_setting(sf)
    cur = set(data.get("files", {}).get("uploaded", []))
    # 표준화 후 제거
    norm = set()
    for p in paths:
        pp = Path(p)
        norm.add(_normalize_rel(pp))
    data.setdefault("files", {})
    data["files"]["uploaded"] = sorted(cur - norm)
    _write_setting(sf, data)