
# ──────────────────────────────────────────────────────────────────────────────
# 2) 전처리: 후보 추출(LLM 토큰 절약 + 품질 보강)
# - OCR 전체 텍스트를 그대로 넘기면 토큰 낭비 + 혼선 발생 가능
# - 규칙 기반으로 날짜/금액/거래처 "후보"를 줄여서 LLM에 전달
# - LLM은 이 후보 중심으로 단일 값을 결정 → 품질↑/비용↓(1차 전처리)
from src.ant.constants import KOREAN_CO_PREFIXES, ACCOUNT_MAP, ACCOUNT_CODE_MAP
from typing import List, Dict, Any, Optional
from src.ant.ocr_document import OCRDocument
from src.ant.utils import _normalize_bbox
import re
from loguru import logger
from src.utils.constants import VENDOR_TABLE_PATH
import json
from src.api.upload import _normalize_rel

def _is_amount_token(s: str) -> bool:
    """
    문자열이 '금액/숫자'처럼 보이는지 간단히 판단.
    허용 예: 26,700 / 24,272 / 2,428 / -13,500 / 1234 / 1234.56
    - 천단위 콤마(,) 허용
    - 음수 기호(-) 허용
    - 소수점(.) 허용
    """
    return bool(
        re.fullmatch(
            r"-?\d{1,3}(,\d{3})+(?:\.\d+)?|-?\d+(?:\.\d+)?",
            s,
        )
    )


def _normalize_amount(s: str) -> str:
    """
    금액 문자열의 표면 정규화:
    - 쉼표(,) 제거
    - 앞뒤 공백 제거
    원문 표시가 필요한 경우가 아니면 내부 처리에는 보통 쉼표를 제거해 numeric 캐스팅을 쉽게 함.
    """
    return s.replace(",", "").strip()


def _find_company_like(lines: List[str]) -> List[str]:
    """
    거래처(회사명) 후보 추출:
    - 라인에 한국 법인형태 접두(주식회사, (주), ㈜, 유한회사, …)가 들어가면 후보로 수집
    - 도메인 특화 키워드(예: 오늘의집) 같은 브랜드명도 추가로 수집(예시)
    - 순서 보존 + 중복 제거(dict.fromkeys 트릭)
    """
    cands: List[str] = []

    # 1) 접두 패턴이 포함된 라인 수집
    for ln in lines:
        t = ln.strip()
        if any(p in t for p in KOREAN_CO_PREFIXES):
            cands.append(t)

    # 2) 프로젝트/도메인 특화 키워드 수집(필요시 확장 가능)
    for ln in lines:
        if "오늘의집" in ln and ln not in cands:
            cands.append(ln)

    # 3) 중복 제거(순서 유지): dict.fromkeys를 리스트로 다시 감싸기
    return list(dict.fromkeys(cands))


def _find_amount_candidates(doc: "OCRDocument") -> List[str]:
    """
    금액 후보 추출:
    - structured numbers(엔진이 뽑아준 숫자들) 중 금액 패턴과 매칭되는 것 수집
    - text_boxes의 원시 텍스트에서도 공백 제거 후 금액 패턴 매칭
    - 최종적으로 중복 제거(순서 보존)
    """
    cands: List[str] = []

    # 1) 구조화 숫자 사전에서 후보 추출
    for n in doc.numbers:
        if _is_amount_token(n):
            cands.append(n)

    # 2) 텍스트 박스에서 직접 금액 모양 탐색(예: 표 셀 값)
    for tb in doc.text_boxes:
        # 공백이 섞인 "2, 428" 같은 경우를 위해 공백 제거 후 판별
        t = tb.text.replace(" ", "")
        if _is_amount_token(t):
            cands.append(t)

    # 3) 중복 제거 + 순서 보존
    return list(dict.fromkeys(cands))


def _find_date_candidates(doc: "OCRDocument") -> List[str]:
    """
    날짜 후보 추출:
    - OCR structured dates(엔진이 이미 날짜로 분류한 값)를 우선 채용
    - 그 외 raw_text_lines 전체를 정규식으로 스캔해서 YYYY-MM-DD/YY.MM.DD/무구분 등 다양한 표기를 포착
    - 포착되면 일관된 'YYYY-MM-DD' 형태로 정규화해서 추가
    - 최종적으로 중복 제거(순서 보존)

    정규식 설명:
    - (20\\d{2}) 또는 (19\\d{2}) → 1900~2099년
    - [-/.]? → 구분자(없어도 되고 -, /, . 허용)
    - (0[1-9]|1[0-2]) → 월
    - (0[1-9]|[12]\\d|3[01]) → 일
    - \b 경계로 숫자 덩어리의 경계를 잡아 '오탑' 매칭을 줄임
    """
    # 다양한 년도 케이스(1900~2099)
    patterns = [
        r"\b(20\d{2})[-/.]?(0[1-9]|1[0-2])[-/.]?(0[1-9]|[12]\d|3[01])\b",
        r"\b(19\d{2})[-/.]?(0[1-9]|1[0-2])[-/.]?(0[1-9]|[12]\d|3[01])\b",
    ]

    seen = set()                 # 중복 체크용
    out: List[str] = list(doc.dates)  # 엔진이 뽑은 날짜 후보를 먼저 담아 둠

    # 라인 단위로 샅샅이 스캔
    for ln in doc.raw_text_lines:
        for pat in patterns:
            for m in re.finditer(pat, ln):
                y, mm, dd = m.group(1), m.group(2), m.group(3)
                norm = f"{y}-{mm}-{dd}"  # 일관된 포맷으로 정규화
                if norm not in seen:
                    out.append(norm)
                    seen.add(norm)

    # 단순히 중복만 제거(등장 횟수/위치 기반 가중치는 여기선 생략)
    return list(dict.fromkeys(out))


# 신규 필드 간단 후보
def _find_bizno_candidates(lines: List[str]) -> List[str]:
    out = []
    for ln in lines:
        for m in _BIZNO_PAT.finditer(ln):
            out.append(f"{m.group(1)}-{m.group(2)}-{m.group(3)}")
    return list(dict.fromkeys(out))[:4]

def _find_ceo_candidates(lines: List[str]) -> List[str]:
    out = []
    name_like = re.compile(r"[가-힣A-Za-z]{2,10}")
    for ln in lines:
        if any(k in ln for k in ["대표자", "성명"]):
            cleaned = re.sub(r"[\[\]()<>{}]", " ", ln)
            out.extend([m.group(0) for m in name_like.finditer(cleaned)])
    return list(dict.fromkeys(out))[:6]

def _find_address_candidates(lines: List[str]) -> List[str]:
    out = []
    for ln in lines:
        if "주소" in ln:
            s = ln.strip()
            part = re.split(r"주소[:\s]*", s, maxsplit=1)
            cand = part[1].strip() if len(part) > 1 and part[1].strip() else s
            out.append(cand)
    return list(dict.fromkeys(out))[:4]

# ============================================================
# 1) 후보 레지스트리: ID + 텍스트 + 상대좌표 + 태그
#    (LLM은 이 레지스트리의 id만 선택 → 좌표를 안정적으로 추적)
# ============================================================

# 간단 패턴들
_BIZNO_PAT = re.compile(r"\b(\d{3})[-–](\d{2})[-–](\d{5})\b")

def _tag_for_text(tb_text: str) -> Optional[str]:
    """
    텍스트 내용을 바탕으로 대략적인 태그를 부여(가벼운 휴리스틱).
    - amount/date/company/keyword/bizno/name/address/other
    - 필요 시 확장 가능. (여기서는 간결 버전)
    """
    t = tb_text.strip()
    t_no_space = t.replace(" ", "")

    # 키워드
    if any(k in t for k in ["공급가액", "세액", "합계", "품목", "공 급 받 는 자", "공급자", "비고"]):
        return "keyword"

    # 회사명(단순)
    if any(k in t for k in ["주식회사", "(주)", "㈜"]):
        return "company"

    # 주소/대표자(키워드 기반)
    if "주소" in t:
        return "address"
    if any(k in t for k in ["대표자", "성명"]):
        return "name"

    # 사업자등록번호
    if _BIZNO_PAT.search(t):
        return "bizno"

    # 날짜(널리 허용)
    if re.search(r"\b(19|20)\d{2}[-/.]?(0[1-9]|1[0-2])[-/.]?(0[1-9]|[12]\d|3[01])\b", t):
        return "date"

    # 금액
    if _is_amount_token(t_no_space):
        return "amount"

    # 기타는 None 처리(필요시 'other'로도 표기 가능)
    return None

def build_candidates(doc: OCRDocument, max_items: int = 200) -> List[Dict[str, Any]]:
    """
    텍스트 박스들에서 '태그가 있는 것'만 골라 후보 레지스트리 생성.
    - 각 항목: {id, text, bbox(0~1), tag}
    - 페이지 개념이 없으면 p0 고정. (PDF 다페이지면 page 번호 붙이도록 확장)
    """
    # 문서 크기 추정
    W = max((tb.bbox[2] for tb in doc.text_boxes), default=1)
    H = max((tb.bbox[3] for tb in doc.text_boxes), default=1)

    candidates: List[Dict[str, Any]] = []
    idx = 0
    for tb in doc.text_boxes:
        tag = _tag_for_text(tb.text)
        if not tag:
            continue
        cid = f"p0_{idx:05d}"
        candidates.append({
            "id": cid,
            "text": tb.text.strip(),
            "bbox": _normalize_bbox(tb.bbox, W, H),
            "tag": tag,
        })
        idx += 1
        if len(candidates) >= max_items:
            break
    return candidates


def add_account_name(data: Dict[str, Any]):
    category_name = data["유형"]
    if isinstance(category_name, list):
        category_name = category_name[0] if len(category_name) > 0 else None
    if category_name in ACCOUNT_MAP:
        data["계정과목"] = ACCOUNT_MAP[category_name]
    else:
        raise ValueError(f"ACCOUNT_MAP에 {category_name} 키가 없습니다.")
    
    if data["계정과목"] in ACCOUNT_CODE_MAP:
        data["계정코드"] = ACCOUNT_CODE_MAP[data["계정과목"]]
    else:
        raise ValueError(f"ACCOUNT_CODE_MAP에 {data['계정과목']} 키가 없습니다.")
    

def add_artist_name(data: Dict[str, Any], artist_name: str = None) -> None:
    data["프로젝트명"] = artist_name
    return data

def load_vendor_table() -> Dict[str, Any]:
    with open(VENDOR_TABLE_PATH, "r", encoding="utf-8") as f:
        vendor_table = json.load(f)
    return vendor_table

def add_vendor_code(data: Dict[str, Any]) -> None:
    vendor_table = load_vendor_table()
    vendor_code = vendor_table.get(data["사업자등록번호"][0]["value"]) # 리스트 형태 유지할것인지 고민
    # vendor_code = vendor_table.get(data["사업자등록번호"])
    if vendor_code:
        data["거래처코드"] = vendor_code["code"]
        data["거래처명"] = vendor_code["name"]
        logger.info(f"거래처 코드 추가 완료: {data['사업자등록번호']} -> {data['거래처코드']}")
    return data

def add_file_id(data: Dict[str, Any], file_path: str) -> None:
    data["file_id"] = _normalize_rel(file_path)
    return data