# mllm_reader.py
import base64, io, json, math, cv2, numpy as np
from typing import List, Dict, Any, Iterable, Tuple
from PIL import Image
import re, json
from datetime import datetime

# types.py
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict

from src.ant.load_llm import load_llm_model
from src.ant.llm_main import _validate_and_coerce
from loguru import logger
from src.entocr.models import ExtractionResult, TextBox
from src.entocr.extractor import ImageDataExtractor

def _encode_png_data_url(img_bgr: np.ndarray) -> str:
    """OpenAI/Anthropic 계열이 잘 받아주는 data URL로 인코드"""
    if img_bgr.ndim == 3:
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(img_rgb)
    else:
        pil = Image.fromarray(img_bgr)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

@dataclass
class TextBox:
    box_id: str
    polygon: List[Tuple[float, float]]  # [(x,y) abs pixels]
    norm_polygon: List[Tuple[float, float]]  # normalized [0,1]
    bbox_xyxy: Tuple[int,int,int,int]  # (x1,y1,x2,y2) ints
    page_index: int
    rotation: float  # degrees

@dataclass
class OCRResult:
    text_boxes: List[TextBox]
    processing_time: float
    image_size: Tuple[int, int]  # (W,H)
    @property
    def average_confidence(self) -> float:
        return 0.0  # detector용이면 0으로. (인식 conf는 MLLM 단계에서)


class MLLMProvider:
    """구체 구현에서 chat/images API를 래핑. 여기서는 인터페이스만."""
    def infer(self, messages: List[Dict[str,Any]]) -> str:
        raise NotImplementedError  # returns text response (JSON string expected)

def _encode_img(img: np.ndarray) -> str:
    pil = Image.fromarray(img[:, :, ::-1]) if img.ndim==3 else Image.fromarray(img)
    buf = io.BytesIO()
    pil.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()

def crop_with_padding(image: np.ndarray, x1,y1,x2,y2, pad_ratio: float=0.04) -> np.ndarray:
    h, w = image.shape[:2]
    pad_x = int((x2-x1) * pad_ratio)
    pad_y = int((y2-y1) * pad_ratio)
    xx1 = max(0, x1 - pad_x); yy1 = max(0, y1 - pad_y)
    xx2 = min(w, x2 + pad_x); yy2 = min(h, y2 + pad_y)
    return image[yy1:yy2, xx1:xx2].copy()


def build_multimodal_messages_for_boxes(
    page_img_bgr: np.ndarray,
    batch_items: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    batch_items: [{"box_id":str, "crop": np.ndarray, "coords":(x1,y1,x2,y2), "hint":str}]
    """
    system_msg = {
        "role": "system",
        "content": (
            """
            You are an OCR reader. Output ONLY JSON array of items.
            Each item: {"box_id": str, "text": str, "lang": str|null}
            No translation, preserve spaces and line breaks. No extra commentary.
            """
        ),
    }

    user_content = []
    # (선택) 페이지 컨텍스트 1장 추가 – 통화기호·표 머리글 등 문맥 인식에 도움
    user_content.append({"type": "text", "text": "Page context for layout reference."})
    user_content.append({
        "type": "image_url",
        "image_url": {"url": _encode_png_data_url(page_img_bgr)}
    })

    # 각 크롭 추가
    for it in batch_items:
        user_content.append({
            "type": "text",
            "text": f'box_id={it["box_id"]} hint={it.get("hint","plain")} coords={it.get("coords")}'
        })
        user_content.append({
            "type": "image_url",
            "image_url": {"url": _encode_png_data_url(it["crop"])}
        })

    user_msg = {"role": "user", "content": user_content}
    return [system_msg, user_msg]


def call_llm_and_parse_newocr(model_name: str, messages: List[Dict[str, Any]]) -> Any:
    llm = load_llm_model(model_name)           # 네가 갖고있는 함수
    resp = llm.invoke(messages)                # LangChain ChatOpenAI 호환
    raw = resp.content if hasattr(resp, "content") else str(resp)
    raw = raw.strip()

    # ① 배열형 응답도 허용
    if not (raw.startswith("{") or raw.startswith("[")):
        m = re.search(r"(\{.*\}|\[.*\])", raw, flags=re.DOTALL)
        if m:
            raw = m.group(0).strip()

    # ② JSON 로딩
    try:
        data = json.loads(raw)
    except Exception:
        # 키 따옴표 보정은 object에만 유효. 배열이면 스킵.
        if raw.startswith("{"):
            raw = re.sub(r"(\w+):", r'"\1":', raw)
        data = json.loads(raw)
               
    return data


def strict_json_loads(s: str) -> List[Dict[str,Any]]:
    # 견고한 파서: 선행/후행 텍스트 제거, code fence 제거 등
    s = s.strip()
    s = s[s.find('['): s.rfind(']')+1] if '[' in s and ']' in s else s
    return json.loads(s)

def _read_image_bgr(path: str) -> np.ndarray:
    img = cv2.imdecode(np.fromfile(path, dtype=np.uint8), cv2.IMREAD_COLOR)  # 윈도 경로 유니코드 대응
    if img is None:
        raise FileNotFoundError(path)
    return img

def recognize_with_mllm(
    extractor: ImageDataExtractor,
    image_path: str,
    ocr_result,               # OCRResult
    model_name: str = "gpt4o_latest",
    batch_size: int = 12,
) -> Dict[str, Any]:
    page = _read_image_bgr(image_path)

    # ocr_Result의 textbox를 업데이트 할거야.
    # 1) 박스 → 아이템화
    items = []
    box_number = 1
    for b in ocr_result.text_boxes:
        # 네 구조에 맞게 매핑 (예시: b.bbox_xyxy = (x1,y1,x2,y2))
        x1,y1,x2,y2 = b.bbox
        crop = crop_with_padding(page, x1,y1,x2,y2, pad_ratio=0.04)
        w, h = (x2-x1), (y2-y1)
        hint = "plain"
        if w > 140 and h < 60: hint = "line_or_amount"
        if h > w*1.6:          hint = "paragraph_or_address"
        box_id = f"box_{box_number:04d}"
        items.append({"box_id": box_id, "coords": (x1,y1,x2,y2), "crop": crop, "hint": hint})
        box_number += 1
    
    logger.info(f"크롭 작업 완료. 박스 개수: {len(items)}")
    
    # 2) 배치 호출
    rec_map: Dict[str, Any] = {}
    for i in range(0, len(items), batch_size):
        chunk = items[i:i+batch_size]
        messages = build_multimodal_messages_for_boxes(page, chunk)
        try:
            arr = call_llm_and_parse_newocr(model_name, messages)  # <= 네 함수 그대로 사용
            # 기대형: arr is list[dict]
            for obj in arr:
                rec_map[obj["box_id"]] = obj
            logger.info(f"MLLM 호출 성공. {i}번째 박스 처리 완료")
        except Exception:
            # 실패 시 단건 재시도(간단)
            for it in chunk:
                m1 = build_multimodal_messages_for_boxes(page, [it])
                arr = call_llm_and_parse_newocr(model_name, m1)
                rec_map[arr[0]["box_id"]] = arr[0]

    logger.info(f"MLLM 호출 완료. 박스 개수: {len(rec_map)}")

    # 3) detector 결과와 merge
    # 그럼 merge를 할때 ocr_result를 업데이트 해야하는거지
    # 이상한걸 뱉으면 안되지 않을까?

    merged = []
    confs = []
    box_number = 1

    for b in ocr_result.text_boxes:
        box_id = f"box_{box_number:04d}"
        r = rec_map.get(box_id, {"text":"", "lang":None, "conf":0.0, "normalized":None})
        b.text = r["text"]
        # confs.append(float(r.get("conf", 0.0)))
        # merged.append({
        #     "box_id": box_id,
        #     "bbox": b.bbox,
        #     "polygon": getattr(b, "polygon", None),
        #     "text": r.get("text",""),
        #     "lang": r.get("lang"),
        #     "conf": float(r.get("conf", 0.0)),
        #     "normalized": r.get("normalized"),
        # })
        box_number +=1 

    # page_conf = float(sum(confs)/len(confs)) if confs else 0.0
    # return {"image_size": ocr_result.image_size, "items": merged, "page_conf_avg": page_conf}
    logger.info(f"MLLM 호출 완료. 박스 개수: {len(rec_map)}")

    if not ocr_result.text_boxes:
        logger.warning(f"No text detected in image: {image_path}")
        return ExtractionResult(
            source_image=str(image_path),
            ocr_result=ocr_result,
            structured_data={},
            extraction_metadata={
                'extraction_time': datetime.now().isoformat(),
                'processing_successful': False,
                'error': 'No text detected'
            }
        )
    
    # Extract structured data
    structured_data = {
        'key_value_pairs': extractor._extract_key_value_pairs(ocr_result.text_boxes),
        'tables': extractor._extract_tables(ocr_result.text_boxes),
        'numbers_and_amounts': extractor._extract_numbers_and_amounts(ocr_result.text_boxes),
        'dates': extractor._extract_dates(ocr_result.text_boxes),
        'raw_text_lines': [box.text for box in ocr_result.text_boxes],
        'layout_analysis': extractor._analyze_layout(ocr_result.text_boxes)
    }

    # Create extraction metadata
    extraction_metadata = {
        'extraction_time': datetime.now().isoformat(),
        'processing_successful': True,
        'text_boxes_count': len(ocr_result.text_boxes),
        'total_characters': sum(len(box.text) for box in ocr_result.text_boxes),
        'avg_confidence': ocr_result.average_confidence,
        'processing_time': ocr_result.processing_time,
        'image_size': ocr_result.image_size
    }
    
    result = ExtractionResult(
        source_image=str(image_path),
        ocr_result=ocr_result,
        structured_data=structured_data,
        extraction_metadata=extraction_metadata
    )

    # Convert to JSON
    json_data = result.to_json_dict()
    json_string = json.dumps(
        json_data,
        indent=4,
        ensure_ascii=False
    )
    
    # Save to file if output path provided
    with open("test/1. OCR/OUTPUT/NEWOCRTEST.json", 'w', encoding='utf-8') as f:
        f.write(json_string)
        
    logger.info(f"JSON data saved to: test/1. OCR/OUTPUT/NEWOCRTEST.json")
        
    logger.info(f"Data extraction completed successfully for: {image_path}")
    return result

def run_pipeline(image_path: str, model_name: str = "gpt4o_latest_mini") -> Dict[str, Any]:
    from src.entocr.extractor import ImageDataExtractor
    extractor = ImageDataExtractor()
    ocr_result = extractor.ocr_service.extract_text(image_path)          # 네가 이미 갖고있는 함수
    rec = recognize_with_mllm(extractor, image_path, ocr_result, model_name=model_name)
    return rec

if __name__ == "__main__":
    rec = run_pipeline("test/1. OCR/INPUT/HUNTRIX.png")
    print(rec)