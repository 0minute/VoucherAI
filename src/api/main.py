from src.api.workspace import (ensure_workspace, 
                               delete_workspace, 
                               list_workspaces, 
                               set_target_period, 
                               set_line_count, 
                               add_uploaded_files, 
                               rename_workspace, 
                               _read_setting, 
                               add_ocr_results, 
                               add_llm_results, 
                               add_visualization, 
                               add_journal_drafts)
from src.api.upload import upload_images_to_workspace, list_uploaded_files, extract_zip_to_workspace, set_files_excluded, bulk_set_file_project, remove_uploaded_files_setting, get_uploaded_files_path
from src.api.constants import (get_setting_file, 
                               DEFAULT_ALLOWED_EXT, 
                               get_ocr_path, 
                               get_llm_path, 
                               get_visualization_path, 
                               get_journal_path,
                               get_voucher_db_path,
                               get_central_db_path)
from src.api.models.upload_models import UploadFileRow, compute_file_meta, UploadsIndexRepository, get_uploads_repo
from src.ant.llm_main import extract_with_locations, draw_overlays
from src.entjournal.journal_main import (get_json_wt_one_value_from_extract_invoice_fields, 
                                         drop_source_id_from_json, 
                                         make_journal_entry, 
                                         make_journal_entry_to_record_list,
                                         sap_view,
                                         dzone_view)
from pathlib import Path
from typing import Union, Iterable
from src.api.utils import _now_iso, fs_to_static_url
from src.entocr.ocr_main import ocr_image_and_save_json_by_extension
from src.api.db import read_voucher_data, update_voucher_data, initialize_voucher_data
import json
import os

from typing import Optional, List, Dict, Any
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Body
from fastapi import Path as ApiPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any, Dict, Optional
import os, json
from pydantic import BaseModel, Field   
from datetime import datetime, timezone
import shutil
import os

from src.api.constants import WORKSPACE_ROOT, get_workspace_path

# 워크스페이스 루트/임시 디렉토리 (프로젝트 규칙에 맞춰 조정)

def get_workspace_tmpdir(workspace_name: str) -> Path:
    tmp = get_workspace_path(workspace_name) / "_tmp_uploads"
    tmp.mkdir(parents=True, exist_ok=True)
    return tmp
        
#A. 워크스페이스
# - 워크스페이스 생성
# def post_create_workspace(workspace_name: str, period_start: str, period_end: str) -> None:
#     ensure_workspace(workspace_name)
#     set_target_period(workspace_name, period_start, period_end)
#     return {"ok": True, "data": {"workspace_name": workspace_name, "period": f"{period_start} ~ {period_end}"}, "error": None, "ts": _now_iso() }

# # - 워크스페이스 삭제
# def post_kill_workspace(workspace_name: str) -> None:
#     delete_workspace(workspace_name, permanent=True)
#     return {"ok": True, "data": {"workspace_name": workspace_name}, "error": None, "ts": _now_iso() }

# # - 워크스페이스 목록 조회
# def get_list_workspaces() -> list[str]:
#     return {"ok": True, "data": {"workspaces": list_workspaces()}, "error": None, "ts": _now_iso() }

# # - 워크스페이스 수정(대상 기간)
# def patch_update_workspace(workspace_name: str, period: str) -> None:
#     set_target_period(workspace_name, period)
#     return {"ok": True, "data": {"workspace_name": workspace_name, "period": period}, "error": None, "ts": _now_iso() }

# # - 워크스페이스 수정(이름 변경)
# def patch_rename_workspace(old_name: str, new_name: str, include_archived: bool = False) -> Path:
#     rename_workspace(old_name, new_name, include_archived)
#     return {"ok": True, "data": {"old_name": old_name, "new_name": new_name}, "error": None, "ts": _now_iso() }

# ====== Pydantic 모델 (JS와 계약) ======
class CreateWorkspaceBody(BaseModel):
    workspaceName: str = Field(min_length=1)
    # periodStart: str = Field(description="YYYY-MM-DD")
    # periodEnd: str = Field(description="YYYY-MM-DD")

# class UpdatePeriodBody(BaseModel):
#     periodStart: str
#     periodEnd: str

class RenameBody(BaseModel):
    newName: str = Field(min_length=1)
    includeArchived: Optional[bool] = False

class ApiResponse(BaseModel):
    ok: bool
    data: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    ts: str

class ExcludeBody(BaseModel):
    filePaths: List[str]
    excluded: bool = True

class ProjectMapBody(BaseModel):
    mapping: Dict[str, Optional[str]]

class VoucherUpdateBody(BaseModel):
    edits: Dict[str, Any]


# ====== FastAPI 앱 ======
app = FastAPI(title="Workspace API", version="1.0.0")

# 필요에 따라 Origin 제한하세요.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # TODO: 배포시 프런트 도메인으로 제한
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# A-1. 워크스페이스 생성
@app.post("/workspaces", response_model=ApiResponse, status_code=201)
def create_workspace(body: CreateWorkspaceBody):
    try:
        ensure_workspace(body.workspaceName)
        # set_target_period(body.workspaceName)
        return ApiResponse(
            ok=True,
            data={
                "workspaceName": body.workspaceName,
            },
            error=None,
            ts=_now_iso()
        )
    except Exception as e:
        # 필요하면 구체적 예외로 분기
        raise HTTPException(status_code=400, detail=str(e))

# A-2. 워크스페이스 삭제
@app.delete("/workspaces/{workspaceName}", response_model=ApiResponse)
def kill_workspace(workspaceName: str):
    try:
        delete_workspace(workspaceName, permanent=True)
        return ApiResponse(
            ok=True,
            data={"workspaceName": workspaceName},
            error=None,
            ts=_now_iso()
        )
    except Exception as e:
        raise HTTPException(status_code=404, detail=str(e))

# A-3. 워크스페이스 목록 조회
@app.get("/workspaces", response_model=ApiResponse)
def get_workspaces():
    try:
        return ApiResponse(
            ok=True,
            data={"workspaces": list_workspaces()},
            error=None,
            ts=_now_iso()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# # A-4. 워크스페이스 기간 수정
# @app.patch("/workspaces/{workspaceName}/period", response_model=ApiResponse)
# def update_workspace_period(workspaceName: str, body: UpdatePeriodBody):
#     try:
#         set_target_period(workspaceName, body.periodStart, body.periodEnd)
#         return ApiResponse(
#             ok=True,
#             data={
#                 "workspaceName": workspaceName,
#                 "period": {
#                     "periodStart": body.periodStart,
#                     "periodEnd": body.periodEnd
#                 }
#             },
#             error=None,
#             ts=_now_iso()
#         )
#     except Exception as e:
#         raise HTTPException(status_code=400, detail=str(e))

# A-5. 워크스페이스 이름 변경
@app.patch("/workspaces/{oldName}", response_model=ApiResponse)
def rename_workspace_api(oldName: str, body: RenameBody):
    try:
        rename_workspace(oldName, body.newName, body.includeArchived or False)
        return ApiResponse(
            ok=True,
            data={"oldName": oldName, "newName": body.newName},
            error=None,
            ts=_now_iso()
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# #B. 업로드
# # - 파일 업로드
# def post_upload_images_with_domain(
#     workspace_name: str,
#     image_paths,
#     *,
#     if_match_index_version: int | None = None,   # 낙관적 잠금(프런트에서 넘기면 충돌 잡아줌)
#     rename_on_conflict: bool = True,
#     allowed_ext: Iterable[str] = DEFAULT_ALLOWED_EXT,
# ):
#     """
#     1) 파일 복사(FS)
#     2) settings.files.uploaded 누적(add_uploaded_files)
#     3) UploadFiles(도메인) upsert + 저장소 save
#     4) 최신 스냅샷 반환
#     """
#     # 1) 파일 복사 (질문 주신 함수 활용)
#     res = upload_images_to_workspace(
#         workspace_name,
#         image_paths,
#         rename_on_conflict=rename_on_conflict,
#         allowed_ext=allowed_ext,
#     )
#     copied = res.get("copied", [])

#     # 2) settings 반영 (Source of Truth 유지)
#     if copied:
#         add_uploaded_files(workspace_name, copied)

#     # 3) 도메인 모델/저장
#     repo = get_uploads_repo(workspace_name)
#     uf = repo.load()  # UploadFiles
#     for rel in copied:
#         meta = compute_file_meta(rel)
#         row = uf.get(rel)
#         if not row:
#             row = UploadFile(rel=rel)  # 기본값(project=None, excluded=False)
#         # 메타 갱신
#         row.size = meta["size"]
#         row.mime = meta["mime"]
#         # 해시를 쓰고 싶다면 UploadFile에 필드 추가해 저장
#         uf.upsert(row)
#     uf = repo.save(uf, if_match=if_match_index_version)

#     # 4) 통합 스냅샷(프런트에 바로 쓰기 좋음)

#     data = {
#         "fs_result": res,
#         "state": {
#             "version": uf.version,
#             "uploaded": uf.uploaded(),
#             "excluded": uf.excluded(),
#             "effective": uf.effective(),
#             "records": uf.records(),  # 각 파일의 project/excluded/size/mime 포함
#         }
#     }
#     return {
#         "ok": True,
#         "data": data,
#         "error": None,
#         "ts": _now_iso()
#     }
# # - zip파일 업로드

# def post_upload_zip(
#     workspace_name: str,
#     zip_path: Union[str, Path],
#     *,
#     preserve_dirs: bool = True,
#     rename_on_conflict: bool = True,
#     allowed_ext: Iterable[str] = DEFAULT_ALLOWED_EXT,
#     rollback_on_failure: bool = True,
#     if_match_index_version: int | None = None,   # ← 추가: 업로드 인덱스(uploads_index.json) 버전 체크
# ) -> dict:
#     """
#     오케스트레이터: ZIP 해제 + settings.files.uploaded 누적 + UploadFiles(도메인) 반영
#     - 실패 시(도메인/설정 커밋 오류) 파일/설정 롤백 옵션 지원
#     - 성공 시 도메인 스냅샷(버전, uploaded/excluded/effective/records) 반환
#     """
#     # 1) ZIP → input_files 로 복사(한글 명/Zip Slip 처리 포함)
#     res = extract_zip_to_workspace(
#         workspace_name,
#         zip_path,
#         preserve_dirs=preserve_dirs,
#         rename_on_conflict=rename_on_conflict,
#         allowed_ext=allowed_ext,
#     )
#     copied_rel = res.get("copied_rel", [])
#     copied_abs = res.get("copied_abs", [])

#     # 2) settings.files.uploaded 누적
#     try:
#         if copied_rel:
#             add_uploaded_files(workspace_name, copied_rel)
#     except Exception as e:
#         # 설정 반영 실패 → 파일 원복(옵션)
#         if rollback_on_failure:
#             for p in copied_abs:
#                 try:
#                     Path(p).unlink(missing_ok=True)
#                 except Exception:
#                     pass
#         raise

#     # 3) 도메인/레포: UploadFiles upsert + save(원자적 쓰기, If-Match)
#     try:
#         repo = get_uploads_repo(workspace_name)    # UploadsIndexRepository(get_uploads_index_path(ws))
#         uf = repo.load()                           # UploadFiles
#         for rel in copied_rel:
#             meta = compute_file_meta(rel)          # {"size":..,"mime":..,"sha256":..}
#             row = uf.get(rel) or UploadFile(rel=rel)
#             row.size = meta.get("size")
#             row.mime = meta.get("mime")
#             # 해시까지 기록하고 싶다면 UploadFile에 sha256 필드 추가 후:
#             # row.sha256 = meta.get("sha256")
#             uf.upsert(row)
#         uf = repo.save(uf, if_match=if_match_index_version)

#         # 통합 스냅샷(프런트에서 즉시 반영 용)
#         state = {
#             "version": uf.version,
#             "uploaded": uf.uploaded(),
#             "excluded": uf.excluded(),
#             "effective": uf.effective(),
#             "records": uf.records(),  # 각 파일의 project/excluded/size/mime 포함
#         }

#         return {
#             "ok": True,
#             "data": {
#                 "fs_result": res,
#                 "state": state,
#             },
#             "error": None,
#             "ts": _now_iso()
#         }

#     except Exception as e:
#         # 3단계(도메인 저장) 실패 시 롤백
#         if rollback_on_failure:
#             # 파일 삭제
#             for p in copied_abs:
#                 try:
#                     Path(p).unlink(missing_ok=True)
#                 except Exception:
#                     pass
#             # settings.files.uploaded 되돌리기
#             try:
#                 remove_uploaded_files_setting(workspace_name, copied_rel)
#             except Exception:
#                 pass
#         raise

# def get_uploaded_files(workspace_name: str) -> list[str]:
#     return {"ok": True, "data": list_uploaded_files(workspace_name), "error": None, "ts": _now_iso() }

# # - 파일 제외
# def patch_exclude_file(workspace_name: str, file_paths: list[str]) -> None:
#     res = set_files_excluded(workspace_name, file_paths, True)
#     return res

# # - 프로젝트명 설정 
# def patch_set_project_name(workspace_name: str, filepath_and_project_name_dict: dict[str, str | None]) -> None:
#     res = bulk_set_file_project(workspace_name, filepath_and_project_name_dict)
#     return res

# ---------- 업로드: 이미지 여러 개 ----------
@app.post("/workspaces/{workspaceName}/uploads/images", response_model=ApiResponse)
async def upload_images_with_domain(
    workspaceName: str,
    files: List[UploadFile] = File(..., description="이미지들"),
    ifMatchIndexVersion: Optional[int] = Form(default=None),
    renameOnConflict: bool = Form(default=True),
    allowedExt: Optional[str] = Form(default=None),  # ".png,.jpg" 형태 허용
):
    try:
        tmpdir = get_workspace_tmpdir(workspaceName)
        saved_paths: List[Path] = []

        # 1) 파일 저장 (multipart → 디스크)
        for f in files:
            suffix = Path(f.filename).suffix.lower()
            # allowedExt 지정 시 필터
            if allowedExt:
                allowed = {s.strip().lower() for s in allowedExt.split(",") if s.strip()}
            else:
                allowed = DEFAULT_ALLOWED_EXT
            if suffix not in allowed:
                raise HTTPException(status_code=400, detail=f"Extension not allowed: {suffix}")

            dest = tmpdir / f.filename
            with dest.open("wb") as w:
                shutil.copyfileobj(f.file, w)
            saved_paths.append(dest)

        # 2) 기존 오케스트레이션 호출
        res = upload_images_to_workspace(
            workspaceName,
            [str(p) for p in saved_paths],
            rename_on_conflict=renameOnConflict,
            allowed_ext=allowed if allowedExt else DEFAULT_ALLOWED_EXT,
        )
        copied = res.get("copied", [])
        if copied:
            add_uploaded_files(workspaceName, copied)

        # 3) 도메인 반영
        repo = get_uploads_repo(workspaceName)
        uf = repo.load()  # UploadFiles 도메인
        for rel in copied:
            meta = compute_file_meta(rel)
            row = uf.get(rel) or UploadFileRow(rel=rel)
            row.size = meta.get("size")
            row.mime = meta.get("mime")
            uf.upsert(row)
        uf = repo.save(uf, if_match=ifMatchIndexVersion)

        state = {
            "version": uf.version,
            "uploaded": uf.uploaded(),
            "excluded": uf.excluded(),
            "effective": uf.effective(),
            "records": uf.records(),
        }

        return ApiResponse(ok=True, data={"fsResult": res, "state": state}, error=None, ts=_now_iso())
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- 업로드: ZIP 1개 ----------
@app.post("/workspaces/{workspaceName}/uploads/zip", response_model=ApiResponse)
async def upload_zip(
    workspaceName: str,
    file: UploadFile = File(..., description="zip 파일"),
    preserveDirs: bool = Form(default=True),
    renameOnConflict: bool = Form(default=True),
    allowedExt: Optional[str] = Form(default=None),
    rollbackOnFailure: bool = Form(default=True),
    ifMatchIndexVersion: Optional[int] = Form(default=None),
):
    try:
        tmpdir = get_workspace_tmpdir(workspaceName)
        # 업로드 zip을 임시 저장
        zip_path = tmpdir / file.filename
        with zip_path.open("wb") as w:
            shutil.copyfileobj(file.file, w)

        # ZIP 해제 + settings + 도메인 upsert (네가 만든 오케스트레이터 그대로 호출)
        res = extract_zip_to_workspace(
            workspaceName, zip_path,
            preserve_dirs=preserveDirs,
            rename_on_conflict=renameOnConflict,
            allowed_ext={s.strip().lower() for s in allowedExt.split(",")} if allowedExt else DEFAULT_ALLOWED_EXT,
        )
        copied_rel = res.get("copied_rel", [])
        copied_abs = res.get("copied_abs", [])

        # settings 누적
        if copied_rel:
            add_uploaded_files(workspaceName, copied_rel)

        # 도메인 저장
        try:
            repo = get_uploads_repo(workspaceName)
            uf = repo.load()
            for rel in copied_rel:
                meta = compute_file_meta(rel)
                row = uf.get(rel) or UploadFileRow(rel=rel)
                row.size = meta.get("size")
                row.mime = meta.get("mime")
                uf.upsert(row)
            uf = repo.save(uf, if_match=ifMatchIndexVersion)
            state = {
                "version": uf.version,
                "uploaded": uf.uploaded(),
                "excluded": uf.excluded(),
                "effective": uf.effective(),
                "records": uf.records(),
            }
            return ApiResponse(ok=True, data={"fsResult": res, "state": state}, error=None, ts=_now_iso())
        except Exception as e:
            if rollbackOnFailure:
                for p in copied_abs:
                    try: Path(p).unlink(missing_ok=True)
                    except Exception: pass
                try: remove_uploaded_files_setting(workspaceName, copied_rel)
                except Exception: pass
            raise
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- 업로드된 파일 목록 ----------
@app.get("/workspaces/{workspaceName}/uploads", response_model=ApiResponse)
def get_uploaded_files_api(workspaceName: str):
    try:
        files = list_uploaded_files(workspaceName)
        return ApiResponse(ok=True, data={"files": files}, error=None, ts=_now_iso())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------- 파일 제외/포함 ----------
@app.patch("/workspaces/{workspaceName}/uploads/excluded", response_model=ApiResponse)
def patch_exclude_file_api(workspaceName: str, body: ExcludeBody):
    try:
        res = set_files_excluded(workspaceName, body.filePaths, body.excluded)
        return ApiResponse(ok=True, data=res, error=None, ts=_now_iso())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# ---------- 프로젝트명 매핑 ----------
@app.patch("/workspaces/{workspaceName}/uploads/projects", response_model=ApiResponse)
def patch_set_project_name_api(workspaceName: str, body: ProjectMapBody):
    try:
        res = bulk_set_file_project(workspaceName, body.mapping)
        return ApiResponse(ok=True, data=res, error=None, ts=_now_iso())
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
    
# # C. OCR 추출 및 분개 추출
# # - OCR - 시각화 - 분개추출
# # 중간 오류 발생 처리를 위해 구조 개선 필요 
# def post_run_ocr_and_journal(workspace_name: str) -> None:
#     uploaded_files = get_uploaded_files_path(workspace_name)
#     ocr_results_l = []
#     llm_results_l = []
#     visualization_d = {}
#     journal_entry_l = []
#     for file in uploaded_files:
#         ocr_result = ocr_image_and_save_json_by_extension(file)
#         if ocr_result:
#             # OCR RESULT 폴더에 저장
#             output_path = os.path.join(get_ocr_path(workspace_name), file.split("/")[-1].split(".")[0] + ".json")
#             with open(output_path, "w", encoding="utf-8") as f:
#                 json.dump(ocr_result, f, ensure_ascii=False, indent=4)
#             ocr_results_l.append(output_path)

#             data, candidates, selections = extract_with_locations(ocr_result)
#             json.dump(data, open(os.path.join(get_llm_path(workspace_name), file.split("/")[-1].split(".")[0] + "_data.json"), "w", encoding="utf-8"), indent=4,  ensure_ascii=False)
#             json.dump(candidates, open(os.path.join(get_llm_path(workspace_name), file.split("/")[-1].split(".")[0] + "_candidates.json"), "w", encoding="utf-8"), indent=4,  ensure_ascii=False)
#             json.dump(selections, open(os.path.join(get_llm_path(workspace_name), file.split("/")[-1].split(".")[0] + "_selections.json"), "w", encoding="utf-8"), indent=4,  ensure_ascii=False)
#             llm_results_l.append(os.path.join(get_llm_path(workspace_name), file.split("/")[-1].split(".")[0] + "_data.json"))
            
#             img_path = ocr_result.get("source_image")
#             if img_path:
#                 filename = os.path.basename(img_path)
#                 filename_without_extension = os.path.splitext(filename)[0]
#                 overlay_path = os.path.join(get_visualization_path(workspace_name), f"{filename_without_extension}_overlay.png")
#                 draw_overlays(img_path, selections, overlay_path)
#                 visualization_d[filename] = overlay_path

#             data_dict = get_json_wt_one_value_from_extract_invoice_fields(data)
#             data_dict = [data_dict]
#             data_dict = drop_source_id_from_json(data_dict)
#             result_dict = make_journal_entry(data_dict)
#             record_list = make_journal_entry_to_record_list(result_dict, os.path.basename(file))
#             journal_entry_l.append(record_list)
            

#         # 추후 ocr 실패시 로깅 및 에러처리 강화 필요
#         else:
#             print(f"OCR 추출 실패: {file}")
#     add_ocr_results(workspace_name, ocr_results_l)
#     add_llm_results(workspace_name, llm_results_l)
#     add_visualization(workspace_name, visualization_d)
    
#     journal_path = os.path.join(get_journal_path(workspace_name), "journal_entry.json")
#     json.dump(journal_entry_l, open(journal_path, "w", encoding="utf-8"), indent=4,  ensure_ascii=False)
#     add_journal_drafts(workspace_name, [journal_path])

#     return {"ok": True, "data": {"ocr_results": ocr_results_l}, "error": None, "ts": _now_iso() }

# # - 분개 조회
# def get_journal_drafts(workspace_name: str) -> list[str]:
#     journal_path = os.path.join(get_journal_path(workspace_name), "journal_entry.json")
#     journal_entry_l = json.load(open(journal_path, "r", encoding="utf-8"))
#     return {"ok": True, "data": journal_entry_l, "error": None, "ts": _now_iso() }

# # - 선택 레코드의 VoucherData 조회
# def get_voucher_data(workspace_name: str, file_id: str) -> dict:
#     #voucher_data는 필수 db이므로 워크스페이스 생성시 초기화함
#     voucher_data_ds = read_voucher_data(workspace_name)
#     voucher_data_d = voucher_data_ds.get(file_id, {})
#     if not voucher_data_d:
#         return {"ok": False, "data": None, "error": "Voucher data not found", "ts": _now_iso() }
#     return {"ok": True, "data": voucher_data_d, "error": None, "ts": _now_iso()}

# # - 선택 레코드의 VoucherData 수정
# def patch_update_voucher_data(workspace_name: str, file_id: str, edits: dict) -> None:
#     success, message = update_voucher_data(workspace_name, file_id, edits)
#     if not success:
#         return {"ok": False, "data": None, "error": message, "ts": _now_iso() }
#     return {"ok": True, "data": {"file_id": file_id, "edits": edits}, "error": None, "ts": _now_iso() }

# # - VoucherData 수정 후 분개 새로고침
# def refresh_journal_entries(workspace_name: str) -> None:
#     voucher_data_ds = read_voucher_data(workspace_name)
#     journal_entry_l = []
#     for file_id, data in voucher_data_ds.items():
#         # data_dict = get_json_wt_one_value_from_extract_invoice_fields(data)
#         # data_dict = [data_dict]
#         # data_dict = drop_source_id_from_json(data_dict)
#         result_dict = make_journal_entry(data)
#         record_list = make_journal_entry_to_record_list(result_dict, os.path.basename(file_id))
#         journal_entry_l.append(record_list)
#     journal_path = os.path.join(get_journal_path(workspace_name), "journal_entry.json")
#     json.dump(journal_entry_l, open(journal_path, "w", encoding="utf-8"), indent=4,  ensure_ascii=False)
#     return {"ok": True, "data": json.dumps(journal_entry_l, ensure_ascii=False, indent=4), "error": None, "ts": _now_iso() }

# # - 클릭한 레코드의 시각화 이미지 경로 조회
# def get_visualization_image_path(workspace_name: str, file_id: str) -> str:
#     settings_d = _read_setting(get_setting_file(workspace_name))
#     visualization_d = settings_d.get("files", {}).get("visualization", {})
#     visualization_path = visualization_d.get(file_id, "")
#     if not visualization_path:
#         return {"ok": False, "data": None, "error": "Visualization image not found", "ts": _now_iso() }
#     return {"ok": True, "data": visualization_path, "error": None, "ts": _now_iso() }

# # - 분개 아카이브
# def archive_journal_entry(workspace_name: str) -> None:
#     central_journal_path = os.path.join(get_central_db_path(), "journal_entry.json")
#     central_journal_entry_d = json.load(open(central_journal_path, "r", encoding="utf-8"))
#     joruanl_entry_current_path = os.path.join(get_journal_path(workspace_name), "journal_entry.json")
#     journal_entry_current_l = json.load(open(joruanl_entry_current_path, "r", encoding="utf-8"))
#     central_journal_entry_d[workspace_name] = journal_entry_current_l
#     json.dump(central_journal_entry_d, open(central_journal_path, "w", encoding="utf-8"), indent=4,  ensure_ascii=False)
#     return {"ok": True, "data": json.dumps(central_journal_entry_d, ensure_ascii=False, indent=4), "error": None, "ts": _now_iso() }

# def get_project_list() -> list[str]:
#     from src.entjournal.constants import ALL_NAMES
#     return {"ok": True, "data" : ALL_NAMES, "error": None, "ts": _now_iso() }


app.mount("/static", StaticFiles(directory=str(WORKSPACE_ROOT)), name="static")

# === 1) OCR + LLM + 시각화 + 분개 파이프라인 실행 ===
@app.post("/workspaces/{workspaceName}/pipeline/ocr-journal", response_model=ApiResponse)
def run_ocr_and_journal(workspaceName: str):
    try:
        uploaded_files: list[str] = get_uploaded_files_path(workspaceName)  # 내부 구현
        ocr_results_l, llm_results_l, journal_entry_l = [], [], []
        visualization_d: Dict[str, str] = {}
        initialize_voucher_data(workspaceName, True)
        for file in uploaded_files:
            ocr_result = ocr_image_and_save_json_by_extension(file)
            if not ocr_result:
                # 추후 서버 로깅 권장
                continue

            # OCR JSON 저장
            ocr_dir = get_ocr_path(workspaceName)
            Path(ocr_dir).mkdir(parents=True, exist_ok=True)
            stem = Path(file).stem
            ocr_json_path = os.path.join(ocr_dir, f"{stem}.json")
            with open(ocr_json_path, "w", encoding="utf-8") as f:
                json.dump(ocr_result, f, ensure_ascii=False, indent=4)
            ocr_results_l.append(ocr_json_path)

            # LLM 추출/저장
            data, candidates, selections = extract_with_locations(ocr_result)
            llm_dir = get_llm_path(workspaceName)
            Path(llm_dir).mkdir(parents=True, exist_ok=True)
            with open(os.path.join(llm_dir, f"{stem}_data.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            with open(os.path.join(llm_dir, f"{stem}_candidates.json"), "w", encoding="utf-8") as f:
                json.dump(candidates, f, ensure_ascii=False, indent=4)
            with open(os.path.join(llm_dir, f"{stem}_selections.json"), "w", encoding="utf-8") as f:
                json.dump(selections, f, ensure_ascii=False, indent=4)
            llm_results_l.append(os.path.join(llm_dir, f"{stem}_data.json"))

            # 시각화 이미지 생성
            img_path = ocr_result.get("source_image")
            if img_path:
                filename = os.path.basename(img_path)
                viz_dir = get_visualization_path(workspaceName)
                Path(viz_dir).mkdir(parents=True, exist_ok=True)
                overlay_path = os.path.join(viz_dir, f"{Path(filename).stem}_overlay.png")
                draw_overlays(img_path, selections, overlay_path)
                visualization_d[filename] = overlay_path

            # 분개 생성
            data_dict = get_json_wt_one_value_from_extract_invoice_fields(data)
            data_dict = [data_dict]
            data_dict = drop_source_id_from_json(data_dict)
            update_voucher_data(workspaceName, file, data_dict[0])
            record_list = make_journal_entry(data_dict)
            # record_list = make_journal_entry_to_record_list(result_dict, os.path.basename(file))
            journal_entry_l.extend(record_list)

        # 상태 반영
        add_ocr_results(workspaceName, ocr_results_l)
        add_llm_results(workspaceName, llm_results_l)
        add_visualization(workspaceName, visualization_d)

        #시연용으로 더존만 내림

        sap_journal_entry_l = sap_view(journal_entry_l)
        dzone_journal_entry_l = dzone_view(journal_entry_l)

        jpath = os.path.join(get_journal_path(workspaceName), "journal_entry.json")
        Path(os.path.dirname(jpath)).mkdir(parents=True, exist_ok=True)
        with open(jpath, "w", encoding="utf-8") as f:
            json.dump(dzone_journal_entry_l, f, ensure_ascii=False, indent=4)
        add_journal_drafts(workspaceName, [jpath])

        # 시각화 경로는 /static URL도 같이 내려주자
        viz_for_front = {
            k: (fs_to_static_url(v) or v) for k, v in visualization_d.items()
        }

        return ApiResponse(
            ok=True,
            data={
                "ocrResults": ocr_results_l,
                "llmResults": llm_results_l,
                "journalPath": jpath,
                "visualizations": viz_for_front,
                "journal": dzone_journal_entry_l
            },
            error=None,
            ts=_now_iso()
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === 2) 분개 초안 조회 ===
@app.get("/workspaces/{workspaceName}/journal-drafts", response_model=ApiResponse)
def get_journal_drafts_api(workspaceName: str):
    try:
        jpath = os.path.join(get_journal_path(workspaceName), "journal_entry.json")
        if not Path(jpath).exists():
            return ApiResponse(ok=True, data={"journal": []}, error=None, ts=_now_iso())
        with open(jpath, "r", encoding="utf-8") as f:
            journal_entry_l = json.load(f)
        return ApiResponse(ok=True, data={"journal": journal_entry_l}, error=None, ts=_now_iso())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === 3) 특정 파일의 VoucherData 조회 ===
@app.get("/workspaces/{workspaceName}/voucher-data/{fileId:path}", response_model=ApiResponse)
def get_voucher_data_api(workspaceName: str, fileId: str = ApiPath(..., description="원본 file_id (URL-encoded)")):
    try:
        ds = read_voucher_data(workspaceName)
        vd = ds.get(fileId, {})
        if not vd:
            return ApiResponse(ok=False, data=None, error="Voucher data not found", ts=_now_iso())
        return ApiResponse(ok=True, data={"fileId": fileId, "voucherData": vd}, error=None, ts=_now_iso())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === 4) 특정 파일의 VoucherData 수정 ===
@app.patch("/workspaces/{workspaceName}/voucher-data/{fileId:path}", response_model=ApiResponse)
def patch_update_voucher_data_api(
    workspaceName: str,
    fileId: str = ApiPath(...),
    body: VoucherUpdateBody = Body(...)
):
    try:
        success, message = update_voucher_data(workspaceName, fileId, body.edits)
        if not success:
            return ApiResponse(ok=False, data=None, error=message, ts=_now_iso())
        return ApiResponse(ok=True, data={"fileId": fileId, "edits": body.edits}, error=None, ts=_now_iso())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === 5) VoucherData 기반 분개 재생성(새로고침) ===
@app.post("/workspaces/{workspaceName}/journal/refresh", response_model=ApiResponse)
def refresh_journal_entries_api(workspaceName: str):
    try:
        ds = read_voucher_data(workspaceName)
        journal_entry_l = []
        for file_id, data in ds.items():
            record_list = make_journal_entry(data)
            # record_list = make_journal_entry_to_record_list(result_dict, os.path.basename(file_id))
            journal_entry_l.extend(record_list)
        jpath = os.path.join(get_journal_path(workspaceName), "journal_entry.json")
        Path(os.path.dirname(jpath)).mkdir(parents=True, exist_ok=True)
        with open(jpath, "w", encoding="utf-8") as f:
            json.dump(journal_entry_l, f, ensure_ascii=False, indent=4)
        return ApiResponse(ok=True, data={"journal": journal_entry_l, "journalPath": jpath}, error=None, ts=_now_iso())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === 6) 클릭한 레코드의 시각화 이미지 경로 조회 ===
@app.get("/workspaces/{workspaceName}/visualizations/{fileId:path}", response_model=ApiResponse)
def get_visualization_image_path_api(workspaceName: str, fileId: str = ApiPath(...)):
    try:
        settings_d = _read_setting(get_setting_file(workspaceName))
        visualization_d = settings_d.get("files", {}).get("visualization", {})
        fs_path = visualization_d.get(os.path.basename(fileId), "")
        if not fs_path:
            return ApiResponse(ok=False, data=None, error="Visualization image not found", ts=_now_iso())
        url = fs_to_static_url(fs_path) or fs_path
        return ApiResponse(ok=True, data={"fileId": fileId, "imageUrl": url, "fsPath": fs_path}, error=None, ts=_now_iso())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# === 7) 분개 아카이브 ===
@app.post("/workspaces/{workspaceName}/journal/archive", response_model=ApiResponse)
def archive_journal_entry_api(workspaceName: str):
    try:
        central = os.path.join(get_central_db_path(), "journal_entry.json")
        Path(os.path.dirname(central)).mkdir(parents=True, exist_ok=True)
        central_d = {}
        if Path(central).exists():
            with open(central, "r", encoding="utf-8") as f:
                central_d = json.load(f)

        current_path = os.path.join(get_journal_path(workspaceName), "journal_entry.json")
        if not Path(current_path).exists():
            return ApiResponse(ok=False, data=None, error="Current journal not found", ts=_now_iso())
        with open(current_path, "r", encoding="utf-8") as f:
            current_l = json.load(f)

        central_d[workspaceName] = current_l
        with open(central, "w", encoding="utf-8") as f:
            json.dump(central_d, f, ensure_ascii=False, indent=4)

        return ApiResponse(ok=True, data={"archivePath": central, "workspaceName": workspaceName}, error=None, ts=_now_iso())
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
if __name__ == "__main__":
    # get_voucher_data_api("wshopp", "C:\\Users\\ykim513\\Desktop\\PythonWorkspace\\Entocr\\workspace\\wshopp\\input_files\\HUNTRIX.png")
    # refresh_journal_entries_api("wshopp")
    # get_visualization_image_path_api("wshopp","visualizations/workspace/wshopp/input_files/HUNTRIX.png")
    # archive_journal_entry_api("wshopp")
    run_ocr_and_journal("wshopp")
    print("done")