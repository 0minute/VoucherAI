import io, os, json, time, zipfile, shutil
from typing import Dict, Any, List

import pandas as pd
import streamlit as st
from PIL import Image

# ---- 프로젝트 내부 유틸 (경로는 프로젝트 구조에 맞게 수정하세요) ----
# LLM 추출 + 위치 매칭 + 시각화 유틸
from src.ant.llm_main import extract_with_locations, draw_overlays, export_thumbnails
from src.entjournal.journal_main import create_dataframe_from_json, to_excel_bytes, to_csv_bytes, get_json_wt_one_value_from_extract_invoice_fields, drop_source_id_from_json, get_result_jsons

# 이미 구현된 OCR 래퍼 (이미지 경로 -> OCR JSON 반환 & (선택) 파일 저장)
# ※ import 경로는 실제 위치로 변경하세요.
from src.entocr.ocr_main import ocr_image_and_save_json_by_extension

# ========================= Streamlit 기본 설정 =========================
st.set_page_config(page_title="ZIP OCR & 시각화", page_icon="🧾", layout="wide")
st.title("🧾 ZIP 업로드 · 이미지 일괄 OCR · 결과 시각화")

# ========================= 경로/캐시 유틸 =============================
def _mk_tmp_dir(root: str = ".st_tmp") -> str:
    path = os.path.join(".", root, time.strftime("%Y%m%d-%H%M%S"))
    os.makedirs(path, exist_ok=True)
    return path

def _is_image(name: str) -> bool:
    return name.lower().endswith((".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"))

@st.cache_data(show_spinner=False)
def _extract_zip(file_bytes: bytes, out_dir: str) -> List[str]:
    """ZIP에서 이미지 파일만 추출해 저장하고 경로 리스트 반환."""
    os.makedirs(out_dir, exist_ok=True)
    paths = []
    with zipfile.ZipFile(io.BytesIO(file_bytes)) as z:
        for n in z.namelist():
            if n.endswith("/"):
                continue
            if not _is_image(n):
                continue
            fname = os.path.basename(n)
            dest = os.path.join(out_dir, fname)
            with z.open(n) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
            paths.append(dest)
    return sorted(paths)

# ========================= 사이드바 / 입력 ============================
st.sidebar.header("업로드")
zip_file = st.sidebar.file_uploader("이미지 ZIP 업로드", type=["zip"])

st.sidebar.header("옵션")
model_name = st.sidebar.text_input("LLM 모델명", value="gpt4o_latest")
thumb_margin = st.sidebar.slider("썸네일 여백(%)", 0, 15, 6, step=1)
run_all = st.sidebar.button("ZIP 처리 실행", type="primary")

# 상태 저장소
if "workdir" not in st.session_state:
    st.session_state["workdir"] = ""
if "images" not in st.session_state:
    st.session_state["images"] = []         # 이미지 경로 목록
if "results" not in st.session_state:
    st.session_state["results"] = {}        # {image_path: {"data":..., "candidates":..., "selections":..., "ocr_json":...}}
if "overlay_paths" not in st.session_state:
    st.session_state["overlay_paths"] = {}  # {image_path: overlay_path}
if "thumb_dirs" not in st.session_state:
    st.session_state["thumb_dirs"] = {}     # {image_path: dir}

# ========================= 처리 실행 ================================
if run_all:
    if not zip_file:
        st.sidebar.error("ZIP 파일을 업로드하세요.")
    else:
        workdir = _mk_tmp_dir()
        st.session_state["workdir"] = workdir
        with st.spinner("ZIP 압축 해제 중..."):
            imgs = _extract_zip(zip_file.getvalue(), os.path.join(workdir, "images"))

        if not imgs:
            st.error("ZIP 안에서 이미지 파일을 찾지 못했습니다.")
        else:
            st.session_state["images"] = imgs
            st.success(f"이미지 {len(imgs)}장을 추출했습니다.")

            progress = st.progress(0.0, text="처리 중...")
            for i, img_path in enumerate(imgs, 1):
                # try:
                # 1) OCR: 이미 구현된 함수 호출
                #    - 권장 시그니처(예시): ocr_image_and_save_json_by_extension(image_path: str) -> Dict[str, Any]
                #    - 함수 내부에서 JSON 파일 저장까지 수행해도 되고, 여기서는 반환 객체만 사용합니다.
                output_path, ocr_json = ocr_image_and_save_json_by_extension(img_path)

                # (방어) 최소 필드 보정
                if "source_image" not in ocr_json:
                    ocr_json["source_image"] = img_path

                # 2) LLM 추출 + 위치 정보 (우리 파이프라인)
                data, candidates, selections = extract_with_locations(ocr_json, model_name=model_name)
                
                # 3) 오버레이/썸네일 생성
                out_overlay = os.path.join(workdir, "overlay", os.path.basename(img_path) + ".overlay.png")
                os.makedirs(os.path.dirname(out_overlay), exist_ok=True)
                draw_overlays(img_path, selections, out_overlay)

                thumbs_dir = os.path.join(workdir, "thumbs", os.path.splitext(os.path.basename(img_path))[0])
                os.makedirs(thumbs_dir, exist_ok=True)
                export_thumbnails(img_path, selections, thumbs_dir, margin=thumb_margin/100.0)

                # 4) 상태 저장
                st.session_state["results"][img_path] = {
                    "data": data,
                    "candidates": candidates,
                    "selections": selections,
                    "ocr_json": ocr_json,
                }
                st.session_state["overlay_paths"][img_path] = out_overlay
                st.session_state["thumb_dirs"][img_path] = thumbs_dir

                # except Exception as e:
                #     st.warning(f"[{os.path.basename(img_path)}] 처리 중 오류: {e}")

                progress.progress(i / len(imgs), text=f"처리 중... ({i}/{len(imgs)})")
            progress.empty()
            st.success("모든 이미지 처리를 완료했습니다.")

# ========================= 결과 브라우저 =============================
left, right = st.columns([1, 2], gap="large")

with left:
    st.subheader("파일 리스트")
    if st.session_state["images"]:
        df = pd.DataFrame({
            "파일명": [os.path.basename(p) for p in st.session_state["images"]],
            "경로": st.session_state["images"],
            "처리여부": ["✅" if p in st.session_state["results"] else "⏳" for p in st.session_state["images"]],
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

        current = st.selectbox(
            "결과 확인할 파일 선택",
            options=st.session_state["images"],
            format_func=lambda p: os.path.basename(p),
        )

        result_jsons = get_result_jsons(st.session_state["results"])
        result_jsons = get_json_wt_one_value_from_extract_invoice_fields(result_jsons)
        result_jsons = drop_source_id_from_json(result_jsons)
        result_df = create_dataframe_from_json(result_jsons)
        
        "전체 결과 확인"
        # 테이블 시각화
        st.dataframe(result_df, use_container_width=True, hide_index=True)

        excel_bytes = to_excel_bytes(result_df)

        # 파일명 안전하게 (current가 없다면 기본값 사용)
        current_time = time.strftime("%Y%m%d-%H%M%S")
        file_name = f"OCR_RESULT_{current_time}.xlsx"

        "전체 결과 다운로드"
        st.download_button(
            label="Excel 다운로드",
            data=excel_bytes,
            file_name=file_name,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        # 전체 csv 다운로드
        csv_bytes = to_csv_bytes(result_df)
        st.download_button(
            "CSV 다운로드",
            data=csv_bytes,
            file_name=file_name.replace(".xlsx", ".csv"),
            mime="text/csv",
        )

        # 전체 JSON 다운로드
        json_bytes = json.dumps(result_jsons, ensure_ascii=False, indent=2).encode("utf-8")
        st.download_button(
            "JSON 다운로드",
            data=json_bytes,
            file_name=file_name.replace(".xlsx", ".json"),
            mime="application/json",
        )
    else:
        current = None
        st.info("좌측 사이드바에서 ZIP 업로드 후 [ZIP 처리 실행]을 눌러주세요.")

with right:
    st.subheader("결과 보기")
    if current and current in st.session_state["results"]:
        res = st.session_state["results"][current]
        overlay_path = st.session_state["overlay_paths"].get(current)
        thumbs_dir = st.session_state["thumb_dirs"].get(current)

        col_a, col_b = st.columns(2)
        with col_a:
            st.image(current, caption="원본 이미지", use_container_width=True)
        with col_b:
            if overlay_path and os.path.exists(overlay_path):
                with open(overlay_path, "rb") as f:
                    bytes_overlay = f.read()
                st.image(bytes_overlay, caption="오버레이", use_container_width=True)
                st.download_button(
                    "오버레이 이미지 다운로드",
                    data=bytes_overlay,
                    file_name=os.path.basename(overlay_path),
                    mime="image/png",
                )
            else:
                st.info("오버레이가 없습니다.")

        st.markdown("---")
        st.subheader("썸네일(ROI)")
        if thumbs_dir and os.path.isdir(thumbs_dir):
            files = sorted([os.path.join(thumbs_dir, f) for f in os.listdir(thumbs_dir)
                            if _is_image(f)])
            if files:
                ncol = min(4, len(files))
                cols = st.columns(ncol)
                for i, p in enumerate(files):
                    with cols[i % ncol]:
                        st.image(p, caption=os.path.basename(p), use_container_width=True)
            else:
                st.info("썸네일이 없습니다.")
        else:
            st.info("썸네일 폴더가 없습니다.")

        # st.markdown("---")
        # st.subheader("LLM 결과(JSON)")
        # st.json(res["data"])

        # st.subheader("candidates (LLM이 선택 가능했던 후보)")
        # st.dataframe(res["candidates"], use_container_width=True)

        # st.subheader("selections (시각화에 사용된 값/좌표)")
        # st.dataframe(res["selections"], use_container_width=True)

        # st.subheader("OCR 원본 JSON")
        # st.json(res["ocr_json"])

        # # 개별 JSON 다운로드
        # json_bytes = json.dumps(res["data"], ensure_ascii=False, indent=2).encode("utf-8")
        # st.download_button(
        #     "결과 JSON 다운로드",
        #     data=json_bytes,
        #     file_name=os.path.basename(current) + ".result.json",
        #     mime="application/json",
        # )


    elif current:
        st.info("아직 처리되지 않았습니다. ZIP 처리 실행 후 확인해주세요.")
