import base64, mimetypes, os

def _image_path_to_data_url(path: str) -> str:
    """
    로컬 이미지 파일을 data URL(base64)로 인코딩.
    - OpenAI/멀티모달 API는 일반적으로 `image_url.url`에 http(s) 또는 data URL을 허용
    - 외부 URL이 없다면 data URL이 가장 간단한 방법
    """
    if not path or not os.path.exists(path):
        raise FileNotFoundError(f"이미지 파일을 찾을 수 없습니다: {path}")

    # 파일 확장자로 MIME 추정 (없으면 png로 fallback)
    mime, _ = mimetypes.guess_type(path)
    if not mime:
        mime = "image/png"

    with open(path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    return f"data:{mime};base64,{b64}"
