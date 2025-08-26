from src.api.workspace import ensure_workspace, delete_workspace, list_workspaces, set_target_period, set_line_count, add_uploaded_files, rename_workspace, _read_setting
from src.api.upload import upload_images_to_workspace, list_uploaded_files, extract_zip_to_workspace, set_files_excluded, bulk_set_file_project, remove_uploaded_files_setting
from src.api.constants import get_setting_file, DEFAULT_ALLOWED_EXT
from src.api.models.upload_models import UploadFile, compute_file_meta, UploadsIndexRepository, get_uploads_repo
from pathlib import Path
from typing import Union, Iterable
from src.api.utils import _now_iso

#A. 워크스페이스
# - 워크스페이스 생성
def post_create_workspace(workspace_name: str, period_start: str, period_end: str) -> None:
    ensure_workspace(workspace_name)
    set_target_period(workspace_name, period_start, period_end)
    return {"ok": True, "data": {"workspace_name": workspace_name, "period": f"{period_start} ~ {period_end}"}, "error": None, "ts": _now_iso() }

# - 워크스페이스 삭제
def post_kill_workspace(workspace_name: str) -> None:
    delete_workspace(workspace_name, permanent=True)
    return {"ok": True, "data": {"workspace_name": workspace_name}, "error": None, "ts": _now_iso() }

# - 워크스페이스 목록 조회
def get_list_workspaces() -> list[str]:
    return {"ok": True, "data": {"workspaces": list_workspaces()}, "error": None, "ts": _now_iso() }

# - 워크스페이스 수정(대상 기간)
def patch_update_workspace(workspace_name: str, period: str) -> None:
    set_target_period(workspace_name, period)
    return {"ok": True, "data": {"workspace_name": workspace_name, "period": period}, "error": None, "ts": _now_iso() }

# - 워크스페이스 수정(이름 변경)
def patch_rename_workspace(old_name: str, new_name: str, include_archived: bool = False) -> Path:
    rename_workspace(old_name, new_name, include_archived)
    return {"ok": True, "data": {"old_name": old_name, "new_name": new_name}, "error": None, "ts": _now_iso() }

#B. 업로드
# - 파일 업로드
def post_upload_images_with_domain(
    workspace_name: str,
    image_paths,
    *,
    if_match_index_version: int | None = None,   # 낙관적 잠금(프런트에서 넘기면 충돌 잡아줌)
    rename_on_conflict: bool = True,
    allowed_ext: Iterable[str] = DEFAULT_ALLOWED_EXT,
):
    """
    1) 파일 복사(FS)
    2) settings.files.uploaded 누적(add_uploaded_files)
    3) UploadFiles(도메인) upsert + 저장소 save
    4) 최신 스냅샷 반환
    """
    # 1) 파일 복사 (질문 주신 함수 활용)
    res = upload_images_to_workspace(
        workspace_name,
        image_paths,
        rename_on_conflict=rename_on_conflict,
        allowed_ext=allowed_ext,
    )
    copied = res.get("copied", [])

    # 2) settings 반영 (Source of Truth 유지)
    if copied:
        add_uploaded_files(workspace_name, copied)

    # 3) 도메인 모델/저장
    repo = get_uploads_repo(workspace_name)
    uf = repo.load()  # UploadFiles
    for rel in copied:
        meta = compute_file_meta(rel)
        row = uf.get(rel)
        if not row:
            row = UploadFile(rel=rel)  # 기본값(project=None, excluded=False)
        # 메타 갱신
        row.size = meta["size"]
        row.mime = meta["mime"]
        # 해시를 쓰고 싶다면 UploadFile에 필드 추가해 저장
        uf.upsert(row)
    uf = repo.save(uf, if_match=if_match_index_version)

    # 4) 통합 스냅샷(프런트에 바로 쓰기 좋음)

    data = {
        "fs_result": res,
        "state": {
            "version": uf.version,
            "uploaded": uf.uploaded(),
            "excluded": uf.excluded(),
            "effective": uf.effective(),
            "records": uf.records(),  # 각 파일의 project/excluded/size/mime 포함
        }
    }
    return {
        "ok": True,
        "data": data,
        "error": None,
        "ts": _now_iso()
    }
# - zip파일 업로드

def post_upload_zip(
    workspace_name: str,
    zip_path: Union[str, Path],
    *,
    preserve_dirs: bool = True,
    rename_on_conflict: bool = True,
    allowed_ext: Iterable[str] = DEFAULT_ALLOWED_EXT,
    rollback_on_failure: bool = True,
    if_match_index_version: int | None = None,   # ← 추가: 업로드 인덱스(uploads_index.json) 버전 체크
) -> dict:
    """
    오케스트레이터: ZIP 해제 + settings.files.uploaded 누적 + UploadFiles(도메인) 반영
    - 실패 시(도메인/설정 커밋 오류) 파일/설정 롤백 옵션 지원
    - 성공 시 도메인 스냅샷(버전, uploaded/excluded/effective/records) 반환
    """
    # 1) ZIP → input_files 로 복사(한글 명/Zip Slip 처리 포함)
    res = extract_zip_to_workspace(
        workspace_name,
        zip_path,
        preserve_dirs=preserve_dirs,
        rename_on_conflict=rename_on_conflict,
        allowed_ext=allowed_ext,
    )
    copied_rel = res.get("copied_rel", [])
    copied_abs = res.get("copied_abs", [])

    # 2) settings.files.uploaded 누적
    try:
        if copied_rel:
            add_uploaded_files(workspace_name, copied_rel)
    except Exception as e:
        # 설정 반영 실패 → 파일 원복(옵션)
        if rollback_on_failure:
            for p in copied_abs:
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass
        raise

    # 3) 도메인/레포: UploadFiles upsert + save(원자적 쓰기, If-Match)
    try:
        repo = get_uploads_repo(workspace_name)    # UploadsIndexRepository(get_uploads_index_path(ws))
        uf = repo.load()                           # UploadFiles
        for rel in copied_rel:
            meta = compute_file_meta(rel)          # {"size":..,"mime":..,"sha256":..}
            row = uf.get(rel) or UploadFile(rel=rel)
            row.size = meta.get("size")
            row.mime = meta.get("mime")
            # 해시까지 기록하고 싶다면 UploadFile에 sha256 필드 추가 후:
            # row.sha256 = meta.get("sha256")
            uf.upsert(row)
        uf = repo.save(uf, if_match=if_match_index_version)

        # 통합 스냅샷(프런트에서 즉시 반영 용)
        state = {
            "version": uf.version,
            "uploaded": uf.uploaded(),
            "excluded": uf.excluded(),
            "effective": uf.effective(),
            "records": uf.records(),  # 각 파일의 project/excluded/size/mime 포함
        }

        return {
            "ok": True,
            "data": {
                "fs_result": res,
                "state": state,
            },
            "error": None,
            "ts": _now_iso()
        }

    except Exception as e:
        # 3단계(도메인 저장) 실패 시 롤백
        if rollback_on_failure:
            # 파일 삭제
            for p in copied_abs:
                try:
                    Path(p).unlink(missing_ok=True)
                except Exception:
                    pass
            # settings.files.uploaded 되돌리기
            try:
                remove_uploaded_files_setting(workspace_name, copied_rel)
            except Exception:
                pass
        raise

def get_uploaded_files(workspace_name: str) -> list[str]:
    return {"ok": True, "data": list_uploaded_files(workspace_name), "error": None, "ts": _now_iso() }

# - 파일 제외
def patch_exclude_file(workspace_name: str, file_paths: list[str]) -> None:
    res = set_files_excluded(workspace_name, file_paths, True)
    return res

# - 프로젝트명 설정 
def patch_set_project_name(workspace_name: str, filepath_and_project_name_dict: dict[str, str | None]) -> None:
    res = bulk_set_file_project(workspace_name, filepath_and_project_name_dict)
    return res

# C. OCR 추출 및 분개 추출
def post_run_ocr_and_journal(workspace_name: str) -> None:
    pass

# D. VoucherData 수정
def patch_update_voucher_data(workspace_name: str, edits: list[dict]) -> None:
    pass



