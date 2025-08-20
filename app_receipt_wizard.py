# -*- coding: utf-8 -*-
"""
Receipt OCR → LLM Review UI (Streamlit Wizard)
- 상단 탭: Upload / Extract / Review / Journal Entry / Visual Verify / Export
- 좌측: 진행/큐, 우측: 각 탭 본문
"""

import io
import os
import json
import time
import zipfile
import shutil
import tempfile
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass

import pandas as pd
import streamlit as st
from PIL import Image

# ==== 프로젝트 내부 유틸 (경로는 프로젝트 구조에 맞춰 수정하세요) ====
# LLM 추출 + 위치 매칭 + 시각화 유틸
from src.ant.llm_main import (
    extract_with_locations,
    draw_overlays,
    export_thumbnails,
)
# OCR: 이미 구현됨
# from your_ocr_module import ocr_image_and_save_json_by_extension
from src.entocr.ocr_main import ocr_image_and_save_json_by_extension
# (선택) 카테고리/분개 매핑에 활용
try:
    from src.ant.constants import CATEGORY
except Exception:
    CATEGORY = []

# ========================= 기본 설정 =========================
st.set_page_config(page_title="AutoVoucher AI", page_icon="🧾", layout="wide")
st.title("🧾 AutoVoucher AI")

# ========================= 상태 초기화 =========================
def _init_state():
    ss = st.session_state
    ss.setdefault("workdir", tempfile.mkdtemp(prefix="st_wizard_"))
    ss.setdefault("images", [])            # 업로드된 이미지 경로들
    ss.setdefault("queue", [])             # 처리 대기 큐 (이미지 경로)
    ss.setdefault("results", {})           # {img_path: {"data","candidates","selections","ocr_json"}}
    ss.setdefault("overlay_paths", {})     # {img_path: overlay.png}
    ss.setdefault("thumb_dirs", {})        # {img_path: dir}
    ss.setdefault("logs", [])              # 전체 로그
    ss.setdefault("errors", {})            # {img_path: "에러메시지"}
    ss.setdefault("model_name", "gpt4o_latest")
    ss.setdefault("lang", "kor+eng")
    ss.setdefault("deskew", False)
    ss.setdefault("denoise", False)
    ss.setdefault("vat_rate", 0.1)         # 분개용 VAT 가정 (필요시 편집)
    ss.setdefault("mapping_profile", "Default")
    ss.setdefault("je_rows_cache", None)   # 분개 미리보기 DataFrame
    ss.setdefault("review_df_cache", None) # 리뷰 테이블 DataFrame
    ss.setdefault("selected_file_for_visual", None)
    ss.setdefault("selected_fields_for_visual", [])  # e.g. ["거래처","금액"]
_init_state()

# ========================= 공통 유틸 =========================
def _is_image(path_or_name: str) -> bool:
    return path_or_name.lower().endswith((".png",".jpg",".jpeg",".webp",".bmp",".tif",".tiff"))

def _save_uploaded_files(files: List) -> List[str]:
    """Streamlit 업로더로 받은 파일들을 임시 폴더에 저장"""
    paths = []
    save_dir = os.path.join(st.session_state["workdir"], "uploads")
    os.makedirs(save_dir, exist_ok=True)
    for f in files:
        dest = os.path.join(save_dir, f.name)
        with open(dest, "wb") as out:
            out.write(f.read())
        paths.append(dest)
    return paths

def _extract_zip(file_bytes: bytes) -> List[str]:
    """ZIP에서 이미지 추출"""
    save_dir = os.path.join(st.session_state["workdir"], "uploads_zip")
    os.makedirs(save_dir, exist_ok=True)
    paths = []
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
        for n in z.namelist():
            if n.endswith("/"): 
                continue
            if not _is_image(n): 
                continue
            fname = os.path.basename(n)
            dest = os.path.join(save_dir, fname)
            with z.open(n) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
            paths.append(dest)
    return sorted(paths)

def _log(msg: str):
    st.session_state["logs"].append(f"[{time.strftime('%H:%M:%S')}] {msg}")

def _queue_images(paths: List[str]):
    ss = st.session_state
    for p in paths:
        if p not in ss["images"]:
            ss["images"].append(p)
        if p not in ss["queue"] and p not in ss["results"]:
            ss["queue"].append(p)

def _short(s: str, n: int = 18) -> str:
    s = str(s)
    return s if len(s) <= n else s[:n] + "…"

def _first_val(obj_list: List[Dict[str, Any]]) -> str:
    """[{"value":..., "source_id":...}] 중 첫 value만 반환(없으면 빈문자열)"""
    if isinstance(obj_list, list) and obj_list:
        return str(obj_list[0].get("value",""))
    return ""

def _to_number(s: str) -> Optional[float]:
    try:
        return float(str(s).replace(",", "").strip())
    except Exception:
        return None

# ========================= Upload 탭 =========================
def tab_upload():
    left, right = st.columns([1,2], gap="large")

    with left:
        st.subheader("진행/큐")
        total = len(st.session_state["images"])
        done = len(st.session_state["results"])
        waiting = len(st.session_state["queue"])
        st.metric("총 이미지", total)
        st.metric("완료", done)
        st.metric("대기", waiting)
        if st.session_state["errors"]:
            st.error(f"실패 {len(st.session_state['errors'])}건")

        # st.divider()
        # st.subheader("옵션")
        # st.session_state["model_name"] = st.text_input("LLM 모델", st.session_state["model_name"])
        # st.session_state["lang"] = st.selectbox("OCR 언어(참고용)", ["kor", "eng", "kor+eng"], index=2)
        # st.session_state["deskew"] = st.checkbox("전처리: Deskew", value=st.session_state["deskew"])
        # st.session_state["denoise"] = st.checkbox("전처리: Denoise", value=st.session_state["denoise"])

        # st.info("※ 전처리 옵션은 실제 OCR 함수 구현에 반영되어야 합니다. 현재 화면은 옵션 전달만 합니다.")

    with right:
        st.subheader("1) 이미지 업로드")
        imgs = st.file_uploader("여러 이미지 선택", accept_multiple_files=True, type=["pdf","png","jpg","jpeg","webp","tif","tiff","bmp"])
        # zf = st.file_uploader("또는 ZIP 업로드", type=["zip"])

        colx, coly = st.columns([1,1])
        with colx:
            if st.button("이미지 추가"):
                if imgs:
                    paths = _save_uploaded_files(imgs)
                    _queue_images(paths)
                    _log(f"이미지 {len(paths)}건 등록")
                    st.success("대기 작업이 준비되었습니다. 상단 탭에서 **2. Extract**를 클릭해 처리하세요.")

                else:
                    st.warning("이미지를 선택하세요.")
        # with coly:
        #     if st.button("ZIP 추출"):
        #         if zf:
        #             paths = _extract_zip(zf.getvalue())
        #             _queue_images(paths)
        #             _log(f"ZIP에서 이미지 {len(paths)}건 추출")
        #         else:
        #             st.warning("ZIP 파일을 업로드하세요.")

        st.markdown("#### 업로드 목록")
        if st.session_state["images"]:
            df = pd.DataFrame({
                "file": [os.path.basename(p) for p in st.session_state["images"]],
                "path": st.session_state["images"],
                "status": ["✅" if p in st.session_state["results"] else ("⏳" if p in st.session_state["queue"] else "•") for p in st.session_state["images"]],
            })
            st.dataframe(df, use_container_width=True, hide_index=True, height=320)
        else:
            st.info("업로드된 이미지가 없습니다.")

        # st.divider()
        # if st.button("시작(Start)", type="primary"):
        #     # 대기 큐 구성
        #     for p in st.session_state["images"]:
        #         if p not in st.session_state["results"] and p not in st.session_state["queue"]:
        #             st.session_state["queue"].append(p)

        #     st.success("대기 작업이 준비되었습니다. 상단 탭에서 **2. Extract**를 클릭해 처리하세요.")
        #     st.toast("대기 큐 준비 완료 → Extract 탭으로 이동해 주세요.")
            # 새로고침으로 좌측 ‘대기’ 카운터만 업데이트하고 탭 전환은 하지 않음
            # st.rerun()

# ========================= Extract 탭 =========================
def _process_queue():
    ss = st.session_state
    q = ss["queue"][:]
    n = len(q)
    if not n:
        st.info("대기 중인 작업이 없습니다.")
        return

    prog = st.progress(0.0, text="처리 시작")

    for i, img_path in enumerate(q, 1):
        # try:
        _log(f"[{os.path.basename(img_path)}] OCR 시작")
        # (1) OCR: 이미 구현된 함수 호출
        output_path, ocr_json = ocr_image_and_save_json_by_extension(img_path)
        # # 방어: source_image 기본값
        # if "source_image" not in ocr_json:
        #     ocr_json["source_image"] = img_path

        # (2) LLM 추출 + 위치정보
        data, candidates, selections = extract_with_locations(ocr_json, model_name=st.session_state["model_name"])

        # (3) 오버레이/썸네일 생성
        overlay_path = os.path.join(ss["workdir"], "overlay", os.path.basename(img_path) + ".overlay.png")
        os.makedirs(os.path.dirname(overlay_path), exist_ok=True)
        draw_overlays(img_path, selections, overlay_path)

        thumbs_dir = os.path.join(ss["workdir"], "thumbs", os.path.splitext(os.path.basename(img_path))[0])
        os.makedirs(thumbs_dir, exist_ok=True)
        export_thumbnails(img_path, selections, thumbs_dir, margin=0.06)

        # 결과 저장
        ss["results"][img_path] = {
            "data": data,
            "candidates": candidates,
            "selections": selections,
            "ocr_json": ocr_json,
        }
        ss["overlay_paths"][img_path] = overlay_path
        ss["thumb_dirs"][img_path] = thumbs_dir
        _log(f"[{os.path.basename(img_path)}] 처리 완료")

        # except Exception as e:
        #     ss["errors"][img_path] = str(e)
        #     _log(f"[{os.path.basename(img_path)}] 처리 실패: {e}")

        # finally:
            # 큐에서 제거
        if img_path in ss["queue"]:
            ss["queue"].remove(img_path)
        prog.progress(i/n, text=f"처리 중... ({i}/{n})")

    prog.empty()

def tab_extract():
    left, right = st.columns([1,2], gap="large")

    with left:
        st.subheader("진행/큐")
        total = len(st.session_state["images"])
        done = len(st.session_state["results"])
        waiting = len(st.session_state["queue"])
        st.metric("총 이미지", total)
        st.metric("완료", done)
        st.metric("대기", waiting)

        st.divider()
        if st.button("OCR 처리 시작", type="primary"):
            _process_queue()

        if st.button("실패건 재시도"):
            for p, msg in list(st.session_state["errors"].items()):
                if p not in st.session_state["queue"] and p not in st.session_state["results"]:
                    st.session_state["queue"].append(p)
            st.success("재시도 큐에 등록 완료")

        st.divider()
        st.subheader("로그")
        st.text("\n".join(st.session_state["logs"][-200:]))

    with right:
        # st.subheader("파이프라인 단계 체크")
#         st.markdown("""
# - ✅ Preprocess (옵션 전달)
# - ✅ OCR (외부 함수 호출)
# - ✅ LLM Extract (extract_with_locations)
# - ✅ Postprocess (사후검증·정규화)
# - ✅ Validate (필수 필드 확인)
#         """.strip())

        # 현재 처리 중 샘플(최근 완료 파일)
        if st.session_state["results"]:
            last_img = list(st.session_state["results"].keys())[-1]
            sample = st.session_state["results"][last_img]["data"]
            st.markdown("#### 최근 결과 샘플 (상위 5~7 키)")
            preview = {
                "file": os.path.basename(last_img),
                "날짜": _first_val(sample.get("날짜", [])),
                "거래처": _first_val(sample.get("거래처", [])),
                "금액": _first_val(sample.get("금액", [])),
                "유형": ", ".join(sample.get("유형", [])),
                "사업자등록번호": _first_val(sample.get("사업자등록번호", [])),
                "대표자": _first_val(sample.get("대표자", [])),
                "주소": _first_val(sample.get("주소", [])),
            }
            st.json(preview)
            # if st.button("Review 단계로 진행 안내", type="primary"):
            st.success("추출이 완료되었습니다. 상단 탭 **3. Review**를 클릭해 데이터를 검토/수정하세요.")
            st.toast("다음 단계: Review 탭에서 데이터 검토")
        else:
            st.info("아직 완료된 결과가 없습니다.")

# ========================= Review 탭 =========================
def _build_review_table() -> pd.DataFrame:
    """results → 편집 가능한 표로 구성"""
    rows = []
    for p, res in st.session_state["results"].items():
        d = res["data"]
        rows.append({
            "file_id": os.path.basename(p),
            "path": p,
            "vendor": _first_val(d.get("거래처", [])),
            "biz_no": _first_val(d.get("사업자등록번호", [])),
            "date": _first_val(d.get("날짜", [])),
            "amount": _first_val(d.get("금액", [])),
            "category": ", ".join(d.get("유형", [])),
            "representative": _first_val(d.get("대표자", [])),
            "address": _first_val(d.get("주소", [])),
            "confidence": "",  # 필요 시 추정치/후보 점수 넣기
            "issues": "",      # 유효성 실패 요약
        })
    df = pd.DataFrame(rows)
    # 간단 유효성 표시
    warn = []
    for i, r in df.iterrows():
        msg = []
        # 사업자번호 10자리 여부
        digits = "".join([c for c in str(r["biz_no"]) if c.isdigit()])
        if digits and len(digits) != 10:
            msg.append("사업자번호 형식")
        # 날짜 YYYY-MM-DD 추정
        if r["date"] and not pd.to_datetime(str(r["date"]), errors="coerce"):
            msg.append("날짜 형식")
        # 금액 숫자여부
        if _to_number(r["amount"]) is None:
            msg.append("금액 형식")
        warn.append(", ".join(msg))
    df["issues"] = warn
    return df

def tab_review():
    left, right = st.columns([1,2], gap="large")

    with left:
        st.subheader("데이터 세트 선택")
        st.caption("현재는 LLM 보강 결과만 표시합니다. (원본 OCR/병합 결과 추가 가능)")
        st.session_state["dataset_sel"] = st.selectbox("Dataset", ["LLM Result"], index=0)

        st.divider()
        st.subheader("품질 패널")
        df = st.session_state.get("review_df_cache")
        if df is not None and not df.empty:
            total = len(df)
            bad = (df["issues"] != "").sum()
            st.metric("총 행", total)
            st.metric("유효성 경고", bad)
            st.info("자동 수정 제안 토글(데모): 정규식/룰 기반 보정 로직을 여기에 연결 가능")
        else:
            st.info("표가 생성되면 요약이 표시됩니다.")

        st.divider()
        st.subheader("Visual Link")
        st.caption("선택 행의 필드를 Visual Verify 탭에서 하이라이트합니다.")
        sel_fields = st.multiselect("하이라이트할 필드", ["vendor","biz_no","date","amount","representative","address"], default=["vendor","amount"])
        if st.button("선택 행 → Visual Verify 이동"):
            idxs = st.session_state.get("review_sel_rows", [])
            if idxs:
                idx = idxs[0]
                row = df.iloc[idx]
                # 파일/필드 매핑
                st.session_state["selected_file_for_visual"] = row["path"]
                # 필드명 변환
                mapping = {
                    "vendor":"거래처","biz_no":"사업자등록번호","date":"날짜",
                    "amount":"금액","representative":"대표자","address":"주소",
                }
                st.session_state["selected_fields_for_visual"] = [mapping[x] for x in sel_fields]
                st.session_state["selected_file_for_visual"] = row["path"]
                st.session_state["selected_fields_for_visual"] = [mapping[x] for x in sel_fields]
                st.success("선택된 파일/필드가 설정되었습니다. 상단 탭 **5. Visual Verify**를 클릭해 확인하세요.")
                st.toast("다음 단계: Visual Verify 탭으로 이동해서 하이라이트 확인")
            else:
                st.warning("먼저 행을 선택하세요.")

    with right:
        st.subheader("3) Review / 편집")
        # 표 구축/캐시
        df = _build_review_table()
        st.session_state["review_df_cache"] = df.copy()
        edited = st.data_editor(
            df,
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True,
            key="review_table",
            on_change=None,
            column_config={
                "path": st.column_config.Column(disabled=True),
                "file_id": st.column_config.Column(disabled=True),
                "issues": st.column_config.Column(help="유효성 경고 요약"),
            }
        )

            # selection_mode="single-row",
        # 선택된 행 인덱스 추출
        sel = st.session_state.get("review_table", {}).get("selection", {})
        st.session_state["review_sel_rows"] = sel.get("rows", [])

        colx, coly = st.columns([1,1])
        with colx:
            if st.button("테이블 변경사항 적용"):
                # 테이블 편집 내용을 results에 반영
                for _, r in edited.iterrows():
                    path = r["path"] 
                    if path not in st.session_state["results"]:
                        continue
                    d = st.session_state["results"][path]["data"]
                    print(d)
                    # 편집값은 value만 갱신(source_id는 None 처리)
                    def _set(k_json, val_str):
                        d.setdefault(k_json, [])
                        if d[k_json]:
                            d[k_json][0]["value"] = str(val_str)
                            d[k_json][0]["source_id"] = d[k_json][0].get("source_id") or None
                        else:
                            d[k_json] = [{"value": str(val_str), "source_id": None}]
                    _set("거래처", r["vendor"])
                    _set("사업자등록번호", r["biz_no"])
                    _set("날짜", r["date"])
                    _set("금액", r["amount"])
                    _set("대표자", r["representative"])
                    _set("주소", r["address"])
                st.success("반영 완료")

        with coly:
            if st.button("유효성 재검사"):
                st.session_state["review_df_cache"] = _build_review_table()
                st.info("검사 완료")

# ========================= Journal Entry 탭 =========================
# 간단 매핑 예시(프로덕션에서는 별도 설정/DB 연결 권장)
ACCOUNT_MAP = {
    # category → (debit_account, credit_account)
    # 실제 회사/프로젝트 매핑에 맞춰 커스터마이즈하세요.
    "기본": ("비용(기타)", "미지급금"),
    "판매대행수수료": ("수수료비용", "미지급금"),
    "운송비": ("운반비", "미지급금"),
    "임차료": ("임차료", "미지급금"),
    "리스/렌탈": ("임차료", "미지급금"),
}

def _build_journal_preview(df_review: pd.DataFrame, vat_rate: float = 0.1) -> pd.DataFrame:
    """
    Review 표 → 분개 미리보기 구성 (간단 버전)
    - 차변: 카테고리별 비용
    - 대변: 미지급금 (또는 카드/현금 등으로 확장 가능)
    - VAT 별도 라인 미생성(간단화). 필요 시 공급가/세액 분리 로직 추가.
    """
    rows = []
    for _, r in df_review.iterrows():
        amount = _to_number(r["amount"]) or 0.0
        category = str(r.get("category") or "").split(",")[0].strip() or "기본"
        debit_acc, credit_acc = ACCOUNT_MAP.get(category, ACCOUNT_MAP["기본"])
        rows.append({
            "date": r["date"],
            "account": debit_acc,
            "debit": amount,
            "credit": 0.0,
            "description": f"{r['vendor']} {category}",
            "vendor": r["vendor"],
            "doc_no": r["biz_no"],
            "cost_center": "",
            "project": "",
            "file_id": r["file_id"],
        })
        rows.append({
            "date": r["date"],
            "account": credit_acc,
            "debit": 0.0,
            "credit": amount,
            "description": f"{r['vendor']} {category}",
            "vendor": r["vendor"],
            "doc_no": r["biz_no"],
            "cost_center": "",
            "project": "",
            "file_id": r["file_id"],
        })
    return pd.DataFrame(rows)

def tab_journal_entry():
    left, right = st.columns([1,2], gap="large")

    with left:
        st.subheader("매핑 프로필")
        # st.session_state["mapping_profile"] = st.selectbox("Profile", ["Default"], index=0)
        # st.session_state["vat_rate"] = st.number_input("VAT (%)", value=int(st.session_state["vat_rate"]*100), min_value=0, max_value=20, step=1) / 100.0

        st.markdown("**규칙 요약 (예시)**")
        st.write(pd.DataFrame([
            {"조건":"category=판매대행수수료","차변":"수수료비용","대변":"미지급금"},
            {"조건":"category=운송비","차변":"운반비","대변":"미지급금"},
            {"조건":"default","차변":"비용(기타)","대변":"미지급금"},
        ]))

    with right:
        st.subheader("4) Journal Entry 미리보기")
        df_review = st.session_state.get("review_df_cache")
        if df_review is None or df_review.empty:
            st.info("Review 탭에서 표가 생성되면 여기서 미리보기를 볼 수 있습니다.")
            return

        je = _build_journal_preview(df_review, st.session_state["vat_rate"])
        # 차대변 합계 검증
        total_debit = float(je["debit"].sum())
        total_credit = float(je["credit"].sum())
        ok = abs(total_debit - total_credit) < 1e-6

        st.dataframe(je, use_container_width=True, hide_index=True)
        st.metric("차변 합계", f"{total_debit:,.0f}")
        st.metric("대변 합계", f"{total_credit:,.0f}")
        if not ok:
            st.error("차대변 합계가 0이 아닙니다. 매핑 규칙/금액을 확인하세요.")
        else:
            st.success("차대변 합계 일치")

        st.session_state["je_rows_cache"] = je

# ========================= Visual Verify 탭 =========================
def _filter_selections(selections: List[Dict[str,Any]], fields: List[str]) -> List[Dict[str,Any]]:
    if not fields:
        return selections
    return [s for s in selections if s.get("field") in fields]

def tab_visual_verify():
    left, right = st.columns([1,2], gap="large")

    with left:
        st.subheader("파일 리스트 / 썸네일")
        imgs = st.session_state["images"]
        if not imgs:
            st.info("업로드된 이미지가 없습니다.")
            return
        current = st.selectbox("파일 선택", options=imgs, format_func=lambda p: os.path.basename(p),
                               index=max(0, imgs.index(st.session_state["selected_file_for_visual"]) if st.session_state["selected_file_for_visual"] in imgs else 0))
        st.session_state["selected_file_for_visual"] = current

        # 필드 필터
        fields = st.multiselect("레이어(필드) 필터", ["날짜","거래처","금액","사업자등록번호","대표자","주소"],
                                default=st.session_state.get("selected_fields_for_visual") or ["날짜","거래처","금액"])
        st.session_state["selected_fields_for_visual"] = fields

        # 썸네일 보여주기
        tdir = st.session_state["thumb_dirs"].get(current)
        if tdir and os.path.isdir(tdir):
            files = sorted([os.path.join(tdir, f) for f in os.listdir(tdir) if _is_image(f)])
            if files:
                ncol = min(4, len(files))
                cols = st.columns(ncol)
                for i, p in enumerate(files):
                    with cols[i % ncol]:
                        st.image(p, caption=os.path.basename(p), use_container_width=True)

    with right:
        st.subheader("5) 시각 검증")
        cur = st.session_state["selected_file_for_visual"]
        if not cur or cur not in st.session_state["results"]:
            st.info("좌측에서 파일을 선택하세요.")
            return

        res = st.session_state["results"][cur]
        sels = _filter_selections(res["selections"], fields)

        # 동적 오버레이 생성 (필드 필터 반영)
        overlay_tmp = os.path.join(st.session_state["workdir"], "overlay_dynamic", os.path.basename(cur) + ".overlay.png")
        os.makedirs(os.path.dirname(overlay_tmp), exist_ok=True)
        draw_overlays(cur, sels, overlay_tmp)

        col1, col2 = st.columns(2)
        with col1:
            st.image(cur, caption="원본", use_container_width=True)
        with col2:
            with open(overlay_tmp, "rb") as f:
                st.image(f.read(), caption="오버레이(필터 적용)", use_container_width=True)

        st.markdown("**선택 항목 상세**")
        st.dataframe(pd.DataFrame(sels), use_container_width=True, hide_index=True)

        st.info("양방향 하이라이트/좌표 편집은 web canvas 기반으로 확장 가능 (Konva.js / streamlit-drawable-canvas).")

# ========================= Export 탭 =========================
def tab_export():
    left, right = st.columns([1,2], gap="large")

    with left:
        st.subheader("내보내기 옵션")
        fmt = st.multiselect("데이터 포맷", ["CSV","XLSX","JSON"], default=["CSV","JSON"])
        # erp = st.selectbox("ERP 프리셋", ["Generic","SAP","더존","영림원"], index=0)
        # st.caption("※ ERP 포맷은 컬럼/헤더/인코딩 매핑을 적용해야 합니다. (데모에서는 Generic만 출력)")

    with right:
        st.subheader("6) Export")
        # Review 표 / JE 표 가져오기
        df_review = st.session_state.get("review_df_cache")
        if df_review is None:
            df_review = pd.DataFrame()
        df_je = st.session_state.get("je_rows_cache")
        if df_je is None:
            df_je = pd.DataFrame()

        colx, coly = st.columns([1,1])
        with colx:
            st.markdown("**추출 데이터 (Review)**")
            st.dataframe(df_review, use_container_width=True, hide_index=True, height=220)
            if not df_review.empty:
                if "CSV" in fmt:
                    st.download_button("Download Extracted (CSV)",
                        data=df_review.to_csv(index=False).encode("utf-8-sig"),
                        file_name="extracted.csv", mime="text/csv")
                if "JSON" in fmt:
                    st.download_button("Download Extracted (JSON)",
                        data=df_review.to_json(orient="records", force_ascii=False).encode("utf-8"),
                        file_name="extracted.json", mime="application/json")
                if "XLSX" in fmt:
                    buf = io.BytesIO()
                    with pd.ExcelWriter(buf, engine="xlsxwriter") as writer:
                        df_review.to_excel(writer, index=False, sheet_name="extracted")
                    st.download_button("Download Extracted (XLSX)",
                        data=buf.getvalue(), file_name="extracted.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        with coly:
            st.markdown("**Journal Entry 미리보기**")
            st.dataframe(df_je, use_container_width=True, hide_index=True, height=220)
            if not df_je.empty:
                if "CSV" in fmt:
                    st.download_button("Download JE (CSV)",
                        data=df_je.to_csv(index=False).encode("utf-8-sig"),
                        file_name="journal_entry.csv", mime="text/csv")
                if "JSON" in fmt:
                    st.download_button("Download JE (JSON)",
                        data=df_je.to_json(orient="records", force_ascii=False).encode("utf-8"),
                        file_name="journal_entry.json", mime="application/json")
                if "XLSX" in fmt:
                    buf2 = io.BytesIO()
                    with pd.ExcelWriter(buf2, engine="xlsxwriter") as writer:
                        df_je.to_excel(writer, index=False, sheet_name="JE")
                    st.download_button("Download JE (XLSX)",
                        data=buf2.getvalue(), file_name="journal_entry.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        st.divider()
        # 전체 아카이브 (표 + 원본 + 오버레이 + 주석JSON + 로그)
        if st.button("모든 결과 ZIP 다운로드"):
            bufz = io.BytesIO()
            with zipfile.ZipFile(bufz, "w", zipfile.ZIP_DEFLATED) as z:
                # 표
                if not df_review.empty:
                    z.writestr("extracted.csv", df_review.to_csv(index=False))
                if not df_je.empty:
                    z.writestr("journal_entry.csv", df_je.to_csv(index=False))
                # 로그
                z.writestr("logs.txt", "\n".join(st.session_state["logs"]))
                # 개별 파일: 원본/오버레이/결과 JSON/후보/선택/ocr_json
                for p, res in st.session_state["results"].items():
                    base = os.path.splitext(os.path.basename(p))[0]
                    # 원본
                    if os.path.exists(p):
                        z.write(p, arcname=f"files/{os.path.basename(p)}")
                    # 오버레이
                    ov = st.session_state["overlay_paths"].get(p)
                    if ov and os.path.exists(ov):
                        z.write(ov, arcname=f"overlay/{os.path.basename(ov)}")
                    # JSON들
                    z.writestr(f"results/{base}.data.json", json.dumps(res["data"], ensure_ascii=False, indent=2))
                    z.writestr(f"results/{base}.candidates.json", json.dumps(res["candidates"], ensure_ascii=False, indent=2))
                    z.writestr(f"results/{base}.selections.json", json.dumps(res["selections"], ensure_ascii=False, indent=2))
                    z.writestr(f"results/{base}.ocr.json", json.dumps(res["ocr_json"], ensure_ascii=False, indent=2))
            st.download_button("Download ZIP Package", data=bufz.getvalue(), file_name="receipt_package.zip", mime="application/zip")

# ========================= 탭 네비게이션 =========================
tabs = st.tabs(["1. Upload", "2. Extract", "3. Review", "4. Journal Entry", "5. Visual Verify", "6. Export"])
with tabs[0]:
    tab_upload()
with tabs[1]:
    tab_extract()
with tabs[2]:
    tab_review()
with tabs[3]:
    tab_journal_entry()
with tabs[4]:
    tab_visual_verify()
with tabs[5]:
    tab_export()


