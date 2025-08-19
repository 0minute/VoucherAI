"""OCR service using PaddleOCR for text detection and recognition."""

import time
from pathlib import Path
from typing import List, Optional, Tuple, Union

import cv2
import numpy as np
from loguru import logger
from paddleocr import PaddleOCR
from PIL import Image

from config.settings import settings
from .models import OCRResult, TextBox


class OCRService:
    """Service for performing OCR on images using PaddleOCR."""

    def __init__(
        self,
        language: Optional[str] = None,
        use_angle_cls: Optional[bool] = None,
        use_gpu: Optional[bool] = None,
        det_limit_side_len: Optional[int] = None,
        rec_batch_num: Optional[int] = None,
    ) -> None:
        """Initialize OCR service with configuration.
        
        Args:
            language: OCR language (defaults to settings value)
            use_angle_cls: Whether to use angle classification (defaults to settings value)
            use_gpu: Whether to use GPU acceleration (defaults to settings value)
            det_limit_side_len: Detection limit side length (defaults to settings value)
            rec_batch_num: Recognition batch number (defaults to settings value)
        """
        self.language = language or settings.ocr_language
        self.use_angle_cls = use_angle_cls if use_angle_cls is not None else settings.ocr_use_angle_cls
        self.use_gpu = use_gpu if use_gpu is not None else settings.ocr_use_gpu
        self.det_limit_side_len = det_limit_side_len or settings.ocr_det_limit_side_len
        self.rec_batch_num = rec_batch_num or settings.ocr_rec_batch_num
        
        self._ocr_engine: Optional[PaddleOCR] = None
        logger.info(f"OCR Service initialized with language: {self.language}")

    @property
    def ocr_engine(self) -> PaddleOCR:
        """Lazy initialization of PaddleOCR engine."""
        if self._ocr_engine is None:
            logger.info("Initializing PaddleOCR engine...")
            
            # 기본 파라미터만 사용 (호환성을 위해)
            base_params = {
                "use_angle_cls": self.use_angle_cls,
                "lang": self.language,
            }
            
            # 선택적 파라미터들 (버전에 따라 지원여부가 다름)
            optional_params = {
                "det_limit_side_len": self.det_limit_side_len,
                "rec_batch_num": self.rec_batch_num
            }

            # "show_log": settings.debug 
            
            if self.use_gpu:
                optional_params["use_gpu"] = True
            
            # PaddleOCR 초기화 (점진적으로 파라미터 제거하면서 시도)
            initialization_attempts = [
                {**base_params, **optional_params},  # 모든 파라미터 포함
                {**base_params, **{k: v for k, v in optional_params.items() if k != "show_log"}},  # show_log 제외
                {**base_params, **{k: v for k, v in optional_params.items() if k not in ["show_log", "use_gpu"]}},  # show_log, use_gpu 제외
                {**base_params, **{k: v for k, v in optional_params.items() if k not in ["show_log", "use_gpu", "rec_batch_num"]}},  # 더 많은 파라미터 제외
                base_params,  # 기본 파라미터만
            ]
            
            last_error = None
            for i, params in enumerate(initialization_attempts):
                try:
                    self._ocr_engine = PaddleOCR(**params)
                    if i > 0:
                        logger.warning(f"PaddleOCR initialized with reduced parameters (attempt {i+1})")
                    else:
                        logger.info("PaddleOCR engine initialized successfully with all parameters")
                    break
                except Exception as e:
                    last_error = e
                    error_msg = str(e).lower()
                    if "unknown argument" in error_msg:
                        logger.warning(f"Attempt {i+1} failed: {e}")
                        continue
                    else:
                        # 다른 종류의 오류는 즉시 중단
                        logger.error(f"PaddleOCR initialization failed: {e}")
                        raise
            else:
                # 모든 시도가 실패한 경우
                logger.error(f"Failed to initialize PaddleOCR after all attempts. Last error: {last_error}")
                raise RuntimeError(f"PaddleOCR initialization failed: {last_error}")
        return self._ocr_engine

    def _validate_image_file(self, image_path: Union[str, Path]) -> Path:
        """Validate image file exists and has supported format.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Validated Path object
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image format is not supported
        """
        path = Path(image_path)
        if not path.exists():
            raise FileNotFoundError(f"Image file not found: {path}")
        
        if path.suffix.lower().lstrip('.') not in settings.supported_formats_list:
            raise ValueError(
                f"Unsupported image format: {path.suffix}. "
                f"Supported formats: {settings.supported_formats_list}"
            )
        
        return path

    def _preprocess_image(self, image_path: Path) -> np.ndarray:
        """Preprocess image for OCR.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Preprocessed image as numpy array
            
        Raises:
            ValueError: If image cannot be loaded or is too large
        """
        # Load image using OpenCV
        image = cv2.imread(str(image_path))
        if image is None:
            raise ValueError(f"Could not load image: {image_path}")
        
        # Check image size
        height, width = image.shape[:2]
        max_size = settings.max_image_size
        
        if max(height, width) > max_size:
            # Resize image while maintaining aspect ratio
            if height > width:
                new_height = max_size
                new_width = int(width * max_size / height)
            else:
                new_width = max_size
                new_height = int(height * max_size / width)
            
            image = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            logger.info(f"Resized image from {width}x{height} to {new_width}x{new_height}")
        
        return image

    def _parse_ocr_results(self, raw_results: List, image_shape: Tuple[int, int]) -> List[TextBox]:
        """Parse raw PaddleOCR results into TextBox objects.
        
        Args:
            raw_results: Raw results from PaddleOCR
            image_shape: Original image shape (height, width)
            
        Returns:
            List of TextBox objects
        """
        text_boxes = []
        
        for result in raw_results:
            try:
                # PaddleOCR 결과 구조는 버전에 따라 다를 수 있음
                if len(result) < 2:
                    continue
                
                # 다양한 결과 구조 처리
                if len(result) == 2:
                    # 일반적인 구조: [coordinates, (text, confidence)]
                    coordinates_raw, text_info = result
                    
                    if isinstance(text_info, (list, tuple)) and len(text_info) >= 2:
                        text, confidence = text_info[0], text_info[1]
                    elif isinstance(text_info, dict):
                        text = text_info.get('text', '')
                        confidence = text_info.get('confidence', 0.0)
                    else:
                        # 단순한 텍스트만 있는 경우
                        text = str(text_info)
                        confidence = 1.0
                        
                elif len(result) == 3:
                    # 다른 구조: [coordinates, text, confidence]
                    coordinates_raw, text, confidence = result
                else:
                    logger.warning(f"Unexpected OCR result structure: {result}")
                    continue
                
                # Convert coordinates to integer format
                if isinstance(coordinates_raw, (list, tuple)):
                    coordinates = [[int(point[0]), int(point[1])] for point in coordinates_raw]
                else:
                    logger.warning(f"Invalid coordinates format: {coordinates_raw}")
                    continue
                
                text_box = TextBox(
                    coordinates=coordinates,
                    text=str(text).strip(),
                    confidence=float(confidence)
                )
                text_boxes.append(text_box)
                
            except Exception as e:
                logger.warning(f"Failed to parse OCR result: {result}, error: {e}")
                continue
        
        logger.debug(f"Parsed {len(text_boxes)} text boxes from OCR results")
        return text_boxes

    def _parse_paddlex_results(self, raw_results, image_shape: Tuple[int, int]) -> List[TextBox]:
        """Parse PaddleX results into TextBox objects.
        
        Args:
            raw_results: Raw results from PaddleX (can be dict or object)
            image_shape: Original image shape (height, width)
            
        Returns:
            List of TextBox objects
        """
        text_boxes = []
        
        try:
            # PaddleX 결과에서 텍스트와 좌표 정보 추출
            if hasattr(raw_results, 'get'):
                # 딕셔너리 접근
                rec_texts = raw_results.get('rec_texts', [])
                rec_scores = raw_results.get('rec_scores', [])
                rec_polys = raw_results.get('rec_polys', raw_results.get('dt_polys', []))
            else:
                # 객체 접근 시도
                rec_texts = getattr(raw_results, 'rec_texts', [])
                rec_scores = getattr(raw_results, 'rec_scores', [])
                rec_polys = getattr(raw_results, 'rec_polys', getattr(raw_results, 'dt_polys', []))
            
            logger.info(f"Found {len(rec_texts)} texts, {len(rec_scores)} scores, {len(rec_polys)} polygons")
            if rec_texts:
                logger.info(f"Sample texts: {rec_texts[:3]}")  # 처음 3개 텍스트 로그
            
            # 텍스트, 점수, 좌표를 조합하여 TextBox 생성
            for i, text in enumerate(rec_texts):
                try:
                    # 신뢰도 점수 가져오기
                    confidence = rec_scores[i] if i < len(rec_scores) else 1.0
                    
                    # 좌표 정보 가져오기
                    if i < len(rec_polys):
                        poly = rec_polys[i]
                        if hasattr(poly, 'tolist'):
                            # numpy array인 경우
                            coordinates = poly.tolist()
                        else:
                            coordinates = list(poly)
                        
                        # 좌표가 4개 점이 아닌 경우 처리
                        if len(coordinates) < 4:
                            # 기본 좌표 생성
                            coordinates = [[0, 0], [100, 0], [100, 20], [0, 20]]
                        else:
                            # 처음 4개 점만 사용
                            coordinates = coordinates[:4]
                        
                        # 좌표를 정수로 변환
                        coordinates = [[int(point[0]), int(point[1])] for point in coordinates]
                    else:
                        # 좌표 정보가 없는 경우 기본값 사용
                        coordinates = [[0, 0], [100, 0], [100, 20], [0, 20]]
                    
                    # 빈 텍스트 제외
                    if text and text.strip():
                        text_box = TextBox(
                            coordinates=coordinates,
                            text=str(text).strip(),
                            confidence=float(confidence)
                        )
                        text_boxes.append(text_box)
                        
                except Exception as e:
                    logger.warning(f"Failed to parse text item {i}: {text}, error: {e}")
                    continue
            
            logger.info(f"Successfully parsed {len(text_boxes)} text boxes from PaddleX results")
                
        except Exception as e:
            logger.error(f"Failed to parse PaddleX results: {e}")
            logger.debug(f"Raw results type: {type(raw_results)}")
            if hasattr(raw_results, '__dict__'):
                logger.debug(f"Raw results attributes: {list(raw_results.__dict__.keys())}")
        
        return text_boxes

    def extract_text(self, image_path: Union[str, Path]) -> OCRResult:
        """Extract text from image using OCR.
        
        Args:
            image_path: Path to image file
            
        Returns:
            OCRResult containing detected text boxes and metadata
            
        Raises:
            FileNotFoundError: If image file doesn't exist
            ValueError: If image format is not supported or image cannot be processed
        """
        start_time = time.time()
        
        # Validate and preprocess image
        validated_path = self._validate_image_file(image_path)
        image = self._preprocess_image(validated_path)
        
        logger.info(f"Starting OCR extraction for: {validated_path}")
        
        try:
            # Perform OCR (새로운 PaddleX 방식)
            try:
                # PaddleX 3.x 방식
                if hasattr(self.ocr_engine, 'predict'):
                    raw_results = self.ocr_engine.predict(str(validated_path))
                    logger.debug("Using PaddleX predict method")
                else:
                    # 기존 PaddleOCR 방식
                    raw_results = self.ocr_engine.ocr(image)
                    logger.debug("Using PaddleOCR ocr method")
            except Exception as e:
                logger.warning(f"First OCR method failed: {e}, trying alternative")
                try:
                    raw_results = self.ocr_engine.ocr(image)
                except Exception as e2:
                    logger.error(f"All OCR methods failed: {e2}")
                    raise
            
            # Handle case where no text is detected
            if not raw_results or not raw_results[0]:
                logger.warning(f"No text detected in image: {validated_path}")
                raw_results = [[]]
            
            # 디버그: OCR 결과 구조 확인 (안전하게)
            try:
                if settings.debug:
                    logger.debug(f"OCR raw results type: {type(raw_results)}")
                    if raw_results:
                        logger.debug(f"OCR raw results length: {len(raw_results)}")
                        if len(raw_results) > 0:
                            logger.debug(f"First element type: {type(raw_results[0])}")
                            # 크기가 큰 경우 요약만 출력
                            first_elem = raw_results[0]
                            if hasattr(first_elem, '__dict__'):
                                logger.debug(f"First element keys: {list(first_elem.__dict__.keys()) if hasattr(first_elem, '__dict__') else 'No dict'}")
                            elif isinstance(first_elem, dict):
                                logger.debug(f"First element keys: {list(first_elem.keys())}")
                            else:
                                logger.debug(f"First element: {str(first_elem)[:200]}...")
            except Exception as debug_e:
                logger.warning(f"Debug logging failed: {debug_e}")
            
            # Parse results (다양한 결과 구조 처리)
            if isinstance(raw_results, list) and len(raw_results) > 0:
                first_result = raw_results[0]
                if hasattr(first_result, 'get') or isinstance(first_result, dict):
                    # PaddleX 결과 구조 (딕셔너리 형태 또는 객체)
                    text_boxes = self._parse_paddlex_results(first_result, image.shape[:2])
                else:
                    # 기존 PaddleOCR 결과 구조
                    text_boxes = self._parse_ocr_results(raw_results[0], image.shape[:2])
            elif isinstance(raw_results, dict):
                # 단일 딕셔너리 PaddleX 결과
                text_boxes = self._parse_paddlex_results(raw_results, image.shape[:2])
            else:
                logger.warning("Unknown OCR result format")
                text_boxes = []
            
            processing_time = time.time() - start_time
            
            result = OCRResult(
                text_boxes=text_boxes,
                processing_time=processing_time,
                image_size=(image.shape[1], image.shape[0])  # (width, height)
            )
            
            logger.info(
                f"OCR completed: {len(text_boxes)} text boxes found in {processing_time:.2f}s "
                f"(avg confidence: {result.average_confidence:.3f})"
            )
            
            return result
            
        except Exception as e:
            logger.error(f"OCR extraction failed for {validated_path}: {e}")
            raise ValueError(f"OCR extraction failed: {e}") from e

    def batch_extract_text(self, image_paths: List[Union[str, Path]]) -> List[OCRResult]:
        """Extract text from multiple images.
        
        Args:
            image_paths: List of paths to image files
            
        Returns:
            List of OCRResult objects, one per image
        """
        results = []
        
        for i, image_path in enumerate(image_paths, 1):
            try:
                logger.info(f"Processing image {i}/{len(image_paths)}: {image_path}")
                result = self.extract_text(image_path)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to process {image_path}: {e}")
                # Create empty result for failed images
                empty_result = OCRResult(
                    text_boxes=[],
                    processing_time=0.0,
                    image_size=(0, 0)
                )
                results.append(empty_result)
        
        return results
