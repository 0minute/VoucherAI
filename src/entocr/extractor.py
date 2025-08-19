"""Main data extractor for converting images to structured JSON data."""

import json
import re
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from loguru import logger

from config.settings import settings
from .models import ExtractionResult, TextBox
from .ocr_service import OCRService
from .pdf_converter import PDFConverter


class ImageDataExtractor:
    """Main class for extracting structured data from images using OCR."""

    def __init__(self, ocr_service: Optional[OCRService] = None) -> None:
        """Initialize the data extractor.
        
        Args:
            ocr_service: Optional OCR service instance. If None, creates a new one.
        """
        self.ocr_service = ocr_service or OCRService()
        self.pdf_converter = PDFConverter()
        logger.info("ImageDataExtractor initialized")

    def _extract_key_value_pairs(self, text_boxes: List[TextBox]) -> Dict[str, Any]:
        """Extract key-value pairs from OCR text boxes.
        
        Args:
            text_boxes: List of detected text boxes
            
        Returns:
            Dictionary of extracted key-value pairs
        """
        key_value_pairs = {}
        
        # Sort text boxes by vertical position (top to bottom)
        sorted_boxes = sorted(text_boxes, key=lambda box: box.center[1])
        
        for i, box in enumerate(sorted_boxes):
            text = box.text.strip()
            
            # Look for patterns like "Key: Value" or "Key Value"
            colon_match = re.match(r'^(.+?):\s*(.+)$', text)
            if colon_match:
                key, value = colon_match.groups()
                key_value_pairs[key.strip()] = value.strip()
                continue
            
            # Look for adjacent text boxes that might be key-value pairs
            if i < len(sorted_boxes) - 1:
                next_box = sorted_boxes[i + 1]
                
                # Check if boxes are horizontally aligned (same row)
                y_diff = abs(box.center[1] - next_box.center[1])
                if y_diff < 20:  # Threshold for same row
                    # If current box ends with ":" treat as key
                    if text.endswith(':'):
                        key = text.rstrip(':').strip()
                        value = next_box.text.strip()
                        key_value_pairs[key] = value
        
        return key_value_pairs

    def _extract_tables(self, text_boxes: List[TextBox]) -> List[Dict[str, Any]]:
        """Extract table-like structures from text boxes.
        
        Args:
            text_boxes: List of detected text boxes
            
        Returns:
            List of table rows as dictionaries
        """
        tables = []
        
        # Group text boxes by rows (similar Y coordinates)
        rows = []
        for box in text_boxes:
            placed = False
            for row in rows:
                # Check if box belongs to existing row
                if any(abs(box.center[1] - existing_box.center[1]) < 15 for existing_box in row):
                    row.append(box)
                    placed = True
                    break
            
            if not placed:
                rows.append([box])
        
        # Sort rows by Y coordinate and boxes within rows by X coordinate
        rows.sort(key=lambda row: min(box.center[1] for box in row))
        for row in rows:
            row.sort(key=lambda box: box.center[0])
        
        # If we have multiple rows with similar column count, treat as table
        if len(rows) >= 2:
            column_counts = [len(row) for row in rows]
            avg_columns = sum(column_counts) / len(column_counts)
            
            # Check if rows have similar column counts (table-like structure)
            if all(abs(count - avg_columns) <= 1 for count in column_counts):
                # Use first row as headers if it looks like headers
                headers = [box.text.strip() for box in rows[0]]
                
                for row in rows[1:]:
                    if len(row) == len(headers):
                        row_data = {}
                        for header, box in zip(headers, row):
                            row_data[header] = box.text.strip()
                        tables.append(row_data)
        
        return tables

    def _extract_numbers_and_amounts(self, text_boxes: List[TextBox]) -> Dict[str, Any]:
        """Extract numeric values and amounts from text.
        
        Args:
            text_boxes: List of detected text boxes
            
        Returns:
            Dictionary of extracted numeric data
        """
        numbers = {}
        
        # Patterns for different number formats
        currency_pattern = r'[\₩$€£¥]\s*[\d,]+(?:\.\d{2})?'
        number_pattern = r'\b\d{1,3}(?:,\d{3})*(?:\.\d+)?\b'
        percentage_pattern = r'\b\d+(?:\.\d+)?%\b'
        
        for box in text_boxes:
            text = box.text.strip()
            
            # Extract currency amounts
            currency_matches = re.findall(currency_pattern, text)
            if currency_matches:
                numbers[f'amount_{len(numbers)}'] = currency_matches[0]
            
            # Extract percentages
            percentage_matches = re.findall(percentage_pattern, text)
            if percentage_matches:
                numbers[f'percentage_{len(numbers)}'] = percentage_matches[0]
            
            # Extract general numbers
            number_matches = re.findall(number_pattern, text)
            if number_matches:
                for num in number_matches:
                    numbers[f'number_{len(numbers)}'] = num
        
        return numbers

    def _extract_dates(self, text_boxes: List[TextBox]) -> List[str]:
        """Extract date patterns from text.
        
        Args:
            text_boxes: List of detected text boxes
            
        Returns:
            List of detected dates
        """
        dates = []
        
        # Various date patterns
        date_patterns = [
            r'\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b',  # YYYY-MM-DD, YYYY/MM/DD, YYYY.MM.DD
            r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{4}\b',  # DD-MM-YYYY, MM/DD/YYYY, etc.
            r'\b\d{1,2}[-/.]\d{1,2}[-/.]\d{2}\b',  # DD-MM-YY, MM/DD/YY, etc.
            r'\b\d{4}년\s*\d{1,2}월\s*\d{1,2}일\b',  # Korean date format
        ]
        
        for box in text_boxes:
            text = box.text.strip()
            for pattern in date_patterns:
                matches = re.findall(pattern, text)
                dates.extend(matches)
        
        return list(set(dates))  # Remove duplicates

    def _analyze_layout(self, text_boxes: List[TextBox]) -> Dict[str, Any]:
        """Analyze the layout and structure of the document.
        
        Args:
            text_boxes: List of detected text boxes
            
        Returns:
            Dictionary with layout analysis results
        """
        if not text_boxes:
            return {}
        
        # Calculate document boundaries
        all_x = [coord[0] for box in text_boxes for coord in box.coordinates]
        all_y = [coord[1] for box in text_boxes for coord in box.coordinates]
        
        layout_info = {
            'document_bounds': {
                'left': min(all_x),
                'top': min(all_y),
                'right': max(all_x),
                'bottom': max(all_y)
            },
            'text_density': len(text_boxes),
            'avg_confidence': sum(box.confidence for box in text_boxes) / len(text_boxes),
            'text_sizes': []
        }
        
        # Analyze text box sizes
        for box in text_boxes:
            bbox = box.bbox
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            layout_info['text_sizes'].append({'width': width, 'height': height})
        
        return layout_info

    def extract_from_image(
        self, 
        image_path: Union[str, Path],
        custom_processors: Optional[List[callable]] = None
    ) -> ExtractionResult:
        """Extract structured data from an image.
        
        Args:
            image_path: Path to the image file
            custom_processors: Optional list of custom processing functions
            
        Returns:
            ExtractionResult containing OCR results and structured data
        """
        image_path = Path(image_path)
        logger.info(f"Starting data extraction from: {image_path}")
        
        try:
            # Perform OCR
            ocr_result = self.ocr_service.extract_text(image_path)
            
            if not ocr_result.text_boxes:
                logger.warning(f"No text detected in image: {image_path}")
                return ExtractionResult(
                    source_image=str(image_path),
                    ocr_result=ocr_result,
                    structured_data={},
                    extraction_metadata={
                        'extraction_time': datetime.now().isoformat(),
                        'processing_successful': False,
                        'error': 'No text detected'
                    }
                )
            
            # Extract structured data
            structured_data = {
                'key_value_pairs': self._extract_key_value_pairs(ocr_result.text_boxes),
                'tables': self._extract_tables(ocr_result.text_boxes),
                'numbers_and_amounts': self._extract_numbers_and_amounts(ocr_result.text_boxes),
                'dates': self._extract_dates(ocr_result.text_boxes),
                'raw_text_lines': [box.text for box in ocr_result.text_boxes],
                'layout_analysis': self._analyze_layout(ocr_result.text_boxes)
            }
            
            # Apply custom processors if provided
            if custom_processors:
                for processor in custom_processors:
                    try:
                        custom_data = processor(ocr_result.text_boxes)
                        if isinstance(custom_data, dict):
                            structured_data.update(custom_data)
                    except Exception as e:
                        logger.warning(f"Custom processor failed: {e}")
            
            # Create extraction metadata
            extraction_metadata = {
                'extraction_time': datetime.now().isoformat(),
                'processing_successful': True,
                'text_boxes_count': len(ocr_result.text_boxes),
                'total_characters': sum(len(box.text) for box in ocr_result.text_boxes),
                'avg_confidence': ocr_result.average_confidence,
                'processing_time': ocr_result.processing_time,
                'image_size': ocr_result.image_size
            }
            
            result = ExtractionResult(
                source_image=str(image_path),
                ocr_result=ocr_result,
                structured_data=structured_data,
                extraction_metadata=extraction_metadata
            )
            
            logger.info(f"Data extraction completed successfully for: {image_path}")
            return result
            
        except Exception as e:
            logger.error(f"Data extraction failed for {image_path}: {e}")
            raise

    def extract_to_json(
        self, 
        image_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        custom_processors: Optional[List[callable]] = None
    ) -> str:
        """Extract data from image and save as JSON.
        
        Args:
            image_path: Path to the image file
            output_path: Optional output path for JSON file
            custom_processors: Optional list of custom processing functions
            
        Returns:
            JSON string of extracted data
        """
        # Extract data
        result = self.extract_from_image(image_path, custom_processors)
        
        # Convert to JSON
        json_data = result.to_json_dict()
        json_string = json.dumps(
            json_data,
            indent=settings.output_indent,
            ensure_ascii=settings.output_ensure_ascii
        )
        
        # Save to file if output path provided
        if output_path:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(json_string)
            
            logger.info(f"JSON data saved to: {output_path}")
        
        return json_string

    def batch_extract_to_json(
        self,
        image_paths: List[Union[str, Path]],
        output_dir: Union[str, Path],
        custom_processors: Optional[List[callable]] = None
    ) -> List[str]:
        """Extract data from multiple images and save as JSON files.
        
        Args:
            image_paths: List of image file paths
            output_dir: Directory to save JSON files
            custom_processors: Optional list of custom processing functions
            
        Returns:
            List of JSON strings for each processed image
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        json_results = []
        
        for image_path in image_paths:
            try:
                image_path = Path(image_path)
                output_path = output_dir / f"{image_path.stem}_extracted.json"
                
                json_string = self.extract_to_json(
                    image_path, 
                    output_path, 
                    custom_processors
                )
                json_results.append(json_string)
                
            except Exception as e:
                logger.error(f"Failed to process {image_path}: {e}")
                json_results.append("{}")
        
        return json_results
    
#-----------------------------------------------------------------------------------------------------------------------
#pdf 변환 관련 코드 
    # 이미지 전처리를 별도로 일괄 수행한 후 OCR 처리할 것이므로 아래 코드 사용하지 않을 예정임
    def extract_from_pdf(
        self, 
        pdf_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        custom_processors: Optional[List] = None,
        keep_images: bool = False,
        dpi: int = 300,
        max_pages: Optional[int] = None
    ) -> Dict[str, Any]:
        """Extract data from PDF by converting to images first.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Directory to save results (None for same as PDF)
            custom_processors: Custom data processing functions
            keep_images: Whether to keep converted PNG files
            dpi: DPI for PDF to image conversion
            max_pages: Maximum number of pages to process
            
        Returns:
            Dictionary with extraction results for all pages
            
        Raises:
            ValueError: If PDF file doesn't exist
            RuntimeError: If PDF conversion fails
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise ValueError(f"PDF file not found: {pdf_path}")
        
        logger.info(f"Starting PDF extraction from: {pdf_path}")
        
        # Set up output directory
        if output_dir is None:
            output_dir = pdf_path.parent
        else:
            output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create temporary directory for images
        temp_dir = Path(tempfile.mkdtemp(prefix="pdf_extract_"))
        
        try:
            # Convert PDF to images
            self.pdf_converter.dpi = dpi
            self.pdf_converter.max_pages = max_pages
            
            logger.info(f"Converting PDF to images at {dpi} DPI...")
            image_paths = self.pdf_converter.convert_pdf_to_images(
                pdf_path, 
                temp_dir if not keep_images else output_dir / "pages",
                filename_prefix=f"{pdf_path.stem}_page"
            )
            
            if not image_paths:
                logger.error("No images were generated from PDF")
                return {
                    "pdf_info": {
                        "source_file": str(pdf_path),
                        "total_pages": 0,
                        "conversion_dpi": dpi,
                        "processed_at": datetime.now().isoformat(),
                        "error": "PDF conversion failed"
                    },
                    "pages": [],
                    "summary": {
                        "total_text_boxes": 0,
                        "average_confidence": 0.0,
                        "processing_time": 0.0,
                        "successful_pages": 0,
                        "failed_pages": 0,
                        "error": "PDF conversion failed"
                    }
                }
            
            logger.info(f"Converted {len(image_paths)} pages to images")
            
            # Process each page
            results = {
                "pdf_info": {
                    "source_file": str(pdf_path),
                    "total_pages": len(image_paths),
                    "conversion_dpi": dpi,
                    "processed_at": datetime.now().isoformat()
                },
                "pages": [],
                "summary": {
                    "total_text_boxes": 0,
                    "average_confidence": 0.0,
                    "processing_time": 0.0
                }
            }
            
            total_boxes = 0
            total_confidence = 0.0
            total_time = 0.0
            
            for i, image_path in enumerate(image_paths):
                logger.info(f"Processing page {i+1}/{len(image_paths)}: {image_path.name}")
                
                try:
                    # Extract data from this page
                    page_result = self.extract_from_image(image_path, custom_processors)
                    
                    # Add page info (convert ExtractionResult to dict)
                    if hasattr(page_result, 'model_dump'):
                        # Pydantic v2
                        result_dict = page_result.model_dump()
                    elif hasattr(page_result, 'dict'):
                        # Pydantic v1
                        result_dict = page_result.dict()
                    else:
                        # Fallback for other objects
                        result_dict = page_result.__dict__
                    
                    page_data = {
                        "page_number": i + 1,
                        "image_file": str(image_path.name),
                        "extraction_result": result_dict
                    }
                    results["pages"].append(page_data)
                    
                    # Update summary statistics
                    if hasattr(page_result, 'ocr_summary'):
                        summary = page_result.ocr_summary
                        total_boxes += summary.get('text_count', 0)
                        total_confidence += summary.get('average_confidence', 0.0)
                        total_time += summary.get('processing_time', 0.0)
                    
                    logger.info(f"Page {i+1} processed successfully")
                    
                except Exception as e:
                    logger.error(f"Failed to process page {i+1}: {e}")
                    page_data = {
                        "page_number": i + 1,
                        "image_file": str(image_path.name),
                        "error": str(e),
                        "extraction_result": None
                    }
                    results["pages"].append(page_data)
            
            # Calculate final summary
            valid_pages = len([p for p in results["pages"] if p.get("extraction_result")])
            if valid_pages > 0:
                results["summary"].update({
                    "total_text_boxes": total_boxes,
                    "average_confidence": total_confidence / valid_pages,
                    "processing_time": total_time,
                    "successful_pages": valid_pages,
                    "failed_pages": len(image_paths) - valid_pages
                })
            
            logger.info(f"PDF extraction completed: {valid_pages}/{len(image_paths)} pages processed")
            
            return results
            
        finally:
            # Clean up temporary files if not keeping them
            if not keep_images:
                self.pdf_converter.cleanup_temp_files(image_paths)
                try:
                    temp_dir.rmdir()
                except Exception as e:
                    logger.debug(f"Could not remove temp directory: {e}")

    # 이미지 전처리를 별도로 일괄 수행한 후 OCR 처리할 것이므로 아래 코드 사용하지 않을 예정임
    def extract_pdf_to_json(
        self,
        pdf_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        custom_processors: Optional[List] = None,
        keep_images: bool = False,
        dpi: int = 300,
        max_pages: Optional[int] = None
    ) -> str:
        """Extract data from PDF and save as JSON.
        
        Args:
            pdf_path: Path to PDF file
            output_path: Path for output JSON file (None for auto-generated)
            custom_processors: Custom data processing functions
            keep_images: Whether to keep converted PNG files
            dpi: DPI for PDF to image conversion
            max_pages: Maximum number of pages to process
            
        Returns:
            JSON string with extraction results
        """
        pdf_path = Path(pdf_path)
        
        if output_path is None:
            output_path = pdf_path.parent / f"{pdf_path.stem}_extracted.json"
        else:
            output_path = Path(output_path)
        
        # Extract data from PDF
        results = self.extract_from_pdf(
            pdf_path, 
            output_path.parent,
            custom_processors,
            keep_images,
            dpi,
            max_pages
        )
        
        # Save to JSON file
        json_string = json.dumps(results, ensure_ascii=False, indent=2)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_string)
        
        logger.info(f"PDF extraction results saved to: {output_path}")
        
        return json_string

    # 필요
    def is_pdf_file(self, file_path: Union[str, Path]) -> bool:
        """Check if file is a PDF.
        
        Args:
            file_path: Path to file
            
        Returns:
            True if file is PDF, False otherwise
        """
        file_path = Path(file_path)
        return file_path.suffix.lower() == '.pdf'
    
    # 이미지 전처리를 별도로 일괄 수행한 후 OCR 처리할 것이므로 아래 코드 사용하지 않을 예정임
    def auto_extract(
        self,
        input_path: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
        **kwargs
    ) -> str:
        """Automatically detect file type and extract data.
        
        Args:
            input_path: Path to input file (image or PDF)
            output_path: Path for output JSON file
            **kwargs: Additional arguments passed to extraction methods
            
        Returns:
            JSON string with extraction results
        """
        input_path = Path(input_path)
        
        if self.is_pdf_file(input_path):
            logger.info(f"Detected PDF file: {input_path}")
            return self.extract_pdf_to_json(input_path, output_path, **kwargs)
        else:
            logger.info(f"Detected image file: {input_path}")
            return self.extract_to_json(input_path, output_path, **kwargs)
