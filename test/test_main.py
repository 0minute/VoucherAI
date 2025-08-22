from test.constants import (TEST_DIR, 
                            OCR_DIR, OCR_INPUT_DIR, TEST_IMAGE, TEST_OCR_OUTPUT_PATH, 
                            LLM_DIR, LLM_INPUT_DIR, LLM_OUTPUT_DIR, 
                            TEST_LLM_INPUT_PATH, TEST_LLM_DATA_PATH,
                            TEST_LLM_CANDIDATES_PATH, TEST_LLM_SELECTIONS_PATH,
                            TEST_VISUALIZATION_DIR, TEST_VISUALIZATION_OUTPUT_PATH, TEST_VISUALIZATION_OUTPUT_DIR,
                            TEST_VISUALIZATION_DATA_PATH, TEST_VISUALIZATION_CANDIDATES_PATH, TEST_VISUALIZATION_SELECTIONS_PATH, TEST_VISUALIZATION_OCR_PATH,
                            TEST_JOURANL_ENTRY_DIR, TEST_JOURANL_ENTRY_OUTPUT_DIR, TEST_JOURANL_ENTRY_INPUT_PATH, TEST_JOURANL_ENTRY_OUTPUT_PATH, TEST_JOURANL_ENTRY_OUTPUT_PATH_EXCEL)
from src.entocr.ocr_main import ocr_image_and_save_json_by_extension
from src.ant.llm_main import extract_with_locations
from src.ant.visualization import draw_overlays, export_thumbnails
from src.entjournal.journal_main import make_journal_entry, get_json_wt_one_value_from_extract_invoice_fields, drop_source_id_from_json, make_journal_entry_to_record_list   
import json
import os

def test_ocr_image():
    """
    OCR 이미지 추출 테스트

    output > "source_image", "success", "ocr_summary", "text_boxes"가 key로 있음.
    "source_image"는 원본 이미지 경로
    "success"는 성공 여부
    "ocr_summary"는 OCR 결과 요약
    "text_boxes"는 OCR 결과 텍스트 박스

    실제로 사용되는 정보는 source_image, text_boxes 임.

    text_boxes의 text > 추출된 텍스트 값
    test_boxes의 coordinates > 추출된 텍스트 박스의 좌표
    text_boxes의 bbox > 추출된 텍스트 박스의 바운딩 박스 좌표 (파싱 위치 표시 시에 사용함)


    """
    output_path,json_result = ocr_image_and_save_json_by_extension(TEST_IMAGE) # 추후 BYTEIO 형식으로 변환 필요
    json.dump(json.loads(json_result), open(TEST_OCR_OUTPUT_PATH, "w", encoding="utf-8"), indent=4,  ensure_ascii=False)
    assert json_result is not None
    assert os.path.exists(TEST_OCR_OUTPUT_PATH)

def test_llm_parse():
    """
    llm 정보 파싱 테스트

    data > 파싱 결과 ["날짜", "거래처", "사업자등록번호", "대표자", "주소", "금액", "유형", "증빙유형", "계정과목"] (RESULT_FIELDS)
    candidates > 후보 레지스트리(텍스트). 텍스트/bbox(좌표박스),tag(로직에 따른 대략적인 tag 추출)로 구성(_tag_for_text 함수)
    selections > candidates 중 llm이 채택한 내역(field, value, source_id, bbox) *source_id 기준으로 시각화와 연결
    """
    ocr_dict = json.load(open(TEST_LLM_INPUT_PATH, "r", encoding="utf-8"))
    data, candidates, selections = extract_with_locations(ocr_dict)
    json.dump(data, open(TEST_LLM_DATA_PATH, "w", encoding="utf-8"), indent=4,  ensure_ascii=False)
    json.dump(candidates, open(TEST_LLM_CANDIDATES_PATH, "w", encoding="utf-8"), indent=4,  ensure_ascii=False)
    json.dump(selections, open(TEST_LLM_SELECTIONS_PATH, "w", encoding="utf-8"), indent=4,  ensure_ascii=False)
    assert data is not None
    assert os.path.exists(TEST_LLM_DATA_PATH)

def test_visualization():
    """
    시각화 테스트
    """
    ocr_json = json.load(open(TEST_VISUALIZATION_OCR_PATH, "r", encoding="utf-8"))
    img_path = ocr_json.get("source_image")  # 원본 이미지 경로가 OCR JSON에 있어야 함
    selections = json.load(open(TEST_VISUALIZATION_SELECTIONS_PATH, "r", encoding="utf-8"))
    if img_path and os.path.exists(img_path):
        filename = os.path.basename(img_path)
        filename_without_extension = os.path.splitext(filename)[0]
        overlay_path = os.path.join(TEST_VISUALIZATION_OUTPUT_DIR, f"{filename_without_extension}_overlay.png")
        thumbnail_path = os.path.join(TEST_VISUALIZATION_OUTPUT_DIR, f"{filename_without_extension}_thumbnails")
        draw_overlays(img_path, selections, overlay_path)
        export_thumbnails(img_path, selections, thumbnail_path, margin=0.06)
    assert os.path.exists(overlay_path)
    assert os.path.exists(thumbnail_path)

def test_create_journal_entry():
    import pandas as pd
    data_dict = json.load(open(TEST_JOURANL_ENTRY_INPUT_PATH, "r", encoding="utf-8"))
    data_dict = get_json_wt_one_value_from_extract_invoice_fields(data_dict)
    data_dict = [data_dict]
    data_dict = drop_source_id_from_json(data_dict)
    result_dict = make_journal_entry(data_dict)
    record_list = make_journal_entry_to_record_list(result_dict, TEST_JOURANL_ENTRY_INPUT_PATH)
    pd.DataFrame(record_list).to_excel(TEST_JOURANL_ENTRY_OUTPUT_PATH_EXCEL, index=False)
    json.dump(result_dict, open(TEST_JOURANL_ENTRY_OUTPUT_PATH, "w", encoding="utf-8"), indent=4,  ensure_ascii=False)
    assert result_dict is not None
    assert os.path.exists(TEST_JOURANL_ENTRY_OUTPUT_PATH)
    assert os.path.exists(TEST_JOURANL_ENTRY_OUTPUT_PATH_EXCEL)


if __name__ == "__main__":
    # test_ocr_image()
    # test_llm_parse()
    # test_visualization()
    test_create_journal_entry()


