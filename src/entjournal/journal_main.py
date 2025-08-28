import pandas as pd
import io, os
from openpyxl.utils import get_column_letter
from src.entjournal.constants import (AP_ACCOUNT_NAME, 
                                      AP_ACCOUNT_CODE, 
                                      COMPANY_NAME, 
                                      PROJECT_NAME_GROUP, 
                                      ACCOUNT_NAME_TO_SPLIT, 
                                      GROUP_MEMBERS,
                                      PROJECT_NAME_TO_CODE)
import datetime
from decimal import Decimal, ROUND_HALF_UP
import json
from src.entjournal.constants import COLUMN_RULES_PATH
from src.entjournal.utils import load_field_schema
from loguru import logger

def get_json_wt_one_value_from_extract_invoice_fields(extract_invoice_fields_results):
    """
    [Note] 현재는 LLM이 한개의 결과를 반환하지만, 추후 후보를 반환한 후 사용자가 선택하는 기능으로의 확장을 고려하여 VALUE를 리스트 형태로 반환하고 있습니다.
    현재는 추천 기능이 없으므로, 해당 함수를 활용하여 후처리를 수행한 후 다음 단계로 넘어가도록 합니다.

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

def load_column_rules() -> dict:
    if os.path.exists(COLUMN_RULES_PATH):
        with open(COLUMN_RULES_PATH, "r", encoding="utf-8") as f:
            column_rules = json.load(f)
    else:
        column_rules = {}
    return column_rules

def map_artist_name_with_column_rules_to_json(json_data: list) -> list:
    # 리스트의 각 요소는 각 영수증에서 추출된 데이터임.
    column_rules = load_column_rules()
    if not column_rules:
        return json_data
    for voucher_data in json_data:
        voucher_data["프로젝트명"] = None
        # 영수증에서 추출된 각 정보(컬럼)별로 검사함.
        for voucher_header, voucher_value in voucher_data.items():
            column_rule = column_rules.get(voucher_header)
            if column_rule:
                artist_name = column_rule.get(voucher_value)
                # 컬럼 규칙에 해당되는 아티스트 명 존재 > 아티스트 명 변경
                voucher_data["프로젝트명"] = artist_name
                logger.info(f"규칙에 따른 아티스트명 맵핑 완료: {voucher_header}_{voucher_value} -> {artist_name}")
                # 규칙 발견시 해당 영수증에 대한 검사는 종료함
                break
        
    return json_data

def make_journal_entry(json_data: list, erp: str = 'dz') -> dict:
    """
    분개를 생성합니다.
    데이터는 모두 비용이므로, 상대계정은 동일한 금액의 미지급금입니다.
    특정 비용은 그룹 구성원별로 분할될 수 있는 것을 고려하여 코드를 구성해야 합니다.
    결과는 dict로 반환(해당 함수는 연산만 수행)

    input: list of dict
    [{
        "날짜": "2025-01-01",
        "거래처": "거래처명",
        "사업자등록번호": "1234567890",
        "대표자": "대표자명",
        "주소": "주소",
        "금액": 1000000,
        "계정과목": "지급수수료",
        "계정코드": "1111111111",
        "유형": "판매대행수수료"
    },...]

    output: list of dict
    1단계 깊이 리스트의 내용: 각 거래 건별로 별도의 딕셔너리를 구성합니다.
    2단계 깊이 딕셔너리의 내용: debit, credit을 key로 구성합니다. value는 리스트입니다.
    3단계 깊이 리스트의 내용: debit 리스트의 내용은 각 레코드입니다. 분할될 경우 2개+의 레코드가 포함됩니다. credit 리스트의 내용은 미지급금 레코드입니다.

    분개 컬럼 구성: SAP/더존 별로 달라집니다. 공통된 부분을 처리한 후, ERP에 따라 분기를 나눕니다.

    params
    erp: str 
        SAP: erp = 'sap'
        DZ: erp = 'dz'        
    """

    # 추출 데이터 별로 순환
    # 컬럼 규칙 적용
    json_data = map_artist_name_with_column_rules_to_json(json_data)
    # Dummy
    # ------------------------------------------------------------
    biz_reg_no_to_Vender_Code = {"11111":"삼일회계법인"}
    artist_code = "HUNTRIX001"
    manager_name = "바비"
    confirmer_name = "Confirm"
    # ------------------------------------------------------------
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    journal_entries = []
    line_number = 1
    for journal_no, voucher_data in enumerate(json_data):
        file_id = voucher_data["file_id"]
        #대변 생성
        journal_entry = []
        credit_row = []
        artist_name = voucher_data["프로젝트명"]
        credit_row.append(make_journal_line(voucher_data, journal_no, 1, now, artist_code, artist_name, voucher_data["금액"], file_id, "credit"))
        
        line_number += 1
        # 차변 생성
        debit_rows = []
        if voucher_data["계정과목"] in ACCOUNT_NAME_TO_SPLIT and artist_name in PROJECT_NAME_GROUP:
            members = GROUP_MEMBERS[artist_name]
            
            # 잔차보정 로직 필요
            amount_per_member = _round_krw(Decimal(voucher_data["금액"]) / len(members))
            for member in members:
                member_code = PROJECT_NAME_TO_CODE[member]
                debit_rows.append(make_journal_line(voucher_data, journal_no, line_number, now, member_code, member,amount_per_member, file_id, "debit"))
                line_number += 1
        else:
            debit_rows.append(make_journal_line(voucher_data, journal_no, line_number, now, artist_code, artist_name, voucher_data["금액"], file_id, "debit"))
            line_number += 1
        journal_entry.extend(credit_row)
        journal_entry.extend(debit_rows)
        journal_entries.extend(journal_entry)

    return journal_entries

def sap_view(journal_entries: list):
    field_schema = load_field_schema()
    sap_journal_entries = []
    for journal_entry in journal_entries:
        sap_journal_entry = {}
        for field, value in journal_entry.items():
            sap_field = field_schema.get(field,{}).get("SAP",{})
            if sap_field:
                sap_journal_entry[sap_field] = value
        sap_journal_entries.append(sap_journal_entry)
    return sap_journal_entries
    
def dzone_view(journal_entries: list):
    field_schema = load_field_schema()
    dzone_journal_entries = []
    for journal_entry in journal_entries:
        dzone_journal_entry = {}
        for field, value in journal_entry.items():
            dzone_field = field_schema.get(field,{}).get("DZ",{})
            if dzone_field:
                dzone_journal_entry[dzone_field] = value
        dzone_journal_entries.append(dzone_journal_entry)
    return dzone_journal_entries

def make_journal_line(voucher_data, journal_no, line_number, now, artist_code, artist_name, amount, file_id, dorc = "credit"):
    
    if dorc == "credit":
      result = {
          "회사코드": "001",
          "전표번호": journal_no,
          "전표일자": voucher_data["날짜"], #사용자 키인으로 변경
          "작성부서": "회계팀",
          "작성자" : "USER",
          "적요" : make_text_for_journal(voucher_data["증빙유형"], voucher_data["날짜"], artist_name, voucher_data["거래처"], voucher_data["유형"]),
          "회계연도": "2025", # voucher_data["날짜"].split("-")[0],
          "회계기간": "12", # voucher_data["날짜"].split("-")[1],
          "전표유형": "SA", #더존 > 일반
          "승인상태" : "미결",
          "자동기표여부" : "N",
          "입력일시" : now,
          "라인번호" : line_number, #UNIQUE ID로 수정
          "계정코드" : AP_ACCOUNT_CODE,
          "계정과목명" : AP_ACCOUNT_NAME,
          "차변/대변구분" : "대변",
          "금액(원화)" : amount,
          "금액(외화)" : amount,
          "차변" : 0,
          "대변" : amount,
          "거래처코드" : None, #voucher_data["거래처코드"],
          "거래처명" : voucher_data["거래처"],
          "부서코드" : "KDH001", # 추후 입력받아야함
          "프로젝트코드" : artist_code,
          "관리항목1" : None,
          "관리항목2" : None,
          "사업자등록번호" : None, #voucher_data["사업자등록번호"],
          "증빙일" : voucher_data["날짜"],
          "참조번호" : None, #voucher_data["참조번호"]
          "손익센터" : None,
          "개별아이템텍스트" : make_text_for_journal(voucher_data["증빙유형"], voucher_data["날짜"], artist_name, voucher_data["거래처"], voucher_data["유형"]),
          "file_id" : file_id
        
      }

    elif dorc == "debit":
      result = {
          "회사코드": "001",
          "전표번호": journal_no,
          "전표일자": voucher_data["날짜"], #사용자 키인으로 변경
          "작성부서": "회계팀",
          "작성자" : "USER",
          "적요" : make_text_for_journal(voucher_data["증빙유형"], voucher_data["날짜"], artist_name, voucher_data["거래처"], voucher_data["유형"]),
          "회계연도": "2025", # voucher_data["날짜"].split("-")[0],
          "회계기간": "12", # voucher_data["날짜"].split("-")[1],
          "전표유형": "SA", #더존 > 일반
          "승인상태" : "미결",
          "자동기표여부" : "N",
          "입력일시" : now,
          "라인번호" : line_number, #UNIQUE ID로 수정
          "계정코드" : voucher_data["계정코드"],
          "계정과목명" : voucher_data["계정과목"],
          "차변/대변구분" : "차변",
          "금액(원화)" : amount,
          "금액(외화)" : amount,
          "차변" : amount,
          "대변" : 0,
          "거래처코드" : None, #voucher_data["거래처코드"],
          "거래처명" : voucher_data["거래처"],
          "부서코드" : "KDH001", # 추후 입력받아야함
          "프로젝트코드" : artist_code,
          "관리항목1" : None,
          "관리항목2" : None,
          "사업자등록번호" : None, #voucher_data["사업자등록번호"],
          "증빙일" : voucher_data["날짜"],
          "참조번호" : None,#voucher_data["참조번호"],
          "손익센터" : None,
          "개별아이템텍스트" : make_text_for_journal(voucher_data["증빙유형"], voucher_data["날짜"], artist_name, voucher_data["거래처"], voucher_data["유형"]),
          "file_id" : file_id
      }
    return result
      
def _round_krw(x: Decimal) -> int:
    # 원화 정수 금액 반올림 (ROUND_HALF_UP)
    return int(x.quantize(Decimal('1'), rounding=ROUND_HALF_UP))

def make_journal_entry_to_record_list(journal_dict: dict, image_path: str= None) -> pd.DataFrame:
    rows = []
    for record_id, journal_entry_data in journal_dict.items():
        for debit_and_credit, entry_rows in journal_entry_data.items():
            for entry_row in entry_rows:
                rows.append({**entry_row, "file_id": os.path.basename(image_path) if image_path else None})
    return rows

# 적요는 자동생성이므로 핵심만 파악할 수 있도록 
# 예: 연월일_아티스트명_거래처명_유형

def make_text_for_journal(doc_type:str, date:str, artist_name:str, account_name:str, type:str):
    """
    inputs
        doc_type: 문서 유형
        date: 연월일(YYYY-MM-DD)
        artist_name: 아티스트명
        account_name: 거래처명
        type: 유형
    output:
        "세금계산서_20250822_HUNTRIX_김복자_연예보조_의상ㆍ스타일링"
    """
    # 식별에 실패한 경우를 위한 에러처리 추가필요
    return f"{doc_type}_{date.replace('-','')}_{artist_name}_{account_name}_{type}"

def edit_voucher_data_show(file_id:str):
    # 선택한 전표의 voucher_Data를 가져와야함
    #todo 지금은 스트림릿의 세션에서 file_id를 저장하고있어서 그걸 가져다 쓰고 있는데, 구조 고민하기
    #voucher_data 구조 바꿔야할 듯? 리스트 형태 버리기
    def _get_voucher_data_by_file_id(file_id):
        pass
    voucher_data = _get_voucher_data_by_file_id(file_id)

    return voucher_data

def edit_voucher_data_save(file_id:str, updated_voucher_data):
    # 지금 streamlit 기준으로는 session에 다시 저장한 후에 journal 생성하면 됨
    # 그래도 DB에서 기억을 하는게 맞을 것 같음.
    # 현재 voucher_data db를 가져오기
    def load_voucher_data_db():
        pass
    voucher_db = load_voucher_data_db
    # 프런트에서 준 내용으로 업데이트
    def update_voucher_data_db(file_id, updated_voucher_data):
        pass
    # 결과 저장
    updated_voucher_db = update_voucher_data_db(file_id, updated_voucher_data)
    def save_voucher_data_db(updated_voucher_db):
        pass
    # journal_entry 재생성
    def refresh_journal_entry():
        pass
    result = refresh_journal_entry()
    return result








if __name__ == "__main__":
    test_json =     [{'날짜': [{'value': '25/08/1120', 'source_id': None}], '거래처': [{'value': '...', 'source_id': None}], '금액': [{'value': '4000', 'source_id': 'p0_00004'}], '유형': ['식비'], '사업자등록번호': [{'value': '...', 'source_id': None}], '대표자': [{'value': '...', 'source_id': None}], '주소': [{'value': '...', 'source_id': None}], '계정과목': '복리후생비_식대', '계정코드': 51103}]

    # journal_entry = make_journal_entry(test_json, erp='dz')
    # print(journal_entry)


    journal_entry = get_json_wt_one_value_from_extract_invoice_fields(test_json)
    print(journal_entry)