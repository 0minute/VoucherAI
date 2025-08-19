"""Command line interface for the OCR data extraction tool."""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from loguru import logger

from config.settings import settings
from .extractor import ImageDataExtractor


def setup_logging(log_level: str, log_file: Optional[str] = None) -> None:
    """Set up logging configuration.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional log file path
    """
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stderr,
        level=log_level,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>"
    )
    
    # Add file logger if specified
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        
        logger.add(
            log_file,
            level=log_level,
            format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
            rotation="10 MB",
            retention="30 days"
        )


def process_single_file(
    file_path: str,
    output_path: Optional[str] = None,
    extractor: Optional[ImageDataExtractor] = None,
    pdf_dpi: int = 300,
    pdf_max_pages: Optional[int] = None,
    keep_images: bool = False
) -> bool:
    """Process a single file (image or PDF).
    
    Args:
        file_path: Path to the file (image or PDF)
        output_path: Optional output path for JSON file
        extractor: Optional extractor instance
        pdf_dpi: DPI for PDF conversion
        pdf_max_pages: Maximum pages to process from PDF
        keep_images: Keep converted images from PDF
        
    Returns:
        True if processing was successful, False otherwise
    """
    if extractor is None:
        extractor = ImageDataExtractor()
    
    try:
        file_path_obj = Path(file_path)
        
        if not output_path:
            output_path = file_path_obj.parent / f"{file_path_obj.stem}_extracted.json"
        
        logger.info(f"Processing file: {file_path}")
        
        # Auto-detect file type and process accordingly
        if extractor.is_pdf_file(file_path):
            json_result = extractor.extract_pdf_to_json(
                file_path, 
                output_path,
                dpi=pdf_dpi,
                max_pages=pdf_max_pages,
                keep_images=keep_images
            )
        else:
            json_result = extractor.extract_to_json(file_path, output_path)
        
        if not output_path:
            # Print to stdout if no output file specified
            print(json_result)
        
        logger.info(f"Successfully processed: {file_path}")
        return True
        
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}")
        return False


def process_multiple_files(
    file_paths: List[str],
    output_dir: str,
    extractor: Optional[ImageDataExtractor] = None,
    pdf_dpi: int = 300,
    pdf_max_pages: Optional[int] = None,
    keep_images: bool = False
) -> int:
    """Process multiple files (images or PDFs).
    
    Args:
        file_paths: List of file paths (images or PDFs)
        output_dir: Output directory for JSON files
        extractor: Optional extractor instance
        pdf_dpi: DPI for PDF conversion
        pdf_max_pages: Maximum pages to process from PDF
        keep_images: Keep converted images from PDF
        
    Returns:
        Number of successfully processed images
    """
    if extractor is None:
        extractor = ImageDataExtractor()
    
    try:
        logger.info(f"Processing {len(file_paths)} files to directory: {output_dir}")
        successful = 0
        
        for file_path in file_paths:
            try:
                file_path_obj = Path(file_path)
                output_path = Path(output_dir) / f"{file_path_obj.stem}_extracted.json"
                
                # Auto-detect file type and process accordingly
                if extractor.is_pdf_file(file_path):
                    extractor.extract_pdf_to_json(
                        file_path,
                        output_path,
                        dpi=pdf_dpi,
                        max_pages=pdf_max_pages,
                        keep_images=keep_images
                    )
                else:
                    extractor.extract_to_json(file_path, output_path)
                
                successful += 1
                logger.info(f"Processed: {file_path}")
                
            except Exception as e:
                logger.error(f"Failed to process {file_path}: {e}")
        
        logger.info(f"Successfully processed {successful}/{len(file_paths)} files")
        return successful
        
    except Exception as e:
        logger.error(f"Batch processing failed: {e}")
        return 0


def find_image_files(directory: str) -> List[str]:
    """Find all supported image and PDF files in a directory.
    
    Args:
        directory: Directory path to search
        
    Returns:
        List of image file paths
    """
    dir_path = Path(directory)
    if not dir_path.exists() or not dir_path.is_dir():
        logger.error(f"Directory not found: {directory}")
        return []
    
    files = []
    # Find image files
    for ext in settings.supported_formats_list:
        pattern = f"*.{ext}"
        files.extend(dir_path.glob(pattern))
        files.extend(dir_path.glob(pattern.upper()))
    
    # Find PDF files
    files.extend(dir_path.glob("*.pdf"))
    files.extend(dir_path.glob("*.PDF"))
    
    return [str(path) for path in sorted(files)]


def main() -> int:
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Extract structured data from images using OCR",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Process single image
  python -m entocr image.jpg
  
  # Process single image with custom output
  python -m entocr image.jpg -o output.json
  
  # Process all images in directory
  python -m entocr -d input_dir -O output_dir
  
  # Process multiple specific images
  python -m entocr image1.jpg image2.png -O output_dir
  
  # Set custom log level
  python -m entocr image.jpg --log-level DEBUG
        """
    )
    
    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "files",
        nargs="*",
        help="Image or PDF file(s) to process"
    )
    input_group.add_argument(
        "-d", "--directory",
        help="Directory containing images to process"
    )
    
    # Output options
    parser.add_argument(
        "-o", "--output",
        help="Output JSON file path (for single image only)"
    )
    parser.add_argument(
        "-O", "--output-dir",
        help="Output directory for JSON files (for multiple images)"
    )
    
    # Configuration options
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
        default=settings.log_level,
        help="Set logging level"
    )
    parser.add_argument(
        "--log-file",
        help="Log file path (default: logs to stderr only)"
    )
    parser.add_argument(
        "--language",
        default=settings.ocr_language,
        help="OCR language"
    )
    parser.add_argument(
        "--no-gpu",
        action="store_true",
        help="Disable GPU acceleration"
    )
    
    # PDF-specific options
    parser.add_argument(
        "--pdf-dpi",
        type=int,
        default=300,
        help="DPI for PDF to image conversion (default: 300)"
    )
    parser.add_argument(
        "--pdf-max-pages",
        type=int,
        help="Maximum number of PDF pages to process"
    )
    parser.add_argument(
        "--keep-images",
        action="store_true",
        help="Keep converted PNG files from PDF processing"
    )
    
    args = parser.parse_args()
    
    # Setup logging
    setup_logging(args.log_level, args.log_file)
    
    # Determine input files
    if args.directory:
        file_paths = find_image_files(args.directory)  # This will need to be updated to handle PDFs too
        if not file_paths:
            logger.error(f"No supported files found in: {args.directory}")
            return 1
        logger.info(f"Found {len(file_paths)} files in directory")
    else:
        file_paths = args.files
        if not file_paths:
            logger.error("No input files specified")
            return 1
    
    # Validate input files exist
    for file_path in file_paths:
        if not Path(file_path).exists():
            logger.error(f"Input file not found: {file_path}")
            return 1
    
    # Initialize extractor
    try:
        from .ocr_service import OCRService
        ocr_service = OCRService(
            language=args.language,
            use_gpu=not args.no_gpu if hasattr(args, 'no_gpu') else False
        )
        extractor = ImageDataExtractor(ocr_service)
    except Exception as e:
        logger.error(f"Failed to initialize OCR service: {e}")
        return 1
    
    # Process files (images or PDFs)
    if len(file_paths) == 1 and not args.output_dir:
        # Single file processing
        success = process_single_file(
            file_paths[0],
            args.output,
            extractor,
            pdf_dpi=args.pdf_dpi,
            pdf_max_pages=args.pdf_max_pages,
            keep_images=args.keep_images
        )
        return 0 if success else 1
    else:
        # Multiple file processing
        output_dir = args.output_dir or "output"
        successful = process_multiple_files(
            file_paths,
            output_dir,
            extractor,
            pdf_dpi=args.pdf_dpi,
            pdf_max_pages=args.pdf_max_pages,
            keep_images=args.keep_images
        )
        
        total = len(file_paths)
        logger.info(f"Processing completed: {successful}/{total} files successful")
        return 0 if successful == total else 1


if __name__ == "__main__":
    sys.exit(main())
