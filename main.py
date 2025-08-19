from src.ant.llm_main import extract_invoice_fields
from src.entocr.ocr_main import ocr_image_and_save_json_by_extension
from src.entjournal.journal_main import get_json_wt_one_value_from_extract_invoice_fields, create_dataframe_from_json, save_dataframe_to_excel, save_dataframe_to_csv, save_dataframe_to_json
import zipfile
import os
import tempfile
import json
# 추가해야할것
# 유형에 따른 계정과목 자동 매핑 추가(추후 추천 ui도 구상 > 시연시에 뭐가 더 있어보일지?)
# 아티스트 분할 관련 고민하기(자동분할) > 1. 매니저별 담당자 정해진 경우/방문일정과 연동<현실적/샵 주소 정보와 연동<과거 히스토리 기반 추천
def run(input_data: str):
    json_path, result = ocr_image_and_save_json_by_extension(input_data)
    print(result)
    result = extract_invoice_fields(json_path)
    print(result)


def run_with_zip(zipfile_path: str):
    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(zipfile_path, 'r') as zip_ref:
            zip_ref.extractall(temp_dir)
        
        ocr_result_list = [ocr_image_and_save_json_by_extension(f"{temp_dir}/{file}") for file in os.listdir(temp_dir)]
    journal_data_list = [extract_invoice_fields(json.loads(ocr_result)) for source_path, ocr_result in ocr_result_list]
    journal_data_list_wt_one_value = [get_json_wt_one_value_from_extract_invoice_fields(journal_data) for journal_data in journal_data_list]
    return journal_data_list_wt_one_value

def save_excel(journal_data_list_wt_one_value: list):
    df = create_dataframe_from_json(journal_data_list_wt_one_value)
    save_dataframe_to_excel(df, "output/journal_data.xlsx")
    save_dataframe_to_csv(df, "output/journal_data.csv")
    save_dataframe_to_json(df, "output/journal_data.json")

    
if __name__ == "__main__":
    # import json
    # result = run("input/TI-2.pdf")
    # with open("output/TI-2.json", "w", encoding="utf-8") as f:
    #     json.dump(result, f, ensure_ascii=False)

    journal_data_list_wt_one_value = run_with_zip("input/input.zip")
    save_excel(journal_data_list_wt_one_value)






