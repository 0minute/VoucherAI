import os
from PIL import Image

def convert_jpg_to_png(jpg_path: str, output_dir: str) -> str:
    """
    JPG 파일을 PNG 파일로 변환하여 output_dir에 저장합니다.
    
    Args:
        jpg_path (str): 변환할 JPG 파일 경로
        output_dir (str): PNG 파일을 저장할 폴더 경로
    
    Returns:
        str: 생성된 PNG 파일 경로
    """
    # 폴더가 없으면 생성
    os.makedirs(output_dir, exist_ok=True)

    # 파일명과 확장자 분리
    file_name = os.path.splitext(os.path.basename(jpg_path))[0]
    png_path = os.path.join(output_dir, f"{file_name}.png")

    # JPG → PNG 변환
    with Image.open(jpg_path) as img:
        # RGB 변환 (투명 배경 불필요시)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGBA")
        else:
            img = img.convert("RGB")
        img.save(png_path, "PNG")

    return png_path

# 사용 예시
if __name__ == "__main__":
    jpg_file = r"input/R-1.jpg"        # 변환할 JPG 파일 경로
    output_folder = r"output/"      # PNG 저장 폴더 경로
    result_path = convert_jpg_to_png(jpg_file, output_folder)
    print(f"변환 완료 → {result_path}")
