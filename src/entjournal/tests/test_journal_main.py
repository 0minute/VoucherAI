from src.entjournal.journal_main import create_dataframe_from_json, to_excel_bytes, drop_source_id_from_json, get_result_jsons
from src.utils.constants import EXTRACTED_JSON_DIR 
import os
import json
from src.entjournal.journal_main import get_json_wt_one_value_from_extract_invoice_fields



def test_to_excel_bytes():
    json_data_r1 = os.path.join("output", "TI-2.json")
    with open(json_data_r1, "r", encoding="utf-8") as f:
        json_data_1 = json.load(f)
    json_data_1["파일명"] = "TI-2.png"
    json_data_ti1 = os.path.join("output", "TI-1.json")
    with open(json_data_ti1, "r", encoding="utf-8") as f:
        json_data_2 = json.load(f)
    json_data_2["파일명"] = "TI-1.png"
    json_results = [json_data_1, json_data_2]
    json_results = get_json_wt_one_value_from_extract_invoice_fields(json_results)
    json_results = drop_source_id_from_json(json_results)
    df = create_dataframe_from_json(json_results)
    excel_bytes = to_excel_bytes(df)
    assert excel_bytes is not None

def test_df_from_result_jsons():
    import pickle
    with open("results.pkl", "rb") as f:
        results = pickle.load(f)
    result_jsons = get_result_jsons(results)
    result_jsons = get_json_wt_one_value_from_extract_invoice_fields(result_jsons)
    result_jsons = drop_source_id_from_json(result_jsons)
    result_df = create_dataframe_from_json(result_jsons)
    print(result_df)


if __name__ == "__main__":
    test_df_from_result_jsons()
    print("All tests passed")