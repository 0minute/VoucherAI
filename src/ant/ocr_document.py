# 1) 데이터 모델
from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple

@dataclass
class OCRTextBox:
    """
    OCR로 추출된 '한 덩어리 텍스트'를 표현하는 구조체.
    - text: 인식된 문자열
    - confidence: 인식 신뢰도(0.0 ~ 1.0 사이로 들어오는 경우가 많음)
    - bbox: 이미지 좌표계에서의 텍스트 박스 경계(왼쪽, 위, 오른쪽, 아래)
      ※ 좌표 단위는 보통 픽셀. 이미지 원점(0,0)은 좌상단 기준이 일반적.
    """
    text: str
    confidence: float
    bbox: Tuple[int, int, int, int]  # (left, top, right, bottom)

@dataclass
class OCRDocument:
    """
    하나의 OCR 결과(문서 단위)를 담는 컨테이너.
    - source_image: 원본 이미지 경로 (없을 수도 있어 Optional)
    - text_boxes: 문서 내 모든 텍스트 박스 목록
    - raw_text_lines: OCR 엔진이 라인 단위로 정리해 준 문자열들(전처리·후처리에 유용)
    - dates: OCR 엔진이 날짜로 인식/후처리한 후보들(YYYY-MM-DD 등)
    - numbers: 숫자/금액 후보들(쉼표 포함 문자열 그대로 보관)
      ※ 이후 단계에서 금액 후보 필터링 등에 활용
    """
    source_image: Optional[str]
    text_boxes: List[OCRTextBox]
    raw_text_lines: List[str]
    dates: List[str]
    numbers: List[str]

    @classmethod
    def from_raw(cls, ocr_json: Dict[str, Any]) -> "OCRDocument":
        """
        OCR 엔진이 반환한 JSON(dict)을 안전하게 파싱해서 OCRDocument로 변환.

        방어적 파싱 포인트:
        - 키가 없을 수 있으므로 dict.get(..., 기본값) 사용
        - None 또는 빈 값이 들어와도 처리되도록 `or {}` / `or []` 패턴 사용
        - 문자열은 .strip()으로 앞뒤 공백 제거(후속 규칙 매칭에 중요)
        - 숫자/좌표는 캐스팅 시 예외 방지를 위해 기본값과 형 변환 적용
        """
        tboxes: List[OCRTextBox] = []

        # 1) 텍스트 박스들 파싱: ocr_json["text_boxes"]는 보통 리스트 형태
        for tb in ocr_json.get("text_boxes", []):
            # 원 데이터에서 값 꺼내기(없으면 기본값)
            raw_text = (tb.get("text", "") or "").strip()

            # confidence는 float로 변환 시도(없거나 변환 불가하면 0.0)
            try:
                conf = float(tb.get("confidence", 0.0))
            except (TypeError, ValueError):
                conf = 0.0

            # bbox는 [left, top, right, bottom] 형태가 일반적.
            # 없거나 길이가 다르면 0으로 패딩해서 길이 4를 보장.
            bbox_raw = tb.get("bbox", [0, 0, 0, 0]) or [0, 0, 0, 0]
            # 안전하게 길이 4로 맞추기
            if not isinstance(bbox_raw, (list, tuple)):
                bbox_raw = [0, 0, 0, 0]
            if len(bbox_raw) < 4:
                bbox_raw = list(bbox_raw) + [0] * (4 - len(bbox_raw))
            # 정수 캐스팅 + 튜플 고정
            bbox = tuple(int(bbox_raw[i]) for i in range(4))

            # OCRTextBox 인스턴스 생성 후 누적
            tboxes.append(OCRTextBox(text=raw_text, confidence=conf, bbox=bbox))

        # 2) 구조화 섹션(엔진별로 달라짐): dates, numbers, raw_text_lines 등
        structured = ocr_json.get("structured_data", {}) or {}

        # raw_text_lines: 후속 규칙/정규식 처리에 유용하므로 문자열 정리
        raw_lines_src = structured.get("raw_text_lines", []) or []
        raw_lines = [str(x).strip() for x in raw_lines_src]

        # dates: OCR이 '날짜'라고 인식한 후보들. 형식은 엔진에 따라 다름.
        dates_src = structured.get("dates", []) or []
        dates = [str(d).strip() for d in dates_src]

        # numbers_and_amounts: {"number_0": "24,272", ...} 식의 dict일 수 있음.
        # 값들만 뽑아 리스트로 변환. 숫자/통화 정규화는 후단에서 처리.
        nums_dict = structured.get("numbers_and_amounts", {}) or {}
        numbers = [str(v).strip() for v in nums_dict.values()]

        # 3) OCRDocument 생성해서 반환
        return cls(
            source_image=ocr_json.get("source_image"),
            text_boxes=tboxes,
            raw_text_lines=raw_lines,
            dates=dates,
            numbers=numbers,
        )
