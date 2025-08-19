"""PDF to PNG conversion utilities for OCR processing.

This module provides functionality to convert PDF documents to PNG images
that can be processed by the ImageDataExtractor.
"""

import tempfile
from pathlib import Path
from typing import List, Union, Optional, Tuple
import shutil

from loguru import logger
from PIL import Image

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False
    logger.warning("PyMuPDF not available. PDF conversion may be limited.")

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False
    logger.warning("pdf2image not available. PDF conversion may be limited.")


class PDFConverter:
    """Converts PDF documents to PNG images for OCR processing.
    
    This class provides multiple methods for PDF to PNG conversion,
    with fallback options if certain libraries are not available.
    """
    
    def __init__(
        self,
        dpi: int = 300,
        output_format: str = "PNG",
        max_pages: Optional[int] = None,
        temp_dir: Optional[Union[str, Path]] = None
    ) -> None:
        """Initialize PDF converter.
        
        Args:
            dpi: DPI resolution for converted images
            output_format: Output image format (PNG, JPEG, etc.)
            max_pages: Maximum number of pages to convert (None for all)
            temp_dir: Temporary directory for intermediate files
        """
        self.dpi = dpi
        self.output_format = output_format.upper()
        self.max_pages = max_pages
        self.temp_dir = Path(temp_dir) if temp_dir else None
        
        logger.info(f"PDFConverter initialized with DPI={dpi}, format={output_format}")
    
    def convert_pdf_to_images(
        self,
        pdf_path: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        filename_prefix: str = "page"
    ) -> List[Path]:
        """Convert PDF to PNG images.
        
        Args:
            pdf_path: Path to input PDF file
            output_dir: Directory to save converted images (None for temp dir)
            filename_prefix: Prefix for output filenames
            
        Returns:
            List of paths to converted PNG files
            
        Raises:
            ValueError: If PDF file doesn't exist or conversion fails
            RuntimeError: If no PDF conversion libraries are available
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise ValueError(f"PDF file not found: {pdf_path}")
        
        # Determine output directory
        if output_dir is None:
            if self.temp_dir:
                output_dir = self.temp_dir
            else:
                output_dir = Path(tempfile.mkdtemp(prefix="pdf_convert_"))
        else:
            output_dir = Path(output_dir)
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"Converting PDF to images: {pdf_path} -> {output_dir}")
        
        # Try PyMuPDF first (faster and more reliable)
        if PYMUPDF_AVAILABLE:
            try:
                return self._convert_with_pymupdf(pdf_path, output_dir, filename_prefix)
            except Exception as e:
                logger.warning(f"PyMuPDF conversion failed: {e}. Trying pdf2image...")
        
        # Fall back to pdf2image
        if PDF2IMAGE_AVAILABLE:
            try:
                return self._convert_with_pdf2image(pdf_path, output_dir, filename_prefix)
            except Exception as e:
                logger.error(f"pdf2image conversion failed: {e}")
                raise RuntimeError(f"PDF conversion failed with all available methods") from e
        
        raise RuntimeError("No PDF conversion libraries available. Install PyMuPDF or pdf2image.")
    
    def _convert_with_pymupdf(
        self,
        pdf_path: Path,
        output_dir: Path,
        filename_prefix: str
    ) -> List[Path]:
        """Convert PDF using PyMuPDF (fitz).
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory
            filename_prefix: Filename prefix
            
        Returns:
            List of converted image paths
        """
        image_paths = []
        
        with fitz.open(pdf_path) as doc:
            page_count = len(doc)
            max_pages = min(page_count, self.max_pages) if self.max_pages else page_count
            
            logger.info(f"Converting {max_pages} pages from PDF with PyMuPDF")
            
            for page_num in range(max_pages):
                page = doc[page_num]
                
                # Create transformation matrix for DPI
                mat = fitz.Matrix(self.dpi / 72, self.dpi / 72)
                pix = page.get_pixmap(matrix=mat)
                
                # Save directly as PNG using PyMuPDF
                output_path = output_dir / f"{filename_prefix}_{page_num + 1:03d}.png"
                pix.save(str(output_path))
                image_paths.append(output_path)
                
                logger.debug(f"Converted page {page_num + 1} -> {output_path}")
        
        logger.info(f"PyMuPDF conversion completed: {len(image_paths)} images")
        return image_paths
    
    def _convert_with_pdf2image(
        self,
        pdf_path: Path,
        output_dir: Path,
        filename_prefix: str
    ) -> List[Path]:
        """Convert PDF using pdf2image.
        
        Args:
            pdf_path: Path to PDF file
            output_dir: Output directory
            filename_prefix: Filename prefix
            
        Returns:
            List of converted image paths
        """
        logger.info(f"Converting PDF with pdf2image at {self.dpi} DPI")
        
        # Convert PDF to images
        images = convert_from_path(
            pdf_path,
            dpi=self.dpi,
            fmt=self.output_format.lower(),
            first_page=1,
            last_page=self.max_pages
        )
        
        image_paths = []
        for i, image in enumerate(images):
            output_path = output_dir / f"{filename_prefix}_{i + 1:03d}.png"
            image.save(output_path, self.output_format)
            image_paths.append(output_path)
            logger.debug(f"Converted page {i + 1} -> {output_path}")
        
        logger.info(f"pdf2image conversion completed: {len(image_paths)} images")
        return image_paths
    
    def get_pdf_info(self, pdf_path: Union[str, Path]) -> dict:
        """Get information about PDF file.
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            Dictionary with PDF information
        """
        pdf_path = Path(pdf_path)
        if not pdf_path.exists():
            raise ValueError(f"PDF file not found: {pdf_path}")
        
        info = {
            "file_path": str(pdf_path),
            "file_size": pdf_path.stat().st_size,
            "pages": 0,
            "title": "",
            "author": "",
            "subject": "",
            "creator": "",
            "producer": "",
            "creation_date": None,
            "modification_date": None
        }
        
        if PYMUPDF_AVAILABLE:
            try:
                with fitz.open(pdf_path) as doc:
                    info["pages"] = len(doc)
                    metadata = doc.metadata
                    info.update({
                        "title": metadata.get("title", ""),
                        "author": metadata.get("author", ""),
                        "subject": metadata.get("subject", ""),
                        "creator": metadata.get("creator", ""),
                        "producer": metadata.get("producer", ""),
                        "creation_date": metadata.get("creationDate"),
                        "modification_date": metadata.get("modDate")
                    })
            except Exception as e:
                logger.warning(f"Failed to get PDF metadata: {e}")
        
        return info
    
    def cleanup_temp_files(self, image_paths: List[Path]) -> None:
        """Clean up temporary image files.
        
        Args:
            image_paths: List of image file paths to delete
        """
        for path in image_paths:
            try:
                if path.exists():
                    path.unlink()
                    logger.debug(f"Deleted temporary file: {path}")
            except Exception as e:
                logger.warning(f"Failed to delete {path}: {e}")
        
        # Also try to remove parent directory if it's empty and temporary
        if image_paths:
            parent_dir = image_paths[0].parent
            try:
                if parent_dir.name.startswith("pdf_convert_"):
                    parent_dir.rmdir()
                    logger.debug(f"Removed temporary directory: {parent_dir}")
            except Exception as e:
                logger.debug(f"Could not remove directory {parent_dir}: {e}")


def convert_pdf_to_png(
    pdf_path: Union[str, Path],
    output_dir: Optional[Union[str, Path]] = None,
    dpi: int = 300,
    max_pages: Optional[int] = None
) -> List[Path]:
    """Convenience function to convert PDF to PNG images.
    
    Args:
        pdf_path: Path to input PDF file
        output_dir: Directory to save converted images
        dpi: DPI resolution for images
        max_pages: Maximum number of pages to convert
        
    Returns:
        List of paths to converted PNG files
    """
    converter = PDFConverter(dpi=dpi, max_pages=max_pages)
    return converter.convert_pdf_to_images(pdf_path, output_dir)


def get_pdf_page_count(pdf_path: Union[str, Path]) -> int:
    """Get the number of pages in a PDF file.
    
    Args:
        pdf_path: Path to PDF file
        
    Returns:
        Number of pages in the PDF
    """
    converter = PDFConverter()
    info = converter.get_pdf_info(pdf_path)
    return info["pages"]
