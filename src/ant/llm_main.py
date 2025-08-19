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
from typing import Any, Dict, List
from src.ant.utils import _image_path_to_data_url
from src.ant.ocr_document import OCRDocument
# ──────────────────────────────────────────────────────────────────────────────
# 0) 외부 제공 함수: load_llm_model
#    (질문에 주신 함수를 같은 모듈/패키지 내에서 import 해 쓰면 됩니다)
from src.ant.load_llm import load_llm_model  # <- 당신 환경에 맞게 경로 조정
# ──────────────────────────────────────────────────────────────────────────────
# 2) 전처리 함수
from src.ant.preprocessing import _find_date_candidates, _find_amount_candidates, _find_company_like
# ──────────────────────────────────────────────────────────────────────────────
# 3) LLM 컨텍스트 구성
from src.ant.constants import SYSTEM_PROMPT, USER_HARD_PROMPT, CATEGORY, ACCOUNT_MAP, REQUIRED_FIELDS, RESULT_FIELDS

from src.ant.categorize import _normalize_token_ko
from src.utils.constants import LLM_MODEL_NAME

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

    # 2) 표/금액 구조를 드러내는 힌트 라인(텍스트 컨텍스트 최소화 버전)
    key_lines = []
    for ln in doc.raw_text_lines:
        if any(k in ln for k in ["공급가액", "세액", "합계", "품목", "공 급 받 는 자", "공급자"]):
            key_lines.append(ln.strip())
    for ln in doc.raw_text_lines:
        if any(k in ln for k in ["주식회사", "(주)", "㈜"]):
            key_lines.append(ln.strip())

    # 3) LLM 컨텍스트: CATEGORY '목록'만 제공 (키워드/후보 제공 안 함)
    context_obj = {
        "이미지": doc.source_image,
        "후보": {
            "날짜": date_cands[:5],
            "금액": amt_cands[:8],
            "거래처": co_cands[:6],
        },
        "CATEGORY": list(dict.fromkeys(CATEGORY)),  # 허용 가능한 최종 선택지
        "힌트라인": key_lines[:16],
        "참고": (
            "세금계산서의 합계 = 공급가액 + 세액. 거래처는 보통 상대방 회사명 한 개. "
            "유형은 반드시 CATEGORY 목록 중 단 하나를 선택."
        ),
    }

    # 4) 이미지(Data URL) 포함 멀티모달 메시지 구성
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
    # 0) 필수 키 존재 검사 (유형 포함)
    for key in REQUIRED_FIELDS:
        if key not in data:
            raise ValueError(f"LLM 결과에 '{key}' 키가 없습니다.")

    # 1) 값들을 리스트로 강제
    for k in REQUIRED_FIELDS:
        v = data[k]
        if isinstance(v, (str, int, float)):
            data[k] = [v]
        elif not isinstance(v, list):
            data[k] = [str(v)]

    # 2) 날짜 정규화
    norm_dates = []
    for d in data["날짜"]:
        ds = str(d).strip()
        m = re.search(r"(19|20)\d{2}[-/.]?(0[1-9]|1[0-2])[-/.]?(0[1-9]|[12]\d|3[01])", ds)
        if m:
            norm_dates.append(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
        else:
            norm_dates.append(ds)
    data["날짜"] = list(dict.fromkeys(norm_dates))

    # 3) 금액 정규화
    norm_amts = []
    for a in data["금액"]:
        s = str(a).replace(",", "").strip()
        if re.fullmatch(r"-?\d+(\.\d+)?", s):
            norm_amts.append(s)
        else:
            m = re.search(r"-?\d{1,3}(?:,\d{3})+|\d+(\.\d+)?", str(a))
            if m:
                norm_amts.append(m.group(0).replace(",", ""))
    if norm_amts:
        data["금액"] = list(dict.fromkeys(norm_amts))

    # 4) 거래처 정리
    data["거래처"] = [str(x).strip() for x in data["거래처"] if str(x).strip()]

    # 5) 유형 검증: 반드시 CATEGORY 중 하나만 남김
    allowed = list(dict.fromkeys(CATEGORY))
    allowed_norm = { _normalize_token_ko(c): c for c in allowed }

    coerced: List[str] = []
    for u in data["유형"]:
        u_str = str(u).strip()
        if u_str in allowed:
            coerced.append(u_str)
            continue
        # 부분/정규화 일치로 보정 시도 (너무 공격적이면 제거 가능)
        u_norm = _normalize_token_ko(u_str)
        if u_norm in allowed_norm:
            coerced.append(allowed_norm[u_norm])
        else:
            # 부분 포함(양방향) 매칭
            matches = [c for n,c in allowed_norm.items()
                       if (n in u_norm) or (u_norm in n)]
            if matches:
                coerced.append(matches[0])

    # 하나도 매칭 안 되면 빈 리스트(상위 로직에서 처리). 하나 이상이면 1개만 유지.
    data["유형"] = coerced[:1]

    # 기타 로직에 따른 필드 추가
    data["계정과목"] = ACCOUNT_MAP[data["유형"][0]]

# ──────────────────────────────────────────────────────────────────────────────
# 5) 파이프라인 진입점
def extract_invoice_fields(
    ocr_json: Dict[str, Any],
    model_name: str = LLM_MODEL_NAME,  # 기본 LLM 모델명
) -> Dict[str, Any]:
    """
    OCR JSON(dict)을 입력받아
    날짜·거래처·금액만 추출한 딕셔너리로 반환.

    동작 순서:
    1) OCR JSON → OCRDocument 객체로 변환
    2) 후보/힌트 기반 LLM 메시지 생성
    3) LLM 호출 + 결과 파싱·검증
    4) 지정된 3개 키만 남기고 반환
    """
    if isinstance(ocr_json, str):
        with open(ocr_json, "r", encoding="utf-8") as f:
            ocr_json = json.load(f)
    else:
        ocr_json = ocr_json
    # 1) OCRDocument 생성
    doc = OCRDocument.from_raw(ocr_json)

    # 2) LLM에 줄 메시지 구성
    messages = build_llm_messages(doc)

    # 3) LLM 호출 및 파싱
    result = call_llm_and_parse(model_name, messages)

    # 4) 최종 보호막: 지정된 3개 키만 남기고 반환
    # 추가 후보: 증빙유형, 공급가액*부가세*합계금액분리/ 과세유형, 거래처 정보 강화(사업자등록번호, 대표자, 주소), 전표유형, 추천계정과목, 결제수단
    # 필드별 추출 근거 남길 수 있으면 좋음
    # 계정과목은 우선 추천계정 수준으로(1대 1 맵핑 > 추후 맥락 기준 정확도 향상 가능)
    whitelisted = {k: result.get(k, []) for k in RESULT_FIELDS}
    return whitelisted
# ──────────────────────────────────────────────────────────────────────────────
# 6) 사용 예시 (첨부하신 파일 경로 기준)
if __name__ == "__main__":
    with open("input/TI-1_extracted.json", "r", encoding="utf-8") as f:
        ocr = json.load(f)

    out = extract_invoice_fields(ocr, model_name="gpt4o_latest")
    # 요구사항상, 여기서도 JSON만 출력하고 싶은 경우:
    print(json.dumps(out, ensure_ascii=False))
