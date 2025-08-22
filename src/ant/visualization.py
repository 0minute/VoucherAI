from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw, ImageFont
import os

# ============================================================
# 5) 시각화용 selections 구성 + 오버레이/썸네일 유틸
# ============================================================

def build_selections_for_viz(data: Dict[str, Any], candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    LLM 결과(value/source_id)와 candidates를 매칭하여
    시각화에 필요한 (field, value, source_id, bbox) 리스트를 만든다.
    - source_id가 None이거나 후보에 없으면 bbox=None → 오버레이 생략
    """
    cmap = {c["id"]: c for c in candidates}
    selections: List[Dict[str, Any]] = []
    def _add(field: str, item: Dict[str, Any]):
        sid = item.get("source_id")
        bbox = cmap[sid]["bbox"] if sid and sid in cmap else None
        selections.append({
            "field": field,
            "value": item.get("value", ""),
            "source_id": sid,
            "bbox": bbox,
        })

    for it in data.get("날짜", []): _add("날짜", it)
    for it in data.get("거래처", []): _add("거래처", it)
    for it in data.get("금액", []): _add("금액", it)
    for it in data.get("사업자등록번호", []): _add("사업자등록번호", it)
    for it in data.get("대표자", []): _add("대표자", it)
    for it in data.get("주소", []): _add("주소", it)
    # 유형은 텍스트만 있으므로 시각화 제외(원하면 회사명 라인 등과 연동 가능)
    return selections

# OS별로 흔한 한글 폰트 후보
FONT_PATH  = os.path.join("data","fonts","malgun.ttf")

def _load_korean_font(size: int = 18) -> Optional[ImageFont.FreeTypeFont]:
    """한글 지원 TTF/TTC/OTF 폰트를 탐색하여 로드."""
    if os.path.exists(FONT_PATH):
        try:
            return ImageFont.truetype(FONT_PATH, size=size)
        except Exception:
            pass
    return None  # 최후엔 PIL 기본폰트로 폴백(한글은 깨짐)

def _measure(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont):
    """텍스트 렌더링 바운딩 박스(w, h) 측정 (Pillow>=8: textbbox 사용)."""
    try:
        l, t, r, b = draw.textbbox((0, 0), text, font=font, stroke_width=0)
        return (r - l, b - t)
    except Exception:
        # 구버전 호환
        return draw.textsize(text, font=font)

def draw_overlays(image_path: str, selections: List[Dict[str, Any]], output_path: str) -> None:
    """
    원본 이미지 위에 선택된 값의 bbox를 색상별로 표시하여 저장.
    - bbox는 0~1 상대좌표
    - bbox가 None인 항목은 스킵
    - 한글 라벨이 깨지지 않도록 한글 폰트 지정
    - 라벨 배경 박스는 실제 텍스트 폭 기반으로 계산
    """
    img = Image.open(image_path).convert("RGB")
    W, H = img.size

    # 반투명 라벨을 위해 별도 레이어 사용
    overlay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    draw_img = ImageDraw.Draw(img)
    draw_ovl = ImageDraw.Draw(overlay)

    # 폰트 로드
    font = _load_korean_font(size=max(14, int(min(W, H) * 0.02)))  # 이미지 크기에 비례
    if font is None:
        # 한글 깨짐이 계속되면 프로젝트 내 ./fonts 에 NanumGothic.ttf 등을 넣어주세요.
        font = ImageFont.load_default()

    colors = {
        "날짜": (66, 133, 244),           # blue
        "거래처": (156, 39, 176),         # purple
        "금액": (255, 152, 0),            # orange
        "사업자등록번호": (76, 175, 80),  # green
        "대표자": (244, 67, 54),          # red
        "주소": (0, 150, 136),            # teal
    }

    for s in selections:
        if not s.get("bbox"):
            continue

        l, t, r, b = s["bbox"]
        pad = 20  # 픽셀 단위 여백
        box = (
            max(0, int(l * W) - pad),             # left
            max(0, int(t * H) - pad),             # top
            min(W, int(r * W) + pad),             # right
            min(H, int(b * H) + pad),             # bottom
        )

        color = colors.get(s.get("field"), (255, 215, 0))
        # 바운딩 박스
        draw_img.rectangle(box, outline=color, width= max(2, int(min(W,H)*0.004)))

        # 라벨 만들기 (필드: 값 일부)
        raw_value = str(s.get("value", ""))
        field = str(s.get("field", ""))
        label_txt = f"{field}: {raw_value}"

        # 라벨이 너무 길면 bbox 너비의 0.9배 안으로 줄이기
        max_label_width = int((box[2] - box[0]) * 0.9)
        if max_label_width <= 0:
            max_label_width = int(W * 0.6)

        # 폭에 맞게 말줄임(...) 적용
        def ellipsize(text: str) -> str:
            w, _ = _measure(draw_ovl, text, font)
            if w <= max_label_width:
                return text
            # 이진 탐색/선형 축소
            base = text
            ell = "…"
            lo, hi = 0, len(base)
            best = ell
            while lo <= hi:
                mid = (lo + hi) // 2
                cand = base[:mid] + ell
                w, _ = _measure(draw_ovl, cand, font)
                if w <= max_label_width:
                    best = cand
                    lo = mid + 1
                else:
                    hi = mid - 1
            return best

        label_txt = ellipsize(label_txt)

        # 라벨 위치(박스 상단 바깥쪽, 화면을 벗어나면 안쪽)
        tx = box[0]
        ty = max(0, box[1] - int(font.size * 1.8))

        # 텍스트 크기 및 배경 계산
        tw, th = _measure(draw_ovl, label_txt, font)
        pad_x, pad_y = int(font.size * 0.4), int(font.size * 0.3)
        bg_rect = [tx - pad_x, ty - pad_y, tx + tw + pad_x, ty + th + pad_y]

        # 배경 반투명(검정), 외곽선 약간
        draw_ovl.rectangle(bg_rect, fill=(0, 0, 0, 170), outline=(0, 0, 0, 220), width=1)

        # 텍스트(가독성을 위해 흰색 + 스트로크)
        draw_ovl.text(
            (tx, ty),
            label_txt,
            fill=(255, 255, 255, 255),
            font=font,
            stroke_width=max(1, int(font.size * 0.08)),
            stroke_fill=(0, 0, 0, 255),
        )

        # 라벨과 박스를 연결하는 가이드 라인(선택)
        # draw_ovl.line([(tx, ty + th), (box[0], box[1])], fill=color + (255,), width=1)

    # 오버레이 합성
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    img.save(output_path, quality=95)

def export_thumbnails(image_path: str, selections: List[Dict[str, Any]], out_dir: str, margin: float=0.06) -> List[str]:
    """
    선택된 bbox 영역을 크롭해서 썸네일로 저장.
    - margin: bbox 가장자리 여백 비율(권장 5~10%)
    - bbox가 None인 항목은 생략
    반환: 저장된 썸네일 경로 목록
    """
    os.makedirs(out_dir, exist_ok=True)
    img = Image.open(image_path).convert("RGB")
    W, H = img.size
    paths: List[str] = []

    for i, s in enumerate(selections):
        if not s.get("bbox"):
            continue
        l,t,r,b = s["bbox"]
        # 여백 적용
        ml = max(0.0, l - margin); mt = max(0.0, t - margin)
        mr = min(1.0, r + margin); mb = min(1.0, b + margin)
        box = (int(ml*W), int(mt*H), int(mr*W), int(mb*H))

        crop = img.crop(box)
        out_path = os.path.join(out_dir, f"{i:02d}_{s['field']}.png")
        crop.save(out_path)
        paths.append(out_path)

    return paths