from typing import List
from src.ant.constants import CATEGORY

def _normalize_token_ko(s: str) -> str:
    """간단 정규화: 공백 제거 + 소문자화(영문 혼용 대비)"""
    return str(s).strip().lower().replace(" ", "")

# def _find_category_candidates(lines: List[str]) -> List[str]:
#     """
#     영수증 유형(카테고리) 후보를 텍스트에서 뽑는다.
#     전략:
#       - CATEGORY 항목을 '부분 포함' 기준으로 탐색 (예: '판매대행수수료(03월)' → '판매대행수수료')
#       - 중복 제거, 순서 보존
#     주의:
#       - CATEGORY 안에 중복 항목이 있으므로(set으로 중복 제거하여 안전 처리)
#     """
#     cats = list(dict.fromkeys(CATEGORY))  # 목록 중복 제거
#     norm_lines = [_normalize_token_ko(x) for x in lines]
#     out: List[str] = []

#     for c in cats:
#         c_norm = _normalize_token_ko(c)
#         # 라인 중 하나라도 카테고리 문자열을 포함하면 후보로 채택
#         if any(c_norm in ln for ln in norm_lines):
#             out.append(c)

#     # 흔한 변형/표현(선택): 키워드→카테고리 맵핑(있으면 추가)
#     # 예: '수수료'가 많이 나오면 '판매대행수수료' 후보로 올리기 등.
#     # 필요 시 확장 가능.

#     return out[:8]  # 너무 길어지는 것 방지
