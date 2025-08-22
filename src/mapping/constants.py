# 아티스트 리스트 > 추후 json 형태로 관리 필요
# 아티스트 관리 화면을 구성해서 아티스트 현황을 관리할 수 있도록 해야함
# 관리 화면의 컬럼 구성은 관리부서/아티스트/구분(그룹/개인)
# 추후에는 동명이인 고려해서 코드로 관리 + 이름 매칭해야하지만 시연용에서는 이름을 KEY로 관리
"""

{
    "HUNTRIX":{
        "artist_category":"GROUP",
        "artist_name":"HUNTRIX",
        "artist_department":"HUNTRIX"
    },
    "루미":{
        "artist_category":"MEMBER",
        "artist_name":"루미",
        "artist_department":"HUNTRIX"
    },
    "미라":{
        "artist_category":"MEMBER",
        "artist_name":"미라",
        "artist_department":"HUNTRIX"
    },
    "조이":{
        "artist_category":"MEMBER",
        "artist_name":"조이",
        "artist_department":"HUNTRIX"
    }
}

"""
ARTIST_NAMES = ["루미","미라","조이"]
GROUP_NAMES = ["HUNTRIX"]
ALL_NAMES = ARTIST_NAMES + GROUP_NAMES


# 컬럼 매핑 규칙> 컬럼명/조건/아티스트로 관리. KEY는 컬럼명(컬럼별로 설정됨) > 조건 > VALUE로 아티스트
"""

{
    "거래처명":
        {"김복자": "HUNTRIX"}
    
}

"""

