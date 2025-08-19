"""Entocr: OCR image data extraction to JSON using PaddleOCR."""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

from .extractor import ImageDataExtractor
from .models import ExtractionResult, OCRResult, TextBox
from .ocr_service import OCRService
from .pdf_converter import PDFConverter, convert_pdf_to_png, get_pdf_page_count
from .jpg_converter import convert_jpg_to_png

__all__ = [
    "ImageDataExtractor",
    "OCRService", 
    "ExtractionResult",
    "OCRResult",
    "TextBox",
    "PDFConverter",
    "convert_pdf_to_png",
    "get_pdf_page_count",
    "convert_jpg_to_png",
]
