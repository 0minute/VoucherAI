import base64, mimetypes, os
import re
from typing import List, Dict, Any

def _image_path_to_data_url(path: str) -> str:
    """
    로컬 이미지 파일을 data URL(base64)로 인코딩.
    - OpenAI/멀티모달 API는 일반적으로 `image_url.url`에 http(s) 또는 data URL을 허용
    - 외부 URL이 없다면 data URL이 가장 간단한 방법
    """
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {path}")

    # 파일 확장자로 MIME 추정 (없으면 png로 fallback)
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        mime = "image/png"

    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime};base64,{b64}"

# ── 상대 bbox 정규화
def _normalize_bbox(bbox, width: int, height: int):
    l, t, r, b = bbox
    W = max(1, width); H = max(1, height)
    return [
        max(0.0, min(1.0, l / W)),
        max(0.0, min(1.0, t / H)),
        max(0.0, min(1.0, r / W)),
        max(0.0, min(1.0, b / H)),
    ]

def _normalize_token_ko(s: str) -> str:
    return str(s).strip().lower().replace(" ", "")

def _normalize_bizno(s: str) -> str:
    digits = re.sub(r"\D", "", str(s))
    if len(digits) == 10:
        return f"{digits[0:3]}-{digits[3:5]}-{digits[5:10]}"
    return str(s).replace("–", "-").strip()


def _as_list_of_obj(v) -> List[Dict[str, Any]]:
    """
    입력을 [{"value":..., "source_id":...}] 형태 리스트로 강제 변환.
    - 문자열/숫자만 오면 value로 래핑, source_id=None
    - dict로 오면 키 검사 후 보정
    """
    def _coerce_one(x):
        if isinstance(x, dict):
            val = x.get("value", x.get("val", x.get("text", "")))
            sid = x.get("source_id", x.get("id"))
            return {"value": str(val).strip(), "source_id": (str(sid).strip() if sid not in (None, "") else None)}
        else:
            return {"value": str(x).strip(), "source_id": None}

    if isinstance(v, list):
        return [_coerce_one(x) for x in v]
    return [_coerce_one(v)]