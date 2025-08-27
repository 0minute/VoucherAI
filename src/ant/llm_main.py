# file: invoice_extract_pipeline.py
# 목적:
#  1) 이미지 경로와 OCR JSON을 입력으로 받는다.
#  2) OCR JSON에는 텍스트 및 좌표가 있음.
#  3) 유저 프롬프트(지정된 형식)와 함께 LLM에 컨텍스트를 전달한다.
#  4) LLM의 출력은 반드시 아래 JSON만 포함하도록 강제한다.
#     {"날짜": [추출한 날짜], "거래처": [추출한 거래처], "금액": [추출한 금액]}

from __future__ import annotations
import json
import re
import os
from typing import Any, Dict, List, Tuple
from src.ant.utils import _image_path_to_data_url, _as_list_of_obj, _normalize_token_ko, _normalize_bizno
from src.ant.ocr_document import OCRDocument
from src.ant.visualization import build_selections_for_viz, draw_overlays, export_thumbnails
# ──────────────────────────────────────────────────────────────────────────────
# 0) 외부 제공 함수: load_llm_model
#    (질문에 주신 함수를 같은 모듈/패키지 내에서 import 해 쓰면 됩니다)
from src.ant.load_llm import load_llm_model  # <- 당신 환경에 맞게 경로 조정
# ──────────────────────────────────────────────────────────────────────────────
# 2) 전처리 함수
from src.ant.preprocessing import (_find_date_candidates, 
                                   _find_amount_candidates, 
                                   _find_company_like, 
                                   _find_bizno_candidates, 
                                   _find_ceo_candidates, 
                                   _find_address_candidates, 
                                   build_candidates, 
                                   add_account_name, 
                                   add_artist_name, 
                                   add_vendor_code,
                                   add_file_id)
# ──────────────────────────────────────────────────────────────────────────────
# 3) LLM 컨텍스트 구성
from src.ant.constants import SYSTEM_PROMPT, USER_HARD_PROMPT, CATEGORY, ACCOUNT_MAP, ACCOUNT_CODE_MAP, REQUIRED_FIELDS, RESULT_FIELDS, DOCUMENT_TYPE

from src.ant.categorize import _normalize_token_ko
from src.utils.constants import LLM_MODEL_NAME, OVERLAY_DIR, THUMBNAIL_DIR, EXTRACTED_JSON_DIR, VENDOR_TABLE_PATH
from loguru import logger


def build_llm_messages(doc: OCRDocument) -> List[Dict[str, object]]:
    """
    완전 LLM 판단 모드:
    - 카테고리 키워드/후보는 제공하지 않고,
      CATEGORY '허용 목록'만 제공하여 모델이 문맥/이미지로 1개를 선택하도록 유도.
    """

    # 1) 날짜/금액/거래처 후보 (텍스트 후보는 그대로 활용: 정확도↑/토큰 효율↑)
    date_cands = _find_date_candidates(doc)
    amt_cands  = _find_amount_candidates(doc)
    co_cands   = _find_company_like(doc.raw_text_lines)
    bizno_cands = _find_bizno_candidates(doc.raw_text_lines)
    ceo_cands   = _find_ceo_candidates(doc.raw_text_lines)
    addr_cands  = _find_address_candidates(doc.raw_text_lines)

    # 표/금액 구조 힌트 라인
    key_lines = []
    for ln in doc.raw_text_lines:
        if any(k in ln for k in ["공급가액", "세액", "합계", "품목", "공 급 받 는 자", "공급자"]):
            key_lines.append(ln.strip())
    for ln in doc.raw_text_lines:
        if any(k in ln for k in ["주식회사", "(주)", "㈜"]):
            key_lines.append(ln.strip())

    # 후보 레지스트리(ID+좌표)
    candidates = build_candidates(doc, max_items=200)

    context_obj = {
        "이미지": doc.source_image,
        "후보": {
            "날짜": date_cands[:5],
            "금액": amt_cands[:8],
            "거래처": co_cands[:6],
            "사업자등록번호": bizno_cands,
            "대표자": ceo_cands,
            "주소": addr_cands,
        },
        "CATEGORY": list(dict.fromkeys(CATEGORY)),  # 카테고리는 '목록'만 제공
        "DOCUMENT_TYPE": list(dict.fromkeys(DOCUMENT_TYPE)),  # 증빙유형은 '목록'만 제공
        "힌트라인": key_lines[:16],
        "candidates": candidates,                   # ← 핵심: ID + bbox 제공
        "참고": (
            "세금계산서의 합계 = 공급가액 + 세액. 거래처는 보통 상대방 회사명 한 개. "
            "유형은 반드시 CATEGORY 목록 중 단 하나를 선택."
        ),
    }

    # 멀티모달 메시지 만들기
    user_content = [
        {"type": "text", "text": json.dumps(context_obj, ensure_ascii=False)},
    ]
    if doc.source_image:
        try:
            data_url = _image_path_to_data_url(doc.source_image)
            user_content.append({
                "type": "image_url",
                "image_url": {"url": data_url, "detail": "high"},
            })
        except Exception:
            pass
    user_content.append({"type": "text", "text": USER_HARD_PROMPT})

    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]

# ──────────────────────────────────────────────────────────────────────────────
# 4) LLM 호출 + 사후검증 (출력은 JSON만!)
def call_llm_and_parse(
    model_name: str,
    messages: List[Dict[str, str]],
) -> Dict[str, Any]:
    """
    LLM에 messages를 전달하고, 그 결과를 JSON으로 파싱·검증하는 함수.
    - LLM이 불필요한 텍스트(설명, 마크다운 등)를 출력하더라도
      JSON 블록만 안전하게 추출하여 반환.
    """
    # 1) LLM 모델 로드 (LangChain ChatOpenAI 객체)
    llm = load_llm_model(model_name)

    # 2) LLM 호출: messages를 입력으로 대화 수행
    resp = llm.invoke(messages)  # LangChain ChatOpenAI 호환 메서드

    # 3) 결과 문자열 추출
    raw = resp.content if hasattr(resp, "content") else str(resp)

    # 4) 출력 전처리: 앞뒤 공백 제거
    raw = raw.strip()

    # 5) LLM 출력에 JSON 이외 텍스트가 섞였을 경우,
    #    '{ ... }' 첫 블록만 정규식으로 추출
    if not raw.startswith("{"):
        m = re.search(r"\{.*\}", raw, flags=re.DOTALL)
        if m:
            raw = m.group(0).strip()

    # 6) JSON 파싱 시도
    try:
        data = json.loads(raw)
    except Exception:
        # 파싱 실패 시: 키에 따옴표가 없는 경우를 보정
        # 예: {날짜: "2023-03-31"} → {"날짜": "2023-03-31"}
        raw = re.sub(r"(\w+):", r'"\1":', raw)
        data = json.loads(raw)

    # 7) 사후 검증 및 형식 보정
    _validate_and_coerce(data)

    return data


def _validate_and_coerce(data: Dict[str, Any]) -> None:
    # 필수키
    required = ["날짜", "거래처", "금액", "유형", "사업자등록번호", "대표자", "주소"]
    for k in required:
        if k not in data:
            raise ValueError(f"LLM 결과에 '{k}' 키가 없습니다.")

    # 리스트 강제 (value/source_id 구조)
    for k in ["날짜", "거래처", "금액", "사업자등록번호", "대표자", "주소"]:
        data[k] = _as_list_of_obj(data[k])

    # 유형은 목록 중 1개만
    v = data["유형"]
    if isinstance(v, list):
        pass
    else:
        data["유형"] = [v]
    allowed = list(dict.fromkeys(CATEGORY))
    allowed_norm = { _normalize_token_ko(c): c for c in allowed }

    coerced_cat: List[str] = []
    for u in data["유형"]:
        u_str = str(u).strip()
        if u_str in allowed:
            coerced_cat.append(u_str); break
        u_norm = _normalize_token_ko(u_str)
        if u_norm in allowed_norm:
            coerced_cat.append(allowed_norm[u_norm]); break
        matches = [c for n,c in allowed_norm.items() if (n in u_norm) or (u_norm in n)]
        if matches:
            coerced_cat.append(matches[0]); break
    data["유형"] = coerced_cat[:1]

    # 날짜 정규화
    for item in data["날짜"]:
        ds = str(item["value"]).strip()
        m = re.search(r"(19|20)\d{2}[-/.]?(0[1-9]|1[0-2])[-/.]?(0[1-9]|[12]\d|3[01])", ds)
        if m:
            item["value"] = f"{m.group(1)}-{m.group(2)}-{m.group(3)}"

    # 금액 정규화
    for item in data["금액"]:
        s = str(item["value"]).replace(",", "").strip()
        if re.fullmatch(r"-?\d+(\.\d+)?", s):
            item["value"] = s
        else:
            m = re.search(r"-?\d{1,3}(?:,\d{3})+|\d+(\.\d+)?", str(item["value"]))
            if m:
                item["value"] = m.group(0).replace(",", "")

    # 사업자등록번호 정규화
    for item in data["사업자등록번호"]:
        item["value"] = _normalize_bizno(item["value"])
        # 하이픈 3-2-5 형태면 OK. 아니면 그대로(후속 처리에 맡김)

    # 거래처/대표자/주소 공백 정리
    for k in ["거래처", "대표자", "주소"]:
        for item in data[k]:
            item["value"] = str(item["value"]).strip()

    # 중복 제거(필드별 value 기준)
    def _dedup(items: List[Dict[str, Any]]):
        seen = set(); out=[]
        for it in items:
            key = (it["value"], it.get("source_id"))
            if key in seen: continue
            seen.add(key); out.append(it)
        return out

    for k in ["날짜","거래처","금액","사업자등록번호","대표자","주소"]:
        data[k] = _dedup(data[k])

# ──────────────────────────────────────────────────────────────────────────────
# 5) 파이프라인 진입점
# def extract_invoice_fields(ocr_json: Dict[str, Any], model_name: str = "gpt4o_latest") -> Dict[str, Any]:
#     """
#     하위호환: 기존 스키마 유지(필드별 값 리스트만 반환).
#     (value/source_id 구조는 내부적으로 보정 후 value만 남김)
#     """
#     doc = OCRDocument.from_raw(ocr_json)
#     messages = build_llm_messages(doc)
#     raw = call_llm_and_parse(model_name, messages)
#     _validate_and_coerce(raw)  # value/source_id 구조로 정리됨

#     # value만 추려서 하위호환 출력
#     def _vals(items: List[Dict[str, Any]]):
#         return [it["value"] for it in items]

#     out = {
#         "날짜": _vals(raw["날짜"]),
#         "거래처": _vals(raw["거래처"]),
#         "금액": _vals(raw["금액"]),
#         "유형": raw["유형"],  # ["카테고리"]
#         "사업자등록번호": _vals(raw["사업자등록번호"]),
#         "대표자": _vals(raw["대표자"]),
#         "주소": _vals(raw["주소"]),
#     }
#     return out

def extract_with_locations(ocr_json, artist_name: str = None, model_name: str = "gpt4o_latest") -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    확장 버전:
    - 반환 1: 구조화 결과(data)  → 각 필드가 [{"value","source_id"}] 구조
    - 반환 2: candidates         → [{"id","text","bbox","tag"}] 전체 후보 레지스트리
    - 반환 3: selections         → 시각화용 [{"field","value","source_id","bbox"}]

    input:
    - artist_name: OCR 이전 단계에서 사용자가 입력한 아티스트명 정보
    - ocr_json: OCR 결과 딕셔너리
    """
    if isinstance(ocr_json, str):
        ocr_json = json.loads(ocr_json)
    elif isinstance(ocr_json, dict):
        pass
    else:
        raise ValueError("ocr_json must be a string or a dictionary")

    doc = OCRDocument.from_raw(ocr_json)
    messages = build_llm_messages(doc)

    # context_obj 안에 들어간 candidates를 다시 꺼내 쓸 수 없으므로
    # 동일 로직으로 한 번 더 생성(혹은 build_llm_messages가 반환하도록 바꿔도 됨)
    candidates = build_candidates(doc, max_items=200)

    data = call_llm_and_parse(model_name, messages)
    _validate_and_coerce(data)
    add_account_name(data)
    selections = build_selections_for_viz(data, candidates)
    add_artist_name(data,artist_name)
    add_vendor_code(data)
    add_file_id(data, ocr_json.get("source_image"))
    return data, candidates, selections


def extract_with_locations_and_save(ocr_json: Dict[str, Any], model_name: str = "gpt4o_latest") -> Tuple[Dict[str, Any], List[Dict[str, Any]], List[Dict[str, Any]]]:
    data, candidates, selections = extract_with_locations(ocr_json, model_name)
    img_path = ocr_json.get("source_image")  # 원본 이미지 경로가 OCR JSON에 있어야 함
    if img_path and os.path.exists(img_path):
        filename = os.path.basename(img_path)
        filename_without_extension = os.path.splitext(filename)[0]
        overlay_path = os.path.join(OVERLAY_DIR, f"{filename_without_extension}_overlay.png")
        thumbnail_path = os.path.join(THUMBNAIL_DIR, f"{filename_without_extension}_thumbnails")
        draw_overlays(img_path, selections, overlay_path)
        export_thumbnails(img_path, selections, thumbnail_path, margin=0.06)
    else:
        print("원본 이미지 경로가 없습니다.")
    return data, overlay_path, thumbnail_path
# ============================================================
# 7) 사용 예시

# ============================================================
if __name__ == "__main__":
    # 1) 추출 + 위치정보
    with open(os.path.join(EXTRACTED_JSON_DIR, "TI-1.json"), "r", encoding="utf-8") as f:
        ocr = json.load(f)

    data, overlay_path, thumbnail_path = extract_with_locations_and_save(ocr, model_name="gpt4o_latest")

    # 4) 하위호환 결과만 필요하면:
    # print(json.dumps(extract_invoice_fields(ocr), ensure_ascii=False, indent=2))