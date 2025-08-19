# Entocr - OCR Data Extraction to JSON

이미지에서 텍스트를 추출하고 구조화된 JSON 데이터로 변환하는 Python 프로젝트입니다. PaddleOCR을 사용하여 한국어를 포함한 다국어 텍스트 인식을 지원합니다.

## 주요 기능

- **다국어 OCR**: PaddleOCR 기반으로 한국어, 영어, 중국어, 일본어 등 80+ 언어 지원
- **PDF 지원**: PDF 문서를 이미지로 변환하여 OCR 처리 (PyMuPDF 또는 pdf2image 사용)
- **구조화된 데이터 추출**: 키-값 쌍, 표, 숫자, 날짜, 금액 등을 자동으로 추출
- **JSON 출력**: 추출된 데이터를 구조화된 JSON 형태로 저장
- **배치 처리**: 여러 이미지/PDF를 한 번에 처리 가능
- **자동 파일 감지**: 이미지와 PDF를 자동으로 구별하여 적절한 방법으로 처리
- **CLI 도구**: 명령행 인터페이스로 간편한 사용
- **확장 가능**: 커스텀 데이터 처리기 추가 가능

## 프로젝트 구조

```
Entocr/
├── src/entocr/              # 메인 소스 코드
│   ├── __init__.py
│   ├── models.py            # 데이터 모델 (Pydantic)
│   ├── ocr_service.py       # PaddleOCR 서비스
│   ├── extractor.py         # 메인 데이터 추출기
│   ├── cli.py               # CLI 인터페이스
│   └── __main__.py
├── config/                  # 설정 관리
│   ├── __init__.py
│   └── settings.py
├── tests/                   # 테스트 파일
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_models.py
│   └── test_extractor.py
├── input/                   # 입력 이미지 폴더
├── docs/                    # 문서
├── main.py                  # 메인 실행 파일
├── pyproject.toml           # 프로젝트 설정
├── requirements.txt         # 의존성 목록
├── requirements-dev.txt     # 개발 의존성
└── .env.example             # 환경 변수 예시
```

## 설치

### 1. 저장소 클론
```bash
git clone <repository-url>
cd Entocr
```

### 2. 가상환경 생성 (권장)
```bash
python -m venv venv

# Windows
venv\\Scripts\\activate

# Linux/Mac
source venv/bin/activate
```

### 3. 의존성 설치
```bash
# 기본 의존성
pip install -r requirements.txt

# 또는 개발 의존성 포함
pip install -r requirements-dev.txt
```

### 4. 환경 설정
```bash
# .env 파일 생성
cp .env.example .env

# 필요시 설정 값 수정
```

## 사용법

### 1. Python 코드에서 사용

```python
from entocr import ImageDataExtractor

# 추출기 초기화
extractor = ImageDataExtractor()

# 단일 이미지 처리
result = extractor.extract_from_image("input/document.jpg")
print(f"추출된 텍스트 박스 수: {len(result.ocr_result.text_boxes)}")

# JSON으로 저장
json_data = extractor.extract_to_json(
    "input/document.jpg", 
    "output/document_extracted.json"
)

# PDF 파일 처리
pdf_result = extractor.extract_from_pdf(
    "input/document.pdf",
    dpi=300,
    max_pages=3,
    keep_images=True
)

# PDF를 JSON으로 변환
pdf_json = extractor.extract_pdf_to_json(
    "input/document.pdf",
    "output/pdf_extracted.json",
    dpi=300,
    max_pages=5
)

# 자동 파일 감지 (이미지 또는 PDF)
auto_result = extractor.auto_extract(
    "input/unknown_file.pdf",  # 또는 .jpg, .png 등
    "output/auto_extracted.json"
)
```

### 2. 메인 스크립트 실행

```bash
# 예시 이미지 처리 (input/TI-1.png)
python main.py
```

### 3. PDF 변환 사용법

```python
from entocr.pdf_converter import PDFConverter, convert_pdf_to_png

# 간단한 PDF → PNG 변환
image_paths = convert_pdf_to_png(
    "input/document.pdf",
    output_dir="output/pages/",
    dpi=300
)

# 고급 PDF 변환 옵션
converter = PDFConverter(
    dpi=200,
    max_pages=3,
    output_format="PNG"
)

# PDF 정보 조회
pdf_info = converter.get_pdf_info("input/document.pdf")
print(f"총 페이지 수: {pdf_info['pages']}")

# 변환 및 정리
images = converter.convert_pdf_to_images("input/document.pdf")
# ... 이미지 처리 ...
converter.cleanup_temp_files(images)  # 임시 파일 정리
```

### 4. CLI 도구 사용

```bash
# 단일 이미지 처리
python -m entocr input/document.jpg

# 출력 파일 지정
python -m entocr input/document.jpg -o output/result.json

# 디렉토리 내 모든 이미지 처리
python -m entocr -d input/ -O output/

# 여러 이미지 처리
python -m entocr image1.jpg image2.png -O output/

# 로그 레벨 설정
python -m entocr input/document.jpg --log-level DEBUG

# 언어 설정
python -m entocr input/document.jpg --language korean

# GPU 비활성화
python -m entocr input/document.jpg --no-gpu

# PDF 파일 처리
python -m entocr input/document.pdf

# PDF 처리 옵션 설정
python -m entocr input/document.pdf --pdf-dpi 300 --pdf-max-pages 5 --keep-images

# 자동 파일 감지 (이미지와 PDF 자동 구별)
python -m entocr input/mixed_files/* -O output/
```

## 설정

환경 변수 또는 `.env` 파일을 통해 설정을 변경할 수 있습니다:

```bash
# OCR 설정
OCR_LANGUAGE=korean           # OCR 언어
OCR_USE_ANGLE_CLS=True       # 각도 분류 사용
OCR_USE_GPU=False            # GPU 사용 여부
OCR_DET_LIMIT_SIDE_LEN=960   # 검출 제한 길이
OCR_REC_BATCH_NUM=6          # 인식 배치 수

# 로깅 설정
LOG_LEVEL=INFO               # 로그 레벨
LOG_FILE=logs/entocr.log     # 로그 파일 경로

# 출력 설정
OUTPUT_FORMAT=json           # 출력 형식
OUTPUT_INDENT=2              # JSON 들여쓰기
OUTPUT_ENSURE_ASCII=False    # ASCII 강제 여부

# 이미지 처리 설정
MAX_IMAGE_SIZE=2048          # 최대 이미지 크기
SUPPORTED_FORMATS=jpg,jpeg,png,bmp,tiff  # 지원 형식

# 애플리케이션 설정
DEBUG=False                  # 디버그 모드
```

## 출력 JSON 구조

```json
{
  "source_image": "input/document.jpg",
  "success": true,
  "ocr_summary": {
    "text_count": 10,
    "average_confidence": 0.92,
    "processing_time": 2.3,
    "image_size": [800, 600]
  },
  "text_boxes": [
    {
      "text": "문서 제목",
      "confidence": 0.95,
      "coordinates": [[20, 20], [200, 20], [200, 50], [20, 50]],
      "bbox": [20, 20, 200, 50],
      "center": [110.0, 35.0]
    }
  ],
  "structured_data": {
    "key_value_pairs": {
      "이름": "홍길동",
      "전화번호": "010-1234-5678"
    },
    "tables": [
      {
        "항목": "상품A",
        "수량": "10",
        "가격": "1,000원"
      }
    ],
    "numbers_and_amounts": {
      "amount_0": "₩1,000",
      "number_0": "10"
    },
    "dates": ["2024-01-15", "2024/03/20"],
    "raw_text_lines": ["문서 제목", "이름: 홍길동"],
    "layout_analysis": {
      "document_bounds": {
        "left": 20,
        "top": 20,
        "right": 780,
        "bottom": 580
      },
      "text_density": 10,
      "avg_confidence": 0.92
    }
  },
  "extraction_metadata": {
    "extraction_time": "2024-01-15T10:30:45",
    "processing_successful": true,
    "text_boxes_count": 10,
    "total_characters": 150,
    "avg_confidence": 0.92,
    "processing_time": 2.3,
    "image_size": [800, 600]
  }
}
```

## 개발

### 테스트 실행

```bash
# 전체 테스트 실행
pytest

# 커버리지 포함
pytest --cov=src

# 특정 테스트 파일 실행
pytest tests/test_models.py

# 상세 출력
pytest -v
```

### 코드 품질 검사

```bash
# 린팅
ruff check src tests

# 포맷팅
black src tests

# 타입 검사
mypy src
```

### 개발 환경 설정

```bash
# 개발 의존성 설치
pip install -r requirements-dev.txt

# pre-commit 설정
pre-commit install
```

## 지원하는 이미지 형식

- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- TIFF (.tiff, .tif)

## 시스템 요구사항

- Python 3.8+
- 메모리: 최소 4GB RAM (GPU 사용시 추가 VRAM 필요)
- 디스크: 약 1GB (모델 파일 포함)

## 라이선스

MIT License

## 기여

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Run tests and linting
6. Submit a pull request

## 문제 해결

### 일반적인 문제

1. **PaddleOCR 설치 오류**
   ```bash
   pip install paddlepaddle-gpu  # GPU 버전
   # 또는
   pip install paddlepaddle      # CPU 버전
   ```

2. **메모리 부족 오류**
   - `MAX_IMAGE_SIZE` 설정값을 낮춰보세요
   - GPU 사용을 비활성화해보세요 (`--no-gpu`)

3. **언어 모델 다운로드 실패**
   - 인터넷 연결을 확인하세요
   - 방화벽 설정을 확인하세요

### 로그 확인

```bash
# 디버그 로그 활성화
python -m entocr input/document.jpg --log-level DEBUG

# 로그 파일 확인
tail -f logs/entocr.log
```

## 업데이트 로그

### v0.1.0
- 초기 릴리스
- PaddleOCR 기반 OCR 기능
- JSON 데이터 추출
- CLI 도구
- 배치 처리 지원
