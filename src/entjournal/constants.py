
# 회사별로 달라져야함
# 별도 테이블로 설정할 수 있도록 하여야함.
AP_ACCOUNT_NAME = "미지급금"
AP_ACCOUNT_CODE = 25300
COMPANY_NAME = "K-POPDEMONHUNTERS"
PROJECT_NAME_GROUP = ["HUNTRIX"]
ACCOUNT_NAME_TO_SPLIT = ["연예보조_의상ㆍ스타일링", "연예보조_화장ㆍ메이크업", "연예보조_촬영ㆍ영상", "연예보조_기타"]
GROUP_MEMBERS = {"HUNTRIX":["루미","미라","조이"]}
# MANAGER_NAMES_AND_ARTIST = {"바비" : {"HUNTRIX":"GROUP","루미":"MEMBER","미라":"MEMBER","조이":"MEMBER"}}
ARTIST_NAMES = ["루미","미라","조이"]
GROUP_NAMES = ["HUNTRIX"]
ALL_NAMES = ARTIST_NAMES + GROUP_NAMES
    
COLUMN_RULES_PATH = "data/column_rules.json"
FIELD_SCHEMA_PATH = "data/field_schema.json"

# 원본 필드가 있고 > SAP/DZONE 확장 가능한 구조로 짜야함
SAP_COLUMN_RULES = {
    "MANDT": "Client", # 고객명
    "BUKRS": "회사코드", # 고객코드 < 필수키
    "BELNR": "전표번호", # < 필수키
    "GJAHR": "회계연도", # < 필수키
    "MONAT": "회계기간", # 월
    "BLART": "전표유형", #  SA=일반전표, KR=매입, DR=매출 > 추후 규칙에 따라 GPT가 맵핑하도록 매입은 관리하는 비용인경우(지급자동화 등) 소액은 SA
    "BUDAT": "전기일",  # TODAY
    "BLDAT": "증빙일", # 세금계산서 날짜
    "CPUDT": "전표입력일", # 전표입력일
    "CPUTM": "전표입력시간", # 전표입력시간
    "WAERS": "통화코드", # KRW
    "XBLNR": "참조번호", # 세금계산서 번호 
    "BKTXT": "헤더텍스트", #적요
    "USNAM": "입력자", # 로그인한 유저 ID < 여기까지 헤더(필수) 컬럼
    "BUZEI": "아이템번호", # 라인넘버
    "HKONT": "G/L 계정", 
    "SHKZG": "차/대변 Indicator",
    "WRBTR": "거래금액", # 양수 음수 구분 대변은 음수
    "DMBTR": "회사코드 통화 금액", # = 금액
    "PSWBT": "원화/기본통화 기준 금액", # = 금액
    "KOSTL": "코스트센터", # 사용부서 > 사용자 매핑 필요
    "AUFNR": "내부오더",  # 건설중인 자산 등 프로젝트 단위로 나가는 비용 관리
    "PRCTR": "손익센터", # 아티스트별
    "ZTERM": "지급조건", # 비우기
    "SGTXT": "개별 아이템 텍스트", # = 적요
    "LIFNR": "거래처 코드", # 매입거래처코드 > 거래처코드 쓰면 될듯
    "KUNNR": "거래처 코드", #매출거래처코드 
    "ZLIFN": "거래처명" # 매입거래처명 > 커스텀 필드(Z~) 
  }

DZONE_COLUMN_RULES = [
    "회사코드",
    "전표번호",
    "전표일자",
    "작성부서",
    "작성자",
    "적요",           # 헤더텍스트
    "회계연도",
    "회계기간",
    "전표유형",
    "승인상태",
    "자동기표여부",
    "입력일시", # 여기까지 헤더
    "전표번호",       # 헤더와 연결 키
    "라인번호",
    "계정코드",
    "차변/대변구분",
    "금액(원화)",
    "금액(외화)",
    "거래처코드",
    "거래처명",
    "적요",           # 라인텍스트
    "부서코드",
    "프로젝트코드",
    "관리항목1",
    "관리항목2",
    "세금코드",
    "부가세구분",
    "공급가액",
    "세액",
    "지급조건",
    "지급예정일", # 여기까지 세부
    "거래처코드", #여기부터 거래처
    "거래처명",
    "사업자등록번호",
    "대표자명",
    "업태",
    "종목",
    "주소",
    "연락처",
    "담당자명",
    "결제조건",
    "은행명",
    "계좌번호",
    "신용한도",
    "사용여부"
]


