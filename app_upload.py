# app.py
# Streamlit >= 1.32 권장
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

# ===== 도메인 데이터 =====
ARTIST_NAMES = ["루미", "미라", "조이"]
GROUP_NAMES = ["HUNTRIX"]
ALL_NAMES = ARTIST_NAMES + GROUP_NAMES  # 파일명 자동 매핑 기준

# ===== 페이지 / 테마(밝고 트렌디) =====
st.set_page_config(page_title="ENT OCR - Artist Mapper", page_icon="🎤", layout="wide")

PRIMARY = "#7C3AED"   # vivid purple
ACCENT  = "#EC4899"   # pink
INK     = "#111827"   # neutral-900
SUBINK  = "#4B5563"   # neutral-600
BG_TOP  = "#FFFFFF"
BG_BOT  = "#F6F7FF"

st.markdown(
    f"""
    <style>
      /* App background: bright gradient */
      .stApp {{
        background: linear-gradient(180deg, {BG_TOP} 0%, {BG_BOT} 65%, #EEF0FF 100%);
      }}
      .block-container {{ padding-top: 1.2rem; }}

      /* Hero */
      .ent-hero-title {{
        font-size: 28px; font-weight: 800; color:{INK}; letter-spacing:.2px;
      }}
      .ent-hero-sub {{
        color:{SUBINK}; font-weight: 500;
      }}

      /* Card */
      .ent-card {{
        background: #FFFFFFE6;
        border: 1px solid #E6E8FF;
        border-radius: 16px;
        padding: 16px;
        box-shadow: 0 4px 16px rgba(124,58,237,0.06);
      }}

      /* Chip */
      .ent-chip {{
        display:inline-flex; align-items:center; gap:8px;
        background: linear-gradient(90deg, {PRIMARY}10, {ACCENT}10);
        border: 1px solid {PRIMARY}33;
        color:{INK}; padding: 6px 12px; border-radius: 999px; font-weight:600;
      }}

      /* Section title underline */
      .ent-h4 {{
        font-size: 18px; font-weight: 800; color:{INK};
        border-bottom: 2px solid {PRIMARY}22; padding-bottom: 6px; margin-bottom: 10px;
      }}

      /* Footer */
      .ent-footer {{ color:{SUBINK}; font-size: 12px; }}
    </style>
    """,
    unsafe_allow_html=True,
)

# ===== 유틸 =====
KST = ZoneInfo("Asia/Seoul")

def now_kst_str() -> str:
    return datetime.now(tz=KST).strftime("%Y-%m-%d %H:%M:%S")

def detect_entities_from_filename(fname: str, candidates: list[str]) -> list[str]:
    """
    파일명에서 후보 이름을 검색해 매핑.
    - 대소문자 무시, 부분일치(실무서 붙여 쓰는 경우 고려)
    - 발견 순서는 candidates 정의 순서 유지
    """
    low = fname.lower()
    found: list[str] = []
    for name in candidates:
        if name.lower() in low and name not in found:
            found.append(name)
    return found

def scope_for(names: list[str]) -> str:
    """선택된 이름들의 범위: '개인'|'그룹'|'혼합'|'미지정'"""
    if not names:
        return "미지정"
    in_person = [n for n in names if n in ARTIST_NAMES]
    in_group  = [n for n in names if n in GROUP_NAMES]
    if in_person and not in_group:
        return "개인"
    if in_group and not in_person:
        return "그룹"
    return "혼합"

def build_table(files: list[st.runtime.uploaded_file_manager.UploadedFile], start_id: int) -> pd.DataFrame:
    rows = []
    ts = now_kst_str()
    for i, f in enumerate(files):
        artists = detect_entities_from_filename(f.name, ALL_NAMES)
        rows.append(
            {
                "id": start_id + i,
                "filename": f.name,
                "artists": artists,           # 다중 선택 허용
                "scope": scope_for(artists),  # 개인/그룹/혼합/미지정
                "uploaded_at": ts,
                "selected": False,            # 일괄 편집 대상
            }
        )
    return pd.DataFrame(rows, dtype=object)

def export_mapping_csv(df: pd.DataFrame) -> bytes:
    safe = df.copy()
    safe["artists"] = safe["artists"].apply(lambda xs: ", ".join(xs) if isinstance(xs, list) else "")
    cols = ["filename", "artists", "scope", "uploaded_at"]
    return safe[cols].to_csv(index=False).encode("utf-8-sig")

# ===== 세션 상태 =====
if "table" not in st.session_state:
    st.session_state.table = pd.DataFrame(columns=["id", "filename", "artists", "scope", "uploaded_at", "selected"])
if "open_modal" not in st.session_state:
    st.session_state.open_modal = False

# ===== 헤더 =====
st.markdown(
    """
<div class="ent-hero-title">🎤 ENT Receipt → Artist Mapper</div>
<div class="ent-hero-sub">이미지 영수증 업로드 → 파일명 기반 아티스트/그룹 자동 매핑 → 모달에서 ‘개인/그룹’ 일괄 지정</div>
<br/>
""",
    unsafe_allow_html=True,
)

with st.sidebar:
    st.markdown("### ⚙️ Quick tips")
    st.caption("💡 파일명에 '루미/미라/조이/HUNTRIX'가 포함되면 자동 매핑됩니다.")
    st.caption("💡 ‘모달 열기’로 선택 행에 아티스트를 한 번에 지정하세요.")
    st.markdown("---")
    st.caption("© 2025 ENT OCR · Entertainment Finance Workflows")

# ===== 업로드 카드 =====
st.markdown('<div class="ent-card">', unsafe_allow_html=True)
st.markdown('<div class="ent-h4">1) 이미지 업로드</div>', unsafe_allow_html=True)

files = st.file_uploader(
    "영수증 이미지 업로드 (PNG/JPG/JPEG, 다중 선택 가능)",
    type=["png", "jpg", "jpeg"],
    accept_multiple_files=True,
    help="업로드 시 파일명 기반으로 아티스트/그룹 자동 매핑",
)

c1, c2 = st.columns(2)
with c1:
    if st.button("테이블 초기화", use_container_width=True, type="secondary"):
        st.session_state.table = pd.DataFrame(columns=st.session_state.table.columns)
        st.success("테이블 초기화 완료")
with c2:
    if files and st.button("업로드 → 테이블 생성/추가", use_container_width=True, type="primary"):
        start_id = 0 if st.session_state.table.empty else int(st.session_state.table["id"].max()) + 1
        new_df = build_table(files, start_id)
        if st.session_state.table.empty:
            st.session_state.table = new_df
        else:
            existing = set(st.session_state.table["filename"].tolist())
            add_df = new_df[~new_df["filename"].isin(existing)]
            st.session_state.table = pd.concat([st.session_state.table, add_df], ignore_index=True)
        st.success(f"{len(files)}개 파일 반영 완료")
st.markdown("</div>", unsafe_allow_html=True)

# ===== 매핑/편집 카드 =====
st.markdown("<br/>", unsafe_allow_html=True)
st.markdown('<div class="ent-card">', unsafe_allow_html=True)
st.markdown('<div class="ent-h4">2) 매핑 테이블 (편집/선택)</div>', unsafe_allow_html=True)

if st.session_state.table.empty:
    st.info("먼저 이미지를 업로드해 테이블을 생성하세요.")
else:
    view_df = st.session_state.table.copy()
    edited = st.data_editor(
        view_df,
        use_container_width=True,
        hide_index=True,
        num_rows="dynamic",
        key="artist_mapping_table",
        column_config={
            "id": st.column_config.Column("ID", disabled=True),
            "filename": st.column_config.Column("파일명", disabled=True),
            "uploaded_at": st.column_config.Column("업로드 시간", disabled=True),
            "selected": st.column_config.Column("선택"),
            "artists": st.column_config.ListColumn("아티스트/그룹(다중)"),
            "scope": st.column_config.SelectboxColumn("범위", options=["미지정", "개인", "그룹", "혼합"]),
        },
    )
    if not edited.equals(st.session_state.table):
        edited["scope"] = edited["artists"].apply(scope_for)
        st.session_state.table = edited

    st.markdown("---")
    sel_mask = st.session_state.table["selected"] == True
    sel_count = int(sel_mask.sum())
    st.markdown(
        f"선택된 행: <span class='ent-chip'>{sel_count} rows</span>",
        unsafe_allow_html=True,
    )

    colX, colY, colZ = st.columns(3)
    with colX:
        if st.button("전체 선택", use_container_width=True):
            st.session_state.table["selected"] = True
    with colY:
        if st.button("선택 해제", use_container_width=True):
            st.session_state.table["selected"] = False
    with colZ:
        if st.button("미배정만 선택", use_container_width=True):
            st.session_state.table["selected"] = st.session_state.table["artists"].apply(lambda xs: len(xs or []) == 0)

    st.markdown("---")
    open_btn = st.button("🎛️ 모달 열기: 아티스트 일괄 매핑", type="primary", disabled=(sel_count == 0))
    if open_btn:
        st.session_state.open_modal = True

    # ===== 모달: 아티스트 일괄 매핑 =====
    @st.dialog("아티스트 일괄 매핑")
    def batch_artist_dialog():
        st.caption("선택된 행에 대해 ‘개인’ 또는 ‘그룹’을 선택하고, 해당 대상에서 여러 명을 지정할 수 있습니다.")

        df = st.session_state.table
        mask = df["selected"] == True
        count = int(mask.sum())
        st.write(f"대상 행: **{count}**")

        kind = st.radio("대상 구분", options=["개인", "그룹"], horizontal=True)
        options = ARTIST_NAMES if kind == "개인" else GROUP_NAMES

        # 기본값: 현재 선택된 행들의 교집합(선택한 범위 내에서만)
        current_lists = df.loc[mask, "artists"].apply(lambda xs: set([x for x in (xs or []) if x in options]))
        if len(current_lists) > 1:
            default_selected = sorted(list(set.intersection(*current_lists)))
        elif len(current_lists) == 1:
            default_selected = sorted(list(list(current_lists)[0]))
        else:
            default_selected = []

        selected_names = st.multiselect(f"{kind} 선택(다중)", options=options, default=default_selected)

        mode = st.radio(
            "적용 방식",
            options=["덮어쓰기", "추가"],
            index=0,
            horizontal=True,
            help="덮어쓰기: 선택된 범위의 기존 목록을 대체 / 추가: 기존 목록에 선택한 이름을 합칩니다(중복 제거).",
        )

        st.divider()
        cA, cB = st.columns(2)
        with cA:
            if st.button("적용", type="primary", use_container_width=True, disabled=(len(selected_names) == 0)):
                if mode == "덮어쓰기":
                    df.loc[mask, "artists"] = [selected_names[:] for _ in range(count)]
                else:
                    def _merge(xs: list[str] | None) -> list[str]:
                        base = set(xs or [])
                        base.update(selected_names)
                        # 정의된 순서 보존
                        return sorted(base, key=lambda x: ALL_NAMES.index(x) if x in ALL_NAMES else 9999)
                    df.loc[mask, "artists"] = df.loc[mask, "artists"].apply(_merge)

                df.loc[mask, "scope"] = df.loc[mask, "artists"].apply(scope_for)
                st.session_state.table = df
                st.success("적용 완료")
                st.session_state.open_modal = False
        with cB:
            if st.button("취소", use_container_width=True):
                st.session_state.open_modal = False

    if st.session_state.open_modal:
        batch_artist_dialog()

    # ===== 검증/경고 =====
    st.markdown("---")
    invalid = []
    for _, row in st.session_state.table.iterrows():
        artists = row["artists"] or []
        if any(a not in ALL_NAMES for a in artists):
            invalid.append(row["filename"])
    if invalid:
        st.error(f"⚠️ 허용되지 않은 이름이 포함된 파일: {', '.join(invalid)}")
    else:
        st.success("✅ 모든 행이 허용된 이름 목록(개인/그룹)만 포함합니다.")

    # ===== 내보내기 =====
    st.markdown("---")
    colE1, colE2 = st.columns([1, 3])
    with colE1:
        st.download_button(
            "📥 매핑 결과 CSV 다운로드",
            data=export_mapping_csv(st.session_state.table),
            file_name=f"artist_mapping_{datetime.now(tz=KST).strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True,
        )
    with colE2:
        st.caption("다운로드 컬럼: filename, artists, scope, uploaded_at")

st.markdown("</div>", unsafe_allow_html=True)

# ===== 푸터 =====
st.markdown("<br/>", unsafe_allow_html=True)
st.markdown("<div class='ent-footer'>© 2025 ENT OCR · Designed for Entertainment Finance Workflows</div>", unsafe_allow_html=True)
