import json
from constants import FIELD_SCHEMA_PATH

def load_field_schema():
    with open(FIELD_SCHEMA_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_field_list():
    field_schema = load_field_schema()
    field_list = [key for key in field_schema.keys()]
    return field_list

def get_field_sap(fieldname:str):
    field_schema = load_field_schema()
    return field_schema.get(fieldname, None)["SAP"]

def get_field_dzone(fieldname:str):
    field_schema = load_field_schema()
    return field_schema.get(fieldname, None)["DZ"]

  for journal_no, voucher_data in enumerate(json_data):
        #대변 생성
        journal_entry = {}
        credit_row = []
        artist_name = voucher_data["프로젝트명"]
        credit_row.append({
            #전표 헤더
            "회사코드": "001",
            "회사명": COMPANY_NAME,
            "회계일자": voucher_data["날짜"], # 날짜 yyyy-mm-dd 후처리 필요
            "묶음번호": journal_no+1,
            "전표차수": 1,
            "전표유형": "일반",
            "작성부서": "회계팀",
            "작성자" : "VOUCHERAI",
            "상태" : "승인",
            "통화" : "KRW",
            "증빙유형" : voucher_data["증빙유형"],
            "생성일시" : now,
            "수정일시" : now,
            "승인일시" : now,
            "생성자" : "VOUCHERAI",
            "수정자" : "VOUCHERAI",
            "승인자" : confirmer_name,

            #전표 라인
            "차변/대변구분": "대변",
            "계정과목": AP_ACCOUNT_NAME,
            "계정코드": AP_ACCOUNT_CODE,
            "금액" : int(voucher_data["금액"]),
            "거래처코드" : voucher_data["거래처코드"],
            "거래처명": voucher_data["거래처"],
            "사업자등록번호": voucher_data["사업자등록번호"], # 거래처코드와 매핑 확장 
            "적요": make_text_for_journal(voucher_data["증빙유형"], voucher_data["날짜"], artist_name, voucher_data["거래처"], voucher_data["유형"]),
            "차변": 0,
            "대변": int(voucher_data["금액"]),
            "프로젝트코드" : artist_code,
            "프로젝트명" : artist_name,
            "사용부서명" : manager_name,
            "지출유형" : voucher_data["유형"]
        })
        # 차변 생성
        debit_rows = []
        serial_no = 2
        if voucher_data["계정과목"] in ACCOUNT_NAME_TO_SPLIT and artist_name in PROJECT_NAME_GROUP:
            members = GROUP_MEMBERS[artist_name]
            # 잔차보정 로직 필요
            amount_per_member = _round_krw(Decimal(voucher_data["금액"]) / len(members))
            for member in members:
                debit_rows.append({
                    #전표 헤더
                    "회사코드": "001",
                    "회사명": COMPANY_NAME,
                    "회계일자": voucher_data["날짜"],
                    "묶음번호": journal_no+1,
                    "전표차수": serial_no,
                    "전표유형": "일반",
                    "작성부서": "회계팀",
                    "작성자" : "VOUCHERAI",
                    "상태" : "승인",
                    "통화" : "KRW",
                    "증빙유형" : voucher_data["증빙유형"],
                    "생성일시" : now,
                    "수정일시" : now,
                    "승인일시" : now,
                    "생성자" : "VOUCHERAI",
                    "수정자" : "VOUCHERAI",
                    "승인자" : confirmer_name,

                    #전표 라인
                    "차변/대변구분": "차변",
                    "계정과목": voucher_data["계정과목"],
                    "계정코드": voucher_data["계정코드"],
                    "금액" : amount_per_member,
                    "거래처코드" : voucher_data["거래처코드"],
                    "거래처명": voucher_data["거래처"],
                    "사업자등록번호": voucher_data["사업자등록번호"], # 거래처코드와 매핑 확장 
                    "적요": make_text_for_journal(voucher_data["증빙유형"], voucher_data["날짜"], member, voucher_data["거래처"], voucher_data["유형"]),
                    "차변": int(amount_per_member),
                    "대변": 0,
                    "프로젝트코드" : f"{member}001", #추후 table로 가져오도록 구성 필요
                    "프로젝트명" : member,
                    "사용부서명" : manager_name,
                    "지출유형" : voucher_data["유형"]
                })
                serial_no += 1
        else:
            debit_rows.append({
                #전표 헤더
                "회사코드": "001",
                "회사명": COMPANY_NAME,
                "회계일자": voucher_data["날짜"],
                "묶음번호": journal_no+1,
                "전표차수": serial_no,
                "전표유형": "일반",
                "작성부서": "회계팀",
                "작성자" : "VOUCHERAI",
                "상태" : "승인",
                "통화" : "KRW",
                "증빙유형" : voucher_data["증빙유형"],
                "생성일시" : now,
                "수정일시" : now,
                "승인일시" : now,
                "생성자" : "VOUCHERAI",
                "수정자" : "VOUCHERAI",
                "승인자" : confirmer_name,

                #전표 라인
                "차변/대변구분": "차변",
                "계정과목": voucher_data["계정과목"],
                "계정코드": voucher_data["계정코드"],
                "금액" : voucher_data["금액"],
                "거래처코드" : voucher_data["거래처코드"],
                "거래처명": voucher_data["거래처"],
                "사업자등록번호": voucher_data["사업자등록번호"], # 거래처코드와 매핑 확장 
                "적요": make_text_for_journal(voucher_data["증빙유형"], voucher_data["날짜"], artist_name, voucher_data["거래처"], voucher_data["유형"]),
                "차변": voucher_data["금액"],
                "대변": 0,
                "프로젝트코드" : artist_code,
                "프로젝트명" : artist_name,
                "사용부서명" : manager_name,
                "지출유형" : voucher_data["유형"]
            })
