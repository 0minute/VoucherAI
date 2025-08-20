from typing import List, Dict, Any
from PIL import Image, ImageDraw
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

def draw_overlays(image_path: str, selections: List[Dict[str, Any]], output_path: str) -> None:
    """
    원본 이미지 위에 선택된 값의 bbox를 색상별로 표시하여 저장.
    - bbox는 0~1 상대좌표
    - bbox가 None인 항목은 스킵
    """
    img = Image.open(image_path).convert("RGB")
    W, H = img.size
    draw = ImageDraw.Draw(img)

    colors = {
        "날짜": (66,133,244),          # blue
        "거래처": (156,39,176),        # purple
        "금액": (255,152,0),           # orange
        "사업자등록번호": (76,175,80), # green
        "대표자": (244,67,54),        # red
        "주소": (0,150,136),          # teal
    }

    for s in selections:
        if not s.get("bbox"):
            continue
        l,t,r,b = s["bbox"]
        pad = 20  # 픽셀 단위 여백
        box = (
            max(0, int(l * W) - pad),             # left
            max(0, int(t * H) - pad),             # top
            min(W, int(r * W) + pad),             # right
            min(H, int(b * H) + pad),             # bottom
        )
        color = colors.get(s["field"], (255, 215, 0))
        draw.rectangle(box, outline=color, width=10)
        # 간단 라벨(상단에 텍스트)
        label = f'{s["field"]}: {s["value"][:20]}'
        tx, ty = box[0], max(0, box[1]-16)
        draw.rectangle([tx, ty, tx+len(label)*7, ty+14], fill=(0,0,0))
        draw.text((tx+2, ty+1), label, fill=color)

    img.save(output_path)

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