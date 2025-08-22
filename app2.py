# app_entertainment.py
# Streamlit demo UI tailored for Entertainment companies (Agency/Label/Production)
# Focus: Sleek design, domain presets (Artist/Project), OCR→LLM→Review→Journal→Export
# Run: streamlit run app_entertainment.py
# pip install -U streamlit pillow pandas numpy pydantic xlsxwriter

from __future__ import annotations
import io
import json
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
import streamlit as st

# =============================
# Theme & CSS (Sleek, agency vibe)
# =============================
st.set_page_config(page_title="ENT·AI Invoice → Journal", layout="wide", page_icon="🎬")

CSS = """
<style>
/******* Root palette *******/
:root { --brand:#7c3aed; --ink:#101114; --muted:#6b7280; --card:#0f1115; --surface:#111317; --accent:#14b8a6; }

/******* Global *******/
.block-container { padding-top: 1.2rem; max-width: 1500px; }
h1,h2,h3,h4 { font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Inter, 'Noto Sans KR', sans-serif; }

/******* Hero *******/
.hero { position: relative; padding: 28px 28px; border-radius: 16px; overflow: hidden; background: radial-gradient(1200px 400px at 20% -10%, rgba(124,58,237,0.35), transparent), linear-gradient(135deg, #0f1115 0%, #171923 100%); border:1px solid rgba(255,255,255,0.06); }
.hero h2 { color: #fff; margin: 0; font-size: 24px; letter-spacing: .2px; }
.hero p { color: #cbd5e1; margin-top: 6px; }
.badge { display:inline-flex; align-items:center; gap:6px; padding:6px 10px; border-radius:999px; font-size:12px; color:#e5e7eb; background:rgba(124,58,237,0.18); border:1px solid rgba(124,58,237,0.35); }
.kpi { display:flex; gap:12px; }
.kpi .card { flex:1; padding:14px; border-radius:14px; background:var(--card); border:1px solid rgba(255,255,255,0.06); color:#e5e7eb; }
.kpi .label { font-size:12px; color:#9ca3af; }
.kpi .value { font-size:20px; font-weight:600; }

/******* Section card *******/
.section { padding:16px; border-radius:16px; background:var(--surface); border:1px solid rgba(255,255,255,0.06); margin-top:16px; }
.section h3 { color:#fff; margin-top:0; }

/******* Table tweaks *******/
[data-testid="stDataFrame"] { border-radius: 12px; overflow:hidden; border:1px solid rgba(255,255,255,0.06);}

/******* Buttons *******/
.stButton>button { border-radius: 10px; border:1px solid rgba(255,255,255,0.12); background: linear-gradient(180deg, rgba(124,58,237,.8), rgba(124,58,237,.65)); color:white; }
.stDownloadButton>button { border-radius: 10px; border:1px solid rgba(255,255,255,0.12); background: linear-gradient(180deg, rgba(20,184,166,.85), rgba(20,184,166,.65)); color:white; }

/******* Chips *******/
.chips { display:flex; gap:8px; flex-wrap:wrap; }
.chip { padding:6px 10px; border-radius:999px; background:#0b0d12; border:1px solid rgba(255,255,255,0.08); color:#cbd5e1; font-size:12px; }

</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# =============================
# Domain constants (Entertainment)
# =============================
FIELD_COLORS = {
    "날짜": (124, 58, 237),          # brand purple
    "거래처": (20, 184, 166),        # accent teal
    "금액": (234, 179, 8),           # amber
    "사업자등록번호": (34, 197, 94),  # green
    "대표자": (239, 68, 68),         # red
    "주소": (59, 130, 246),          # blue
    "아티스트": (168, 85, 247),      # violet
    "활동유형": (244, 114, 182),     # pink
}

ARTIST_MASTER = [
    {"artist":"A-STAR","team":"Solo","project":"2025 WORLD TOUR"},
    {"artist":"G-IDOLZ","team":"Group","project":"NEW MINI ALBUM"},
    {"artist":"NEON B","team":"Solo","project":"Drama OST"},
]

VENDOR_PRESET = {
    "헤어/메이크업": {"acct":"헤어메이크업비","code":"515200","vat":0.1},
    "스타일링": {"acct":"스타일링비","code":"515210","vat":0.1},
    "안무/연습실": {"acct":"연습실임차료","code":"514300","vat":0.1},
    "대관": {"acct":"대관료","code":"514400","vat":0.1},
    "촬영/편집": {"acct":"영상제작비","code":"516100","vat":0.1},
    "홍보/마케팅": {"acct":"프로모션비","code":"518500","vat":0.1},
    "음원/유통": {"acct":"유통수수료","code":"521700","vat":0.0},
    "저작권": {"acct":"저작권료","code":"521800","vat":0.0},
}

# =============================
# Data models
# =============================
@dataclass
class Field:
    name: str
    value: Any
    bbox: Optional[Tuple[float, float, float, float]]  # normalized
    confidence: float
    source: str

@dataclass
class Page:
    page_no: int
    image_key: str
    fields: List[Field]

@dataclass
class Doc:
    file_id: str
    filename: str
    pages: List[Page]

SK_DOCS = "docs"
SK_EXTRACT = "extract_df"
SK_JE = "je_df"

# =============================
# Utils
# =============================

def _put_image_to_state(img: Image.Image) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="PNG")
    key = f"img:{uuid.uuid4()}"
    st.session_state[key] = buf.getvalue()
    return key


def _get_image(key: str) -> Image.Image:
    return Image.open(io.BytesIO(st.session_state[key])).convert("RGB")


def kr_brn_checksum(value: str) -> bool:
    """간이 한국 사업자등록번호 체크섬 (###-##-##### 형태 포함).
    참고: 실무용은 국세청 공식 규칙을 사용하세요.
    """
    digits = [int(c) for c in value if c.isdigit()]
    if len(digits) != 10:
        return False
    weights = [1,3,7,1,3,7,1,3,5]
    s = sum(d*w for d, w in zip(digits[:9], weights))
    s += (digits[8]*5)//10
    check = (10 - (s % 10)) % 10
    return check == digits[9]


def draw_overlays(img: Image.Image, fields: List[Field]) -> Image.Image:
    W, H = img.size
    out = img.copy(); dr = ImageDraw.Draw(out)
    try: font = ImageFont.load_default()
    except: font = None
    for f in fields:
        if not f.bbox: continue
        l,t,r,b = f.bbox
        box = (int(l*W), int(t*H), int(r*W), int(b*H))
        color = FIELD_COLORS.get(f.name, (255,255,255))
        # border
        for i in range(2):
            dr.rectangle((box[0]-i,box[1]-i,box[2]+i,box[3]+i), outline=color)
        # label
        label = f"{f.name} {f.confidence:.2f}"
        tw = dr.textlength(label, font=font); th = (font.size if font else 12)
        pad=4
        pill = (box[0], max(0, box[1]-th-2*pad), box[0]+int(tw)+2*pad, box[1])
        dr.rectangle(pill, fill=color)
        dr.text((pill[0]+pad,pill[1]+pad), label, fill=(0,0,0), font=font)
    return out

# =============================
# Mock OCR / LLM (replace with actual engines)
# =============================

def run_ocr(img: Image.Image) -> List[Field]:
    seed = int(np.array(img.resize((8,8))).sum()) % 97
    rng = np.random.default_rng(seed)
    def bb():
        l = float(rng.uniform(0.05, 0.65)); t = float(rng.uniform(0.06, 0.78))
        w = float(rng.uniform(0.12, 0.3)); h = float(rng.uniform(0.04, 0.11))
        return (l,t,min(0.98,l+w),min(0.98,t+h))
    return [
        Field("날짜","2025-02-14",bb(),0.93,"ocr"),
        Field("거래처","Studio BLK",bb(),0.89,"ocr"),
        Field("금액", 330000, bb(),0.95,"ocr"),
    ]


def run_llm(ocr_fields: List[Field], meta: Dict[str,Any]) -> List[Field]:
    out = list(ocr_fields)
    # domain enrich
    out += [
        Field("사업자등록번호","123-45-67890", None, 0.82, "llm"),
        Field("아티스트", meta.get("artist","A-STAR"), None, 0.9, "llm"),
        Field("활동유형", meta.get("activity","뮤직비디오 촬영"), None, 0.88, "llm"),
        Field("주소","서울 강남구 테헤란로 123", None, 0.7, "llm"),
    ]
    return out

# =============================
# Build extract table & JE
# =============================

def build_extract(docs: List[Doc]) -> pd.DataFrame:
    rows = []
    for d in docs:
        for p in d.pages:
            fx = {f.name:f for f in p.fields}
            rec = {
                "file_id": d.file_id,
                "filename": d.filename,
                "page": p.page_no,
                "날짜": fx.get("날짜", Field("날짜","",None,0,"")).value,
                "거래처": fx.get("거래처", Field("거래처","",None,0,"")).value,
                "금액": fx.get("금액", Field("금액",0,None,0,"")).value,
                "사업자등록번호": fx.get("사업자등록번호", Field("사업자등록번호","",None,0,"")).value,
                "아티스트": fx.get("아티스트", Field("아티스트","",None,0,"")).value,
                "활동유형": fx.get("활동유형", Field("활동유형","",None,0,"")).value,
                "_image_key": p.image_key,
                "_trace": f"{d.filename}#p{p.page_no}",
            }
            # default mapping hint by activity
            rec["계정과목"] = VENDOR_PRESET.get("촬영/편집")["acct"]
            rec["계정코드"] = VENDOR_PRESET.get("촬영/편집")["code"]
            rows.append(rec)
    df = pd.DataFrame(rows)
    if not df.empty:
        df["금액"] = pd.to_numeric(df["금액"], errors="coerce").fillna(0).astype(float)
    return df


def map_account(activity: str) -> Tuple[str,str,float]:
    # naive rule: pick by keyword
    if any(k in activity for k in ["스타일", "코디", "의상"]):
        v = VENDOR_PRESET["스타일링"]; return v["acct"], v["code"], v["vat"]
    if any(k in activity for k in ["헤어","메이크업"]):
        v = VENDOR_PRESET["헤어/메이크업"]; return v["acct"], v["code"], v["vat"]
    if any(k in activity for k in ["연습실","안무"]):
        v = VENDOR_PRESET["안무/연습실"]; return v["acct"], v["code"], v["vat"]
    if any(k in activity for k in ["대관","공연장"]):
        v = VENDOR_PRESET["대관"]; return v["acct"], v["code"], v["vat"]
    if any(k in activity for k in ["홍보","마케팅","프로모"]):
        v = VENDOR_PRESET["홍보/마케팅"]; return v["acct"], v["code"], v["vat"]
    if any(k in activity for k in ["음원","유통"]):
        v = VENDOR_PRESET["음원/유통"]; return v["acct"], v["code"], v["vat"]
    if any(k in activity for k in ["저작권","저작료"]):
        v = VENDOR_PRESET["저작권"]; return v["acct"], v["code"], v["vat"]
    v = VENDOR_PRESET["촬영/편집"]; return v["acct"], v["code"], v["vat"]


def make_journal(df: pd.DataFrame, project: str) -> pd.DataFrame:
    if df.empty: return pd.DataFrame()
    rows = []
    for _, r in df.iterrows():
        acct, code, vat = map_account(str(r.get("활동유형","")))
        amt = float(r.get("금액",0) or 0)
        date = str(r.get("날짜",""))
        vendor = r.get("거래처","")
        artist = r.get("아티스트","")
        # Simple VAT split (if applicable) — expense recorded as gross by default; adjust as needed
        vat_amt = round(amt*vat, 0) if vat>0 else 0
        net_amt = amt - vat_amt
        # D- expense (net) + D- VAT input (if any), C- A/P
        ln = 1
        if net_amt>0:
            rows.append({"전표일자":date,"라인":ln,"계정코드":code,"계정과목":acct,"차대":"D","금액":net_amt,"거래처":vendor,"아티스트":artist,"프로젝트":project,"메모":r.get("_trace","")}); ln+=1
        if vat_amt>0:
            rows.append({"전표일자":date,"라인":ln,"계정코드":"133100","계정과목":"매입부가세","차대":"D","금액":vat_amt,"거래처":vendor,"아티스트":artist,"프로젝트":project,"메모":r.get("_trace","")}); ln+=1
        rows.append({"전표일자":date,"라인":ln,"계정코드":"211000","계정과목":"미지급금","차대":"C","금액":amt,"거래처":vendor,"아티스트":artist,"프로젝트":project,"메모":r.get("_trace","")})
    je = pd.DataFrame(rows)
    cols = ["전표일자","라인","계정코드","계정과목","차대","금액","거래처","아티스트","프로젝트","메모"]
    return je[cols]

# =============================
# Sidebar (Agency presets)
# =============================
with st.sidebar:
    st.markdown("<div class='badge'>🎵 Entertainment Mode</div>", unsafe_allow_html=True)
    agency = st.selectbox("소속사/레이블", ["HNX Entertainment","BlueLabel","Aurora Creative"])
    roster = [a["artist"] for a in ARTIST_MASTER]
    artist = st.selectbox("아티스트", roster)
    proj = st.text_input("프로젝트/캠페인", value=next((x["project"] for x in ARTIST_MASTER if x["artist"]==artist), "2025 NEW RELEASE"))
    activity = st.selectbox("활동유형", ["뮤직비디오 촬영","앨범 자켓","공연 대관","홍보/마케팅","연습실 대여","의상/스타일","헤어/메이크업","음원 유통","저작권"])
    st.markdown("<div class='chips'><span class='chip'>PII Mask</span><span class='chip'>On-Prem</span><span class='chip'>ERP Template: 더존</span></div>", unsafe_allow_html=True)

# =============================
# Hero & KPIs
# =============================
st.markdown("""
<div class="hero">
  <div class="badge">SaaS + On-Prem Ready · OCR → LLM → Journal</div>
  <h2>Entertainment Finance Automation</h2>
  <p>영수증/세금계산서에서 아티스트/활동 컨텍스트까지 자동 보강하고, 분개/템플릿까지 원클릭.</p>
  <div class="kpi">
    <div class="card"><div class="label">처리 문서</div><div class="value">Batch 24</div></div>
    <div class="card"><div class="label">평균 처리시간</div><div class="value">~1.4s/페이지</div></div>
    <div class="card"><div class="label">필드 정확도</div><div class="value">≥ 90%</div></div>
    <div class="card"><div class="label">엔터 도메인 룰</div><div class="value">8 Packs</div></div>
  </div>
</div>
""", unsafe_allow_html=True)

# =============================
# Sections
# =============================

st.markdown("<div class='section'>", unsafe_allow_html=True)
st.subheader("① 업로드")
uploads = st.file_uploader("이미지/스캔 업로드 (PNG/JPG)", type=["png","jpg","jpeg"], accept_multiple_files=True)

colA, colB = st.columns([1,1])
with colA:
    if st.button("샘플 이미지 불러오기", use_container_width=True):
        demo = []
        for i in range(3):
            img = Image.new("RGB", (1200, 1700), (18, 20, 28))
            d = ImageDraw.Draw(img); d.text((40,60), f"MV Invoice #{i+1}", fill=(220,220,230))
            demo.append(img)
        st.session_state["demo_files"] = [
            type("U", (), {"name": f"mv_{i+1}.png", "getvalue": (lambda im=im: _buf(im))}) for i,im in enumerate(demo)
        ]
        st.success("샘플 3건 준비 완료 → ②에서 OCR 실행")
with colB:
    st.write(" ")

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='section'>", unsafe_allow_html=True)
st.subheader("② OCR & 추출 (엔터 도메인 보강)")
files = uploads or st.session_state.get("demo_files", [])
if not files:
    st.info("파일을 업로드하거나 샘플을 불러오세요.")
else:
    if st.button("OCR & LLM 실행", type="primary"):
        docs: List[Doc] = []
        for uf in files:
            name = getattr(uf, "name", f"file_{uuid.uuid4()}.png")
            img = Image.open(io.BytesIO(uf.getvalue())).convert("RGB")
            fields = run_llm(run_ocr(img), {"artist": artist, "activity": activity})
            key = _put_image_to_state(img)
            docs.append(Doc(file_id=str(uuid.uuid4()), filename=name, pages=[Page(1, key, fields)]))
        st.session_state[SK_DOCS] = docs
        st.session_state[SK_EXTRACT] = build_extract(docs)
        st.success(f"처리 완료: {len(docs)}건")

if st.session_state.get(SK_DOCS):
    st.dataframe(pd.DataFrame([{ "파일": d.filename, "페이지": len(d.pages), "file_id": d.file_id } for d in st.session_state[SK_DOCS]]), use_container_width=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='section'>", unsafe_allow_html=True)
st.subheader("③ 검토 (원본 + 오버레이 / 테이블 인라인 편집)")
df = st.session_state.get(SK_EXTRACT, pd.DataFrame())
if df.empty:
    st.info("②에서 먼저 실행하세요.")
else:
    L, R = st.columns([1,1])
    with R:
        st.markdown("**추출 테이블**")
        edited = st.data_editor(df, use_container_width=True, num_rows="dynamic", hide_index=True,
            column_config={"_image_key": st.column_config.Column(disabled=True), "file_id": st.column_config.Column(disabled=True), "_trace": st.column_config.Column(disabled=True)})
        st.session_state[SK_EXTRACT] = edited
        # Quick validations
        bad_brn = edited[~edited["사업자등록번호"].astype(str).apply(kr_brn_checksum)] if "사업자등록번호" in edited else pd.DataFrame()
        if not bad_brn.empty:
            st.warning(f"사업자등록번호 유효성 경고 {len(bad_brn)}건 – 포맷/번호를 확인하세요.")
    with L:
        row = edited.iloc[0]
        img = _get_image(row["_image_key"]) 
        doc = next(d for d in st.session_state[SK_DOCS] if d.file_id == row["file_id"])
        over = draw_overlays(img, doc.pages[0].fields)
        st.image(over, use_column_width=True)

    st.divider()
    if st.button("선택/전체 → 분개 시뮬레이션", type="primary"):
        st.session_state[SK_JE] = make_journal(st.session_state[SK_EXTRACT], proj)
        st.success("④ 분개 탭으로 이동하여 확인")

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='section'>", unsafe_allow_html=True)
st.subheader("④ 분개 (VAT 분리 / 아티스트·프로젝트 차원)")
je = st.session_state.get(SK_JE, pd.DataFrame())
if je.empty:
    st.info("③에서 분개 시뮬레이션을 실행하세요.")
else:
    dsum = je.loc[je["차대"]=="D","금액"].sum(); csum = je.loc[je["차대"]=="C","금액"].sum()
    k1,k2,k3 = st.columns(3)
    with k1: st.metric("차변 합계", f"{dsum:,.0f}")
    with k2: st.metric("대변 합계", f"{csum:,.0f}")
    with k3: st.metric("균형", "OK" if abs(dsum-csum)<1e-6 else "Mismatch")
    st.dataframe(je, use_container_width=True, hide_index=True)

st.markdown("</div>", unsafe_allow_html=True)

st.markdown("<div class='section'>", unsafe_allow_html=True)
st.subheader("⑤ 내보내기")
col1,col2 = st.columns(2)
if not df.empty:
    with col1:
        b = df.to_csv(index=False).encode("utf-8-sig")
        st.download_button("📥 추출 테이블 CSV", b, file_name="extract_ent.csv")
if not je.empty:
    with col2:
        buf = io.BytesIO()
        with pd.ExcelWriter(buf, engine="xlsxwriter") as xw:
            je.to_excel(xw, sheet_name="JE", index=False)
        st.download_button("📥 분개 엑셀", buf.getvalue(), file_name="journal_ent.xlsx")

st.markdown("</div>", unsafe_allow_html=True)

# buffer util

def _buf(img: Image.Image) -> bytes:
    bio = io.BytesIO(); img.save(bio, format="PNG"); return bio.getvalue()
