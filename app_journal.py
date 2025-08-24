# app.py
# -----------------------------------------------------------
# Entertainment Demo: JSON → Journal Entry → Records → Table
# - Legacy rules {column: {value: artist}} + modal editor
# - HOVER preview: row hover → show overlay image (from index dict)
# -----------------------------------------------------------
import base64
import json
import os
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
import streamlit as st
from streamlit.components.v1 import html as st_html
from src.entjournal.constants import COLUMN_RULES_PATH

# ===== 도메인 데이터 =====
ARTIST_NAMES = ["루미", "미라", "조이"]
GROUP_NAMES = ["HUNTRIX"]
ALL_NAMES = ARTIST_NAMES + GROUP_NAMES

# ===== 파일 경로 =====
RULES_DB_PATH = Path(COLUMN_RULES_PATH)

# ===== 외부 파이프라인 임포트(실제 프로젝트 경로로 교체) =====
try:
    from src.entjournal.journal_main import (
        get_json_wt_one_value_from_extract_invoice_fields,
        drop_source_id_from_json,
        make_journal_entry,
        make_journal_entry_to_record_list,
    )
    USING_STUB = False
except Exception:
    USING_STUB = True

    def get_json_wt_one_value_from_extract_invoice_fields(d: dict) -> dict:
        return d

    def drop_source_id_from_json(dl: List[dict]) -> List[dict]:
        return [{k: v for k, v in d.items() if k != "source_id"} for d in dl]

    # 규칙 로드(레거시)
    def load_column_rules() -> Dict[str, Dict[str, str]]:
        if RULES_DB_PATH.exists():
            try:
                return json.loads(RULES_DB_PATH.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {}

    def map_artist_name_with_column_rules_to_json(json_data: List[dict]) -> List[dict]:
        column_rules = load_column_rules()
        if not column_rules:
            return json_data
        for voucher in json_data:
            if voucher.get("프로젝트명"):
                continue
            for col, val in voucher.items():
                rule = column_rules.get(col)
                if not rule or val is None:
                    continue
                artist = rule.get(str(val))
                if artist:
                    voucher["프로젝트명"] = artist
                    break
        return json_data

    def make_journal_entry(dl: List[dict]) -> Dict[str, Any]:
        dl = map_artist_name_with_column_rules_to_json(dl)
        out = []
        for row in dl:
            amount = row.get("금액", 0)
            out.append({
                "debit": [{"account": row.get("계정과목", "지급수수료"), "amount": amount}],
                "credit": [{"account": "미지급금", "amount": amount}],
                "meta": row,
            })
        return {"entries": out}

    def make_journal_entry_to_record_list(result_dict: Dict[str, Any], src_path: str) -> List[Dict[str, Any]]:
        recs = []
        for i, e in enumerate(result_dict.get("entries", []), 1):
            meta = e.get("meta", {})
            rec = {
                "행": i,
                "날짜": meta.get("날짜"),
                "거래처명": meta.get("거래처명") or meta.get("거래처"),
                "계정과목": e["debit"][0]["account"],
                "차변": e["debit"][0]["amount"],
                "대변계정": e["credit"][0]["account"],
                "대변": e["credit"][0]["amount"],
                "파일명": os.path.basename(src_path),   # << 키 fallback
            }
            if meta.get("file_id"):
                rec["file_id"] = meta["file_id"]       # << 키 우선
            if meta.get("프로젝트명"):
                rec["프로젝트명"] = meta["프로젝트명"]
            recs.append(rec)
        return recs

# ===== 스타일 =====
def inject_brand_css():
    st.markdown(
        """
        <style>
        :root {
          --brand-gradient: linear-gradient(135deg, #7C3AED 0%, #EC4899 100%);
          --brand-bg: #0b0b11;
          --card-bg: rgba(255,255,255,0.04);
          --card-border: rgba(255,255,255,0.08);
        }
        .stApp {
          background: radial-gradient(1200px 800px at 20% 0%, rgba(124,58,237,0.10), transparent 60%),
                      radial-gradient(1000px 600px at 100% 20%, rgba(236,72,153,0.10), transparent 60%),
                      var(--brand-bg);
        }
        .app-hero {
          padding: 20px 24px;
          border-radius: 18px;
          background: var(--card-bg);
          border: 1px solid var(--card-border);
        }
        .hero-title {
          font-weight: 800;
          font-size: 28px;
          line-height: 1.1;
          background: var(--brand-gradient);
          -webkit-background-clip: text;
          background-clip: text;
          color: transparent;
          margin: 0;
        }
        .hero-sub { color: #c9c9d1; margin-top: 6px; font-size: 14px; }
        .soft-card {
          padding: 16px;
          border-radius: 16px;
          background: var(--card-bg);
          border: 1px solid var(--card-border);
        }
        .split { display: grid; grid-template-columns: 1.2fr 1fr; gap: 16px; }
        @media (max-width: 1100px) { .split { grid-template-columns: 1fr; } }
        .pill {
          display: inline-flex; align-items: center; gap: 6px;
          padding: 6px 10px; border-radius: 999px;
          background: rgba(255,255,255,0.06); color: #E5E7EB;
          border: 1px solid var(--card-border); font-size: 12px;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

# ===== 레거시 규칙 유틸 =====
def load_column_rules() -> Dict[str, Dict[str, str]]:
    if RULES_DB_PATH.exists():
        try:
            return json.loads(RULES_DB_PATH.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def save_column_rules(rules: Dict[str, Dict[str, str]]) -> None:
    RULES_DB_PATH.write_text(json.dumps(rules, ensure_ascii=False, indent=2), encoding="utf-8")

# ===== 파일명/ID 힌트 =====
def initial_guess_from_filename(filename: str) -> Optional[str]:
    base = os.path.basename(filename).lower()
    for name in ALL_NAMES:
        if name.lower() in base:
            return name
    return None

# ===== 파이프라인 실행 =====
def run_pipeline_from_bytes(file_bytes: bytes, file_name: str) -> pd.DataFrame:
    # tmp_dir = Path("./.tmp"); tmp_dir.mkdir(exist_ok=True)
    # tmp_path = tmp_dir / file_name
    # tmp_path.write_bytes(file_bytes)

    # input_path = str(tmp_path)
    # data_dict = json.load(open(input_path, "r", encoding="utf-8"))
    # data_dict = get_json_wt_one_value_from_extract_invoice_fields(data_dict)
    # data_dict = [data_dict]
    # data_dict = drop_source_id_from_json(data_dict)
    # result_dict = make_journal_entry(data_dict)  # 내부에서 프로젝트명 매핑 가정
    # record_list = make_journal_entry_to_record_list(result_dict, input_path)
    # df = pd.DataFrame(record_list)

    # if "프로젝트명" not in df.columns:
    #     guess = initial_guess_from_filename(file_name)
    #     if guess:
    #         df["프로젝트명"] = guess
    # return df
    tmp_dir = Path("./.tmp"); tmp_dir.mkdir(exist_ok=True)
    tmp_path = tmp_dir / file_name
    tmp_path.write_bytes(file_bytes)

    input_path = str(tmp_path)
    raw_dict = json.load(open(input_path, "r", encoding="utf-8"))
    processed_dict = get_json_wt_one_value_from_extract_invoice_fields(raw_dict)
    # 편집 재실행 대비: 추후 패치 적용용으로 저장
    st.session_state["last_input_dict"] = processed_dict

    data_list = [processed_dict]
    data_list = drop_source_id_from_json(data_list)
    result_dict = make_journal_entry(data_list)
    record_list = make_journal_entry_to_record_list(result_dict, input_path)
    df = pd.DataFrame(record_list)

    # 파일명 힌트
    if "프로젝트명" not in df.columns:
        guess = initial_guess_from_filename(file_name)
        if guess:
            df["프로젝트명"] = guess

    # (★추가) 원본 메타를 키로 보관: file_id > 파일명
    meta_map = {}
    for e in result_dict.get("entries", []):
        meta = e.get("meta", {})
        key = meta.get("file_id") or os.path.basename(input_path)
        meta_map[str(key)] = meta
    st.session_state["meta_map"] = meta_map
    st.session_state["last_file_key"] = os.path.basename(input_path)

    return df
# ===== 이미지 인덱스 로더/인코더 =====
def _guess_mime(path: str) -> str:
    ext = os.path.splitext(path)[1].lower()
    if ext in [".jpg", ".jpeg"]:
        return "image/jpeg"
    if ext in [".webp"]:
        return "image/webp"
    return "image/png"

def image_path_to_data_uri(path: str) -> Optional[str]:
    try:
        norm = os.path.normpath(path)
        with open(norm, "rb") as f:
            b64 = base64.b64encode(f.read()).decode("ascii")
        return f"data:{_guess_mime(norm)};base64,{b64}"
    except Exception:
        return None

def build_data_uri_map(overlay_index: Dict[str, str]) -> Dict[str, str]:
    data = {}
    for key, p in overlay_index.items():
        uri = image_path_to_data_uri(p)
        if uri:
            data[key] = uri
    return data

# ===== Hover Preview 컴포넌트 =====
def render_journal_table_with_hover_tooltip(
    df: pd.DataFrame,
    overlay_index: Dict[str, str],
    container_height_px: int = 820,
    fixed_height: bool = True,
    min_height: bool = False,
    meta_map: Optional[Dict[str, Any]] = None,   # ★ 원본 메타 맵 주입
):
    import base64, os, json
    from typing import Optional
    from streamlit.components.v1 import html as st_html

    temp_dict = {"HUNTRIX_data.json":{
    "날짜": [
        {
            "value": "20-12-31",
            "source_id": "p0_00011"
        }
    ],
    "거래처": [
        {
            "value": "HUNTER피부과",
            "source_id": None
        }
    ],
    "금액": [
        {
            "value": "1452000",
            "source_id": "p0_00023"
        }
    ],
    "유형": [
        "피부"
    ],
    "사업자등록번호": [
        {
            "value": "000-00-00000",
            "source_id": "p0_00001"
        }
    ],
    "대표자": [
        {
            "value": "OOO",
            "source_id": None
        }
    ],
    "주소": [
        {
            "value": "서울특별시",
            "source_id": None
        }
    ],
    "증빙유형": [
        "세금계산서"
    ],
    "계정과목": "연예보조_기타",
    "계정코드": 53899,
    "프로젝트명": None,
    "거래처코드": "10001",
    "거래처명": "HUNTRIX한의원"
}}
    if df is None or df.empty:
        st.info("분개 결과가 없습니다.")
        return

    key_col = "file_id" if "file_id" in df.columns else ("파일명" if "파일명" in df.columns else None)
    if not key_col:
        st.warning("미리보기를 위해 'file_id' 또는 '파일명' 컬럼이 필요합니다.")
        return

    # ----- 이미지 data URI 준비 (데모/로컬용) -----
    def _guess_mime(path: str) -> str:
        ext = os.path.splitext(path)[1].lower()
        if ext in (".jpg", ".jpeg"): return "image/jpeg"
        if ext == ".webp": return "image/webp"
        return "image/png"

    def _to_data_uri(path: str) -> Optional[str]:
        try:
            with open(os.path.normpath(path), "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
            return f"data:%s;base64,%s" % (_guess_mime(path), b64)
        except Exception:
            return None

    data_uri_map = {}
    for k, v in (overlay_index or {}).items():
        if isinstance(v, str):
            uri = _to_data_uri(v)
            if uri: data_uri_map[str(k)] = uri

    # ----- 표시 컬럼/값 준비 -----
    cols_pref = ["행","날짜","거래처명","프로젝트명","계정과목","차변","대변",key_col]
    show_cols = list(df.columns)

    def _fmt(v):
        try:
            if isinstance(v, (int, float)) and not isinstance(v, bool):
                return f"{v:,.0f}"
        except Exception:
            pass
        return "" if v is None else str(v)

    rows = [{c: _fmt(r[c]) for c in show_cols} for _, r in df.iterrows()]

    # ----- 모달용 원본 메타 전달 -----
    meta_map = meta_map or temp_dict #시연용 임시 meta_map = meta_map or {}
    # 편집폼 렌더 시 첫번째 값 추출 함수는 JS에서 수행

    payload = {
        "rows": rows,
        "cols": show_cols,
        "key_col": key_col,
        "img_map": data_uri_map,
        "meta_map": meta_map,          # ★ JS로 전달
    }
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")

    # 높이 고정/최소/최대 선택
    if fixed_height:
        root_height_decl = f"height: {container_height_px}px;"
    elif min_height:
        root_height_decl = f"min-height: {container_height_px}px;"
    else:
        root_height_decl = f"max-height: {container_height_px}px;"

    html_template = r"""

    
<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  :root { --row-gap: 8px; --bg: rgba(11,11,17,0.9); }
  html, body { margin:0; padding:0; background: var(--bg); color:#e6e6f0; font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Noto Sans KR"; }
  #root { position: relative; __ROOT_HEIGHT_DECL__; overflow: auto; padding: 0 0 var(--row-gap) 0; }

  table.tbl { width:100%; border-collapse:separate; border-spacing:0 var(--row-gap); font-size:14px; }
  .tbl thead th { position:sticky; top:0; background:var(--bg); text-align:left; font-weight:700; padding:8px 10px; color:#cfcfe3; z-index:2; }
  .tbl tbody tr { background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); }
  .tbl tbody tr:hover { background:rgba(124,58,237,0.16); border-color:rgba(124,58,237,0.35); }
  .tbl td { padding:10px 10px; white-space:nowrap; }

  /* 툴팁(커서 옆 이미지) */
  #ent-tip { position:absolute; z-index:9999; display:none; pointer-events:none; background:rgba(0,0,0,0.82);
             border:1px solid rgba(255,255,255,0.12); border-radius:12px; padding:6px; box-shadow:0 8px 32px rgba(0,0,0,0.45);
             max-width:800px; max-height:800px; }
  #ent-tip img { display:block; max-width:800px; max-height:800px; object-fit:contain; }

  /* 모달 */
  #modal-backdrop { position:absolute; inset:0; background:rgba(0,0,0,0.55); display:none; z-index:9998; }
  #modal { position:absolute; top:50%; left:50%; transform:translate(-50%,-50%);
           width:min(820px, 92%); max-height:80%; overflow:auto;
           background:#0f0f16; border:1px solid rgba(255,255,255,0.08); border-radius:14px; padding:16px; display:none; z-index:9999; }
  .modal-title { font-weight:800; margin:0 0 8px 0; font-size:18px; }
  .kv-grid { display:grid; grid-template-columns: 220px 1fr; column-gap:12px; row-gap:8px; }
  .kv-key { color:#bdbdd0; padding:6px 8px; background:rgba(255,255,255,0.04); border:1px solid rgba(255,255,255,0.08); border-radius:8px; }
  .kv-value { padding:6px 8px; background:rgba(255,255,255,0.03); border:1px solid rgba(255,255,255,0.08); border-radius:8px; }
  .kv-value input { width:100%; background:transparent; border:none; outline:none; color:#e6e6f0; font-size:14px; }
  .modal-actions { display:flex; gap:8px; justify-content:flex-end; margin-top:12px; }
  .btn { padding:8px 12px; border-radius:10px; border:1px solid rgba(255,255,255,0.12); background:rgba(255,255,255,0.06); color:#e6e6f0; cursor:pointer; }
  .btn.primary { background:linear-gradient(135deg, #7C3AED, #EC4899); border:none; }
  .btn.danger  { background:rgba(239,68,68,0.15); border-color:rgba(239,68,68,0.45); }
</style>
</head>
<body>
  <div id="root">
    <table class="tbl">
      <thead id="thead"></thead>
      <tbody id="tbody"></tbody>
    </table>
    <div id="ent-tip"><img id="ent-img" alt="preview"></div>

    <!-- 모달 -->
    <div id="modal-backdrop"></div>
    <div id="modal">
      <h3 class="modal-title">원본 정보 편집</h3>
      <div id="kv" class="kv-grid"></div>
      <div class="modal-actions">
        <button class="btn danger" id="btn-download">변경사항 JSON 다운로드</button>
        <div style="flex:1"></div>
        <button class="btn" id="btn-cancel">취소</button>
        <button class="btn primary" id="btn-save">저장(표시값 갱신)</button>
      </div>
    </div>
  </div>

  <script id="PAYLOAD" type="application/json">__PAYLOAD__</script>
<script>
const P       = JSON.parse(document.getElementById('PAYLOAD').textContent);
const ROWS    = P.rows, COLS = P.cols, KEY = P.key_col, IMG = P.img_map || {};
const META    = P.meta_map || {};

const root    = document.getElementById('root');
const thead   = document.getElementById('thead');
const tbody   = document.getElementById('tbody');
const tip     = document.getElementById('ent-tip');
const tipImg  = document.getElementById('ent-img');

const modalBackdrop = document.getElementById('modal-backdrop');
const modal         = document.getElementById('modal');
const kv            = document.getElementById('kv');
const btnCancel     = document.getElementById('btn-cancel');
const btnSave       = document.getElementById('btn-save');
const btnDownload   = document.getElementById('btn-download');

const OFFSET_X=18, OFFSET_Y=18;

function esc(s){return String(s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;");}

/* 테이블 렌더 */
thead.innerHTML = '<tr>' + COLS.map(c=>`<th>${esc(c)}</th>`).join('') + '</tr>';
tbody.innerHTML = ROWS.map(r=>{
  const key = r[KEY] ?? '';
  const cells = COLS.map(c=>`<td>${esc(r[c] ?? '')}</td>`).join('');
  return `<tr data-key="${esc(String(key))}">${cells}</tr>`;
}).join('');

/* 툴팁 위치 (컨테이너 기준) */
function placeTip(evt){
  if (tip.style.display!=='block') return;
  const rect = root.getBoundingClientRect();
  let x = (evt.clientX - rect.left) + root.scrollLeft + OFFSET_X;
  let y = (evt.clientY - rect.top)  + root.scrollTop  + OFFSET_Y;
  const w = tip.offsetWidth||300, h = tip.offsetHeight||300;
  const maxX = root.scrollWidth - w - 4, maxY = root.scrollHeight - h - 4;
  if (x > maxX) x = Math.max(4, (evt.clientX - rect.left) + root.scrollLeft - w - OFFSET_X);
  if (y > maxY) y = Math.max(4, (evt.clientY - rect.top)  + root.scrollTop  - h - OFFSET_Y);
  tip.style.left = x + 'px'; tip.style.top = y + 'px';
}

/* Hover 미리보기 */
tbody.addEventListener('mouseover', (e)=>{
  const tr = e.target.closest('tr'); if(!tr) return;
  const key = tr.getAttribute('data-key');
  const src = IMG[key];
  if (src) { if (tipImg.src!==src) tipImg.src=src; tip.style.display='block'; placeTip(e); }
  else { tip.style.display='none'; tipImg.src=''; }
});
tbody.addEventListener('mousemove', placeTip);
root.addEventListener('mouseleave', ()=>{ tip.style.display='none'; tipImg.src=''; });

/* === 더블클릭: 모달 열기 === */
let currentKey = null;
tbody.addEventListener('dblclick', (e)=>{
  const tr = e.target.closest('tr'); if(!tr) return;
  const key = tr.getAttribute('data-key');
  currentKey = key;

  const meta = META[key] || {};
  // 폼 초기화
  kv.innerHTML = '';
  // 메타를 key/value 편집행으로 변환: 리스트면 첫번째, dict 리스트면 첫 원소.value
  const fields = Object.keys(meta);
  fields.forEach(k=>{
    let v = meta[k];
    let display = '';
    if (Array.isArray(v)) {
      if (v.length>0) {
        if (typeof v[0]==='object' && v[0] && 'value' in v[0]) display = v[0]['value'] ?? '';
        else display = String(v[0] ?? '');
      }
    } else {
      display = (typeof v==='object' && v && 'value' in v) ? (v['value'] ?? '') : String(v ?? '');
    }
    const row = document.createElement('div');
    row.className = 'kv-key';
    row.textContent = k;
    const val = document.createElement('div');
    val.className = 'kv-value';
    val.innerHTML = `<input type="text" value="${esc(display)}" data-field="${esc(k)}" />`;
    kv.appendChild(row);
    kv.appendChild(val);
  });

  modalBackdrop.style.display='block';
  modal.style.display='block';
});

/* 모달 버튼 */
btnCancel.addEventListener('click', ()=>{
  modalBackdrop.style.display='none';
  modal.style.display='none';
});

/* 저장: 화면상의 ROWS/셀만 갱신 */
btnSave.addEventListener('click', ()=>{
  if (!currentKey) return;
  const inputs = kv.querySelectorAll('input[data-field]');
  // 패치 사전 준비
  const patch = {};
  inputs.forEach(inp => { patch[inp.getAttribute('data-field')] = inp.value; });

  // 표시 컬럼 동기화: "날짜", "거래처명"(또는 "거래처"), "금액","유형","계정과목","프로젝트명" 등 있는 경우 갱신
  const row = ROWS.find(r => String(r[KEY])===String(currentKey));
  if (row) {
    const mapping = ["날짜","거래처명","거래처","금액","유형","계정과목","프로젝트명","주소","대표자","사업자등록번호"];
    mapping.forEach(m => { if (m in patch && m in row) row[m] = patch[m]; });
    // 테이블 재렌더 간단화: 해당 tr만 다시 그림
    const tr = tbody.querySelector(`tr[data-key="${CSS.escape(String(currentKey))}"]`);
    if (tr) {
      tr.innerHTML = COLS.map(c => `<td>${esc(row[c] ?? '')}</td>`).join('');
    }
  }

  modalBackdrop.style.display='none';
  modal.style.display='none';
});

/* 패치 JSON 다운로드: { "<key>": { field: value, ... } } */
btnDownload.addEventListener('click', ()=>{
  if (!currentKey) return;
  const inputs = kv.querySelectorAll('input[data-field]');
  const o = {}; inputs.forEach(inp=>{ o[inp.getAttribute('data-field')] = inp.value; });
  const blob = new Blob([JSON.stringify({ [currentKey]: o }, null, 2)], {type:'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `row_patch_${currentKey}.json`;
  document.body.appendChild(a); a.click(); a.remove();
});
</script>
</body></html>
    """

    html_final = (
        html_template
        .replace("__PAYLOAD__", payload_json)
        .replace("__ROOT_HEIGHT_DECL__", root_height_decl)
    )
    st_html(html_final, height=container_height_px + 24, scrolling=False)




# ===== 규칙 모달(레거시: equals) =====
def rules_modal_legacy(df: pd.DataFrame, target_column: str):
    all_rules = load_column_rules()
    col_rules: Dict[str, str] = dict(all_rules.get(target_column, {}))

    rows = [{"조건값(정확일치)": k, "아티스트명": v} for k, v in col_rules.items()]
    editor_df = pd.DataFrame(rows, columns=["조건값(정확일치)", "아티스트명"])
    if editor_df.empty:
        editor_df = pd.DataFrame([{"조건값(정확일치)": "", "아티스트명": ALL_NAMES[0]}])

    with st.form("rules_form_legacy", clear_on_submit=False):
        st.caption(f"선택 컬럼: **{target_column}** · 조건은 '정확히 일치(equals)'만 지원합니다.")
        edited = st.data_editor(
            editor_df,
            use_container_width=True,
            num_rows="dynamic",
            column_config={
                "조건값(정확일치)": st.column_config.TextColumn("조건값(정확일치)", required=True, width="large"),
                "아티스트명": st.column_config.SelectboxColumn("아티스트명", options=ALL_NAMES, required=True),
            },
            hide_index=True,
        )
        test_value = st.text_input("🔎 규칙 테스트", value="")
        c1, c2, c3 = st.columns(3)
        with c1:
            st.form_submit_button("규칙 적용 미리보기")
        with c2:
            save_now = st.form_submit_button("규칙 저장")
        with c3:
            save_and_rerun = st.form_submit_button("규칙 저장 후 결과 재생성")

    if test_value:
        artist = None
        for _, r in edited.iterrows():
            if str(test_value) == str(r["조건값(정확일치)"]):
                artist = r["아티스트명"]; break
        st.info(f"테스트 결과: **{artist}**" if artist else "테스트 결과: (매칭 없음)")

    def _persist(e: pd.DataFrame):
        cleaned: Dict[str, str] = {}
        for _, r in e.iterrows():
            key = str(r["조건값(정확일치)"]).strip()
            if not key:
                continue
            cleaned[key] = str(r["아티스트명"]).strip()
        all_rules[target_column] = cleaned
        save_column_rules(all_rules)

    if save_now:
        _persist(edited)
        st.success("규칙을 저장했습니다.")

    if save_and_rerun:
        _persist(edited)
        st.success("규칙을 저장했습니다. 결과를 재생성합니다…")
        st.session_state["_rerun_with_rules"] = True
        st.session_state["_rules_modal_open"] = False

# ===== 메인 =====
def main():
    st.set_page_config(page_title="ENT • Journal Demo", page_icon="🎵", layout="wide")
    inject_brand_css()

    st.markdown(
        """
        <div class="app-hero">
          <div class="pill">ENT Finance • AI Assisted</div>
          <h1 class="hero-title">분개 자동생성 & 아티스트 매핑</h1>
          <div class="hero-sub">JSON 업로드 → 분개 → 테이블. 행 hover 시 우측에 오버레이 이미지 미리보기.</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")

    # 재실행 필요 시 수행
    if st.session_state.get("_rerun_with_rules"):
        fb = st.session_state.get("_last_file_bytes")
        fn = st.session_state.get("_last_file_name")
        if fb and fn:
            try:
                df = run_pipeline_from_bytes(fb, fn)
                st.session_state["df"] = df
                st.success("규칙 반영하여 결과 재생성 완료.")
            except Exception as e:
                st.error(f"재생성 오류: {e}")
        st.session_state["_rerun_with_rules"] = False

    st.markdown('<div class="split">', unsafe_allow_html=True)

    # 왼쪽: 업로드 & 결과
    with st.container():
        st.markdown('<div class="soft-card">', unsafe_allow_html=True)
        st.subheader("1) JSON 업로드 & 실행", divider="grey")
        uploaded = st.file_uploader("JSON 파일 업로드", type=["json"], accept_multiple_files=False)
        run = st.button("🚀 분개 생성 실행", use_container_width=True)
        if run:
            if not uploaded:
                st.warning("JSON 파일을 먼저 업로드하세요.")
            else:
                try:
                    st.session_state["_last_file_bytes"] = uploaded.getvalue()
                    st.session_state["_last_file_name"] = uploaded.name
                    df = run_pipeline_from_bytes(st.session_state["_last_file_bytes"], st.session_state["_last_file_name"])
                    st.session_state["df"] = df
                    st.success("분개 생성 완료!")
                except Exception as e:
                    st.error(f"실행 오류: {e}")

        # 결과 표(기본)
        df = st.session_state.get("df")
        # if isinstance(df, pd.DataFrame) and not df.empty:
            # st.subheader("2) 결과 테이블", divider="grey")
            # st.dataframe(df, use_container_width=True, height=420)
        # st.markdown('</div>', unsafe_allow_html=True)

        # Hover Preview (커스텀)
        st.markdown('<div class="soft-card">', unsafe_allow_html=True)
        st.subheader("분개 생성 결과", divider="grey")
        overlay_index = st.session_state.get("overlay_index") or {}
        if not overlay_index and Path("overlay_index.json").exists():
            try:
                overlay_index = json.loads(Path("overlay_index.json").read_text(encoding="utf-8"))
                st.session_state["overlay_index"] = overlay_index
            except Exception:
                pass
        overlay_index = {
            "HUNTRIX_data.json": "test\\3. VISUALIZATION\\OUTPUT\\HUNTRIX_overlay.png"
        }
        meta_map = st.session_state.get("meta_map") or {}
        render_journal_table_with_hover_tooltip(
            df, overlay_index,
            container_height_px=900, fixed_height=True,
            meta_map=meta_map,   # ★ 원본 메타 전달
        )
        st.markdown('</div>', unsafe_allow_html=True)

    # 오른쪽: 규칙 & 인덱스 업로드
    with st.container():
        st.markdown('<div class="soft-card">', unsafe_allow_html=True)
        st.subheader("매핑 규칙(정확일치)", divider="grey")

        if isinstance(df, pd.DataFrame) and not df.empty:
            candidates = list(df.columns)
            default_col = "거래처명" if "거래처명" in candidates else ("파일명" if "파일명" in candidates else candidates[0])
        else:
            candidates = ["거래처명", "파일명"]
            default_col = "거래처명"

        target_col = st.selectbox("규칙 편집 대상 컬럼", candidates, index=candidates.index(default_col) if default_col in candidates else 0)

        c1, c2 = st.columns([1, 1])
        with c1:
            if st.button("🎛️ 매핑 규칙 관리", use_container_width=True):
                st.session_state["_rules_modal_open"] = True
        with c2:
            cnt = len(load_column_rules().get(target_col, {}))
            st.metric("해당 컬럼의 규칙 개수", cnt)
        st.markdown('</div>', unsafe_allow_html=True)

        # 오버레이 인덱스 업로드
        st.markdown('<div class="soft-card">', unsafe_allow_html=True)
        st.subheader("오버레이 인덱스(JSON)", divider="grey")
        st.caption("예: { \"HUNTRIX_data.json\": \"test\\\\3. VISUALIZATION\\\\OUTPUT\\\\HUNTRIX_overlay.png\" }")
        idx_file = st.file_uploader("overlay_index.json 업로드", type=["json"], accept_multiple_files=False, key="idx_uploader")
        if idx_file is not None:
            try:
                overlay_index = json.loads(idx_file.getvalue().decode("utf-8"))
                st.session_state["overlay_index"] = overlay_index
                st.success(f"인덱스 {len(overlay_index)}건 로드됨.")
            except Exception as e:
                st.error(f"인덱스 로드 실패: {e}")
        else:
            if "overlay_index" in st.session_state:
                st.info(f"현재 인덱스 {len(st.session_state['overlay_index'])}건 사용 중.")
            else:
                st.info("인덱스를 업로드하거나 프로젝트 루트의 overlay_index.json을 사용합니다.")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('</div>', unsafe_allow_html=True)

    # 모달
    if st.session_state.get("_rules_modal_open", False):
        try:
            @st.dialog("매핑 규칙 관리", width="large")
            def _modal():
                df_ = st.session_state.get("df", pd.DataFrame())
                rules_modal_legacy(df_, target_column=target_col)
            _modal()
        except Exception:
            st.markdown("### 🪟 매핑 규칙 관리 (모달 fallback)")
            df_ = st.session_state.get("df", pd.DataFrame())
            rules_modal_legacy(df_, target_column=target_col)

if __name__ == "__main__":
    main()
