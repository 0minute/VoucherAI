import json
import os
from pathlib import Path
from datetime import datetime
import unicodedata
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Optional
from src.api.constants import WORKSPACE_ROOT

def _atomic_write_json(path: Path, data: dict):
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(tmp, path)
    
def _now_iso() -> str:
    return datetime.utcnow().isoformat() + "Z"

def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))

def _slugify(text: str) -> str:
    # 간단 슬러그: 공백→-, 영숫자/한글/하이픈만 남김, 소문자
    t = unicodedata.normalize("NFKC", text).strip().lower()
    t = re.sub(r"\s+", "-", t)
    t = re.sub(r"[^0-9a-z가-힣\-]", "", t)
    return t[:64] or "proj-" + datetime.utcnow().strftime("%H%M%S")

def _ensure_iso_date(s: str) -> str:
    """
    'YYYY-MM-DD' 문자열을 보장. 파싱 불가 시 ValueError.
    """
    if not s:
        raise ValueError("date is required (YYYY-MM-DD)")
    try:
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            _ = date.fromisoformat(s)
            return s
        # 다른 포맷이 오면 최대한 보정(예: '2025/08/26')
        s2 = s.replace("/", "-").strip()
        _ = date.fromisoformat(s2)
        return s2
    except Exception:
        raise ValueError(f"invalid date: {s!r}")

def _to_decimal(v) -> Decimal:
    if v is None or v == "":
        return Decimal("0")
    try:
        return v if isinstance(v, Decimal) else Decimal(str(v))
    except InvalidOperation:
        raise ValueError(f"invalid amount: {v!r}")

# ===== 유틸: 파일시스템 경로를 /static URL로 변환 =====
def fs_to_static_url(fs_path: str) -> Optional[str]:
    """ data/workspaces/... 하위면 /static/... 로 바꿔서 브라우저가 접근 가능하게 """
    try:
        p = Path(fs_path).resolve()
        root = WORKSPACE_ROOT.resolve()
        rel = p.relative_to(root)  # ValueError 시 outside
        return f"/static/{rel.as_posix()}"
    except Exception:
        return None