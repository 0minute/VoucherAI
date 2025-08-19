import pandas as pd

def get_json_wt_one_value_from_extract_invoice_fields(extract_invoice_fields_result: dict):
    """
    extract_invoice_fields의 결과 딕셔너리를 테이블(한개의 value를 가진 딕셔너리)로 변환합니다.
    #todo value가 리스트인 경우 사용자가 선택할 수 있도록 함
    #현재방식: 첫번째 값을 사용
    
    input : {key: [value1, value2, ...], key2: [value1, value2, ...], ...}
    output : {key: value, key2: value, ...}
    
    예시구조 : 
    {'날짜': ['20-03-31'], '거래처': ['주식회사 버킷플레이스'], '사업자등록번호': ['119-86-91245'], '대표자': ['이승재'], '주소': ['서울특별시 서초구 서초대로74길 4, 25,27층(서초동, 삼성생명서초타워)'], '금액': ['26700'], '유형': ['판매대행수수료'], '계정과목': '지급수수료'}
    
    """

    if not isinstance(extract_invoice_fields_result, dict):
        raise TypeError("extract_invoice_fields_result must be a dict")

    result = {}
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
            else:
                selected = value

        result[key] = selected

    return result
def create_dataframe_from_json(json_data: dict):
    df = pd.DataFrame(json_data)
    return df

def save_dataframe_to_excel(df: pd.DataFrame, file_path: str):
    df.to_excel(file_path, index=False)

def save_dataframe_to_csv(df: pd.DataFrame, file_path: str):
    df.to_csv(file_path, index=False)

def save_dataframe_to_json(df: pd.DataFrame, file_path: str):
    df.to_json(file_path, orient='records', lines=True)
