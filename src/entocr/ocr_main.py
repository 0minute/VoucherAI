"""
OCR을 수행하는 Main 파일입니다.

PDF/JPG/PNG 파일을 입력하면, 결과 JSON을 반환합니다.
"""
import sys
import os
import tempfile
from pathlib import Path
from typing import List, Union

# # Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from src.entocr import ImageDataExtractor
from config.settings import settings
from loguru import logger
from src.utils.constants import EXTRACTED_JSON_DIR

# 이미지 파일을 추출합니다.
def ocr_image_and_save_json(image_path: str, output_path: str) -> None:
    from entocr import ImageDataExtractor
    extractor = ImageDataExtractor()
    json_result = extractor.extract_to_json(image_path, output_path)
    return json_result

# 확장자 검사 후 임시 폴더에 변환을 수행한 뒤에, 이미지 파일을 추출합니다.
def ocr_image_and_save_json_by_extension(image_path: str) -> str:
    """
    파일 확장자에 따라 변환 후 OCR을 수행합니다.
    
    Args:
        image_path (str): 입력 파일 경로. png/jpg/jpeg/pdf 파일 지원(pdf는 현재 오류 발생중)
        output_path (str): 출력 JSON 파일 경로
        
    Returns:
        str: 생성된 JSON 문자열
    """
    file_path = Path(image_path)
    extension = file_path.suffix.lower()

    output_path = os.path.join(EXTRACTED_JSON_DIR, f"{file_path.stem}.json")
    
    # 임시 디렉토리 생성
    with tempfile.TemporaryDirectory(prefix="entocr_temp_") as temp_dir:
        temp_path = Path(temp_dir)
        converted_files = []
        
        logger.info(f"Processing file: {image_path} (extension: {extension})")
        logger.info(f"Using temporary directory: {temp_dir}")
        
        # 확장자 변환 수행
        try:
            if extension == ".pdf":
                from src.entocr import convert_pdf_to_png
                logger.info("Converting PDF to PNG images...")
                converted_files = convert_pdf_to_png(
                    image_path, 
                    temp_path, 
                    dpi=300
                )
                logger.info(f"Converted {len(converted_files)} pages")
                
            elif extension in [".jpg", ".jpeg"]:
                from src.entocr import convert_jpg_to_png
                logger.info("Converting JPG/JPEG to PNG...")
                converted_file = convert_jpg_to_png(image_path, str(temp_path))
                converted_files = [Path(converted_file)]
                logger.info(f"Converted to: {converted_file}")
                
            elif extension == ".png":
                # PNG 파일은 변환 없이 그대로 사용
                converted_files = [file_path]
                logger.info("PNG file detected, using original file")
                
            else:
                raise ValueError(f"Unsupported file extension: {extension}")
            
            # OCR 처리
            extractor = ImageDataExtractor()
            
            if len(converted_files) == 1:
                # 단일 이미지 처리
                json_result = extractor.extract_to_json(str(converted_files[0]), output_path)
                logger.info(f"Single image processed successfully: {output_path}")
                
            else:
                # 여러 이미지 처리 (PDF의 경우)
                logger.info(f"Processing {len(converted_files)} images...")
                all_results = []
                
                for i, img_path in enumerate(converted_files, 1):
                    logger.info(f"Processing page {i}/{len(converted_files)}: {img_path.name}")
                    page_result = extractor.extract_from_image(img_path)
                    
                    # 페이지 정보 추가
                    page_data = {
                        "page_number": i,
                        "image_file": img_path.name,
                        "extraction_result": page_result.model_dump() if hasattr(page_result, 'model_dump') else page_result.__dict__
                    }
                    all_results.append(page_data)
                
                # 통합 결과 생성
                combined_result = {
                    "source_file": str(file_path),
                    "total_pages": len(converted_files),
                    "processed_at": extractor._get_timestamp(),
                    "pages": all_results,
                    "summary": {
                        "total_text_boxes": sum(
                            len(page["extraction_result"].get("text_boxes", [])) 
                            for page in all_results
                        ),
                        "successful_pages": len(all_results),
                        "average_confidence": sum(
                            page["extraction_result"].get("ocr_summary", {}).get("average_confidence", 0)
                            for page in all_results
                        ) / len(all_results) if all_results else 0
                    }
                }
                
                # JSON 파일로 저장
                import json
                json_result = json.dumps(combined_result, ensure_ascii=False)
                
                output_file = Path(output_path)
                output_file.parent.mkdir(parents=True, exist_ok=True)
                output_file.write_text(json_result, encoding='utf-8')
                
                logger.info(f"Multi-page processing completed: {output_path}")
                
            return output_path,json_result
            
        except Exception as e:
            logger.error(f"Error processing file {image_path}: {e}")
            raise
        
        finally:
            # 임시 파일들은 with 블록이 끝나면 자동으로 정리됨
            logger.info("Temporary files cleaned up")






if __name__ == "__main__":
    # 로깅 설정
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # 테스트 케이스들
    test_cases = [
        # ("input/TI-1.png", "output/TI-1_main.json"),  # PNG 파일
        ("input/한의원.pdf", "output/한의원.json"),  # PDF 파일
    ]
    
    logger.info("=== Entocr Main Processing Test ===")
    
    for i, (input_file, output_file) in enumerate(test_cases, 1):
        if not Path(input_file).exists():
            logger.warning(f"Test {i}: Input file not found: {input_file}")
            continue
            
        try:
            logger.info(f"Test {i}: Processing {input_file} -> {output_file}")
            result, _ = ocr_image_and_save_json_by_extension(input_file)
            logger.info(f"Test {i}: ✅ Success! Output saved to {output_file}")
            
        except Exception as e:
            logger.error(f"Test {i}: ❌ Failed to process {input_file}: {e}")
    
    logger.info("=== Main Processing Test Complete ===")
    
    # 사용예시 (주석 처리)
    """
    # 단일 이미지 처리
    result = ocr_image_and_save_json("input/image.png", "output/result.json")
    
    # 확장자별 자동 변환 처리  
    result = ocr_image_and_save_json_by_extension("input/document.pdf", "output/result.json")
    """
