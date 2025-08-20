import pandas as pd
import io, os
from openpyxl.utils import get_column_letter


def get_json_wt_one_value_from_extract_invoice_fields(extract_invoice_fields_results):
    """
    extract_invoice_fields의 결과 딕셔너리를 테이블(한개의 value를 가진 딕셔너리)로 변환합니다.
    #todo value가 리스트인 경우 사용자가 선택할 수 있도록 함
    #현재방식: 첫번째 값을 사용
    
    input : {key: [value1, value2, ...], key2: [value1, value2, ...], ...}
    output : {key: value, key2: value, ...}
    
    예시구조 : 
    {'날짜': ['20-03-31'], '거래처': ['주식회사 버킷플레이스'], '사업자등록번호': ['119-86-91245'], '대표자': ['이승재'], '주소': ['서울특별시 서초구 서초대로74길 4, 25,27층(서초동, 삼성생명서초타워)'], '금액': ['26700'], '유형': ['판매대행수수료'], '계정과목': '지급수수료'}
    
    """

    if isinstance(extract_invoice_fields_results, dict):
        extract_invoice_fields_results = [extract_invoice_fields_results]
    elif isinstance(extract_invoice_fields_results, list):
        pass
    else:
        raise TypeError("extract_invoice_fields_result must be a dict or a list")

    result_l = []
    for extract_invoice_fields_result in extract_invoice_fields_results:
        result_d = {}
        for key, value in extract_invoice_fields_result.items():
            selected = None

            if isinstance(value, (list, tuple)):
                # 리스트인 경우 첫 번째 유효한 값 선택 (빈 문자열/None 제외)
                for candidate in value:
                    if candidate is None:
                        continue
                    if isinstance(candidate, str):
                        stripped = candidate.strip()
                        if stripped == "":
                            continue
                        selected = stripped
                        break
                    else:
                        selected = candidate
                        break
            else:
                # 단일 값인 경우 문자열은 trim
                if isinstance(value, str):
                    selected = value.strip()
                elif isinstance(value, list):
                    selected = value[0]
                else:
                    selected = value

            result_d[key] = selected
            result_l.append(result_d)
    if len(result_l) == 1:
        return result_l[0]
    else:
        return result_l

def create_dataframe_from_json(json_data: dict):
    # json 전처리
    df = pd.DataFrame(json_data)
    return df

def save_dataframe_to_excel(df: pd.DataFrame, file_path: str):
    df.to_excel(file_path, index=False)

def save_dataframe_to_csv(df: pd.DataFrame, file_path: str):
    df.to_csv(file_path, index=False)

def save_dataframe_to_json(df: pd.DataFrame, file_path: str):
    df.to_json(file_path, orient='records', lines=True)

def drop_source_id_from_json(json_results):
    for json_result in json_results:
        for key, value_d in json_result.items():
            if isinstance(value_d, dict):
                json_result[key] = value_d["value"]

    return json_results

def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "Results") -> bytes:
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)

        ws = writer.sheets[sheet_name]

        # 각 컬럼 너비 자동 맞춤(대략적인 문자폭 기준)
        for idx, col in enumerate(df.columns, start=1):  # 1-based
            # 헤더/데이터 길이 최대값 계산
            if df.empty:
                max_len = len(str(col))
            else:
                # NaN 포함 대비해 문자열화 후 길이 측정
                series_lens = df[col].astype(str).map(len)
                max_len = max(series_lens.max(), len(str(col)))

            # 엑셀 열문자 (A, B, ...)
            col_letter = get_column_letter(idx)
            # 가독성 위한 여백 + 상한
            width = min(max_len + 2, 60)
            ws.column_dimensions[col_letter].width = width

    buffer.seek(0)
    return buffer.getvalue()

def to_csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    df.to_csv(buffer, index=False)
    buffer.seek(0)
    return buffer.getvalue()

def get_result_jsons(session_state_results:dict):
    """
    streamlit의 session_state["results"]를 입력으로 받아서 각 이미지별 처리된 결과 json을 추출합니다.
    """
    result_jsons = []
    for image_path, results in session_state_results.items():
        result_json = results["data"]
        result_json["파일명"] = os.path.basename(os.path.basename(image_path))
        result_jsons.append(result_json)
    return result_jsons