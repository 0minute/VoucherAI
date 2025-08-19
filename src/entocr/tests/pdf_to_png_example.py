"""PDF to PNG conversion example script.

This script demonstrates how to use the PDF conversion functionality
to convert PDF documents to PNG images and then extract data using OCR.
"""

import sys
from pathlib import Path

# Add src directory to Python path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from loguru import logger
from entocr.pdf_converter import PDFConverter, convert_pdf_to_png
from entocr import ImageDataExtractor


def example_basic_pdf_conversion(pdf_path: str) -> None:
    """Basic PDF to PNG conversion example.
    
    Args:
        pdf_path: Path to PDF file
    """
    logger.info("=== Basic PDF Conversion Example ===")
    
    try:
        # Simple conversion using convenience function
        logger.info(f"Converting PDF: {pdf_path}")
        image_paths = convert_pdf_to_png(
            pdf_path,
            output_dir="output/pdf_images",
            dpi=300
        )
        
        logger.info(f"✅ Converted to {len(image_paths)} PNG images:")
        for i, path in enumerate(image_paths, 1):
            logger.info(f"  Page {i}: {path}")
            
    except Exception as e:
        logger.error(f"❌ Conversion failed: {e}")


def example_advanced_pdf_conversion(pdf_path: str) -> None:
    """Advanced PDF conversion with options.
    
    Args:
        pdf_path: Path to PDF file
    """
    logger.info("=== Advanced PDF Conversion Example ===")
    
    try:
        # Create converter with custom settings
        converter = PDFConverter(
            dpi=200,              # Lower DPI for faster processing
            output_format="PNG",
            max_pages=3           # Only convert first 3 pages
        )
        
        # Get PDF info first
        pdf_info = converter.get_pdf_info(pdf_path)
        logger.info(f"PDF Info: {pdf_info['pages']} pages, {pdf_info['file_size']} bytes")
        
        # Convert with custom settings
        logger.info(f"Converting first 3 pages at 200 DPI...")
        image_paths = converter.convert_pdf_to_images(
            pdf_path,
            output_dir="output/pdf_pages",
            filename_prefix="custom"
        )
        
        logger.info(f"✅ Converted {len(image_paths)} pages:")
        for path in image_paths:
            logger.info(f"  {path}")
        
        # Clean up temporary files
        logger.info("Cleaning up temporary files...")
        converter.cleanup_temp_files(image_paths)
        
    except Exception as e:
        logger.error(f"❌ Advanced conversion failed: {e}")


def example_pdf_to_json_extraction(pdf_path: str) -> None:
    """Complete PDF to JSON extraction example.
    
    Args:
        pdf_path: Path to PDF file
    """
    logger.info("=== PDF to JSON Extraction Example ===")
    
    try:
        # Initialize extractor
        extractor = ImageDataExtractor()
        
        # Extract data from PDF
        logger.info(f"Extracting data from PDF: {pdf_path}")
        json_result = extractor.extract_pdf_to_json(
            pdf_path,
            output_path="output/pdf_extracted.json",
            dpi=300,
            max_pages=2,        # Process only first 2 pages
            keep_images=True    # Keep the converted PNG files
        )
        
        logger.info("✅ PDF extraction completed!")
        logger.info("JSON result saved to: output/pdf_extracted.json")
        
        # Show brief summary
        import json
        data = json.loads(json_result)
        summary = data.get('summary', {})
        logger.info(f"Summary:")
        logger.info(f"  - Total pages processed: {summary.get('successful_pages', 0)}")
        logger.info(f"  - Total text boxes: {summary.get('total_text_boxes', 0)}")
        logger.info(f"  - Average confidence: {summary.get('average_confidence', 0):.3f}")
        
    except Exception as e:
        logger.error(f"❌ PDF extraction failed: {e}")


def example_auto_detection(file_path: str) -> None:
    """Auto file type detection example.
    
    Args:
        file_path: Path to file (image or PDF)
    """
    logger.info("=== Auto File Type Detection Example ===")
    
    try:
        extractor = ImageDataExtractor()
        
        # Auto-detect and process
        logger.info(f"Auto-processing file: {file_path}")
        json_result = extractor.auto_extract(
            file_path,
            output_path=f"output/{Path(file_path).stem}_auto_extracted.json",
            # PDF-specific options (ignored for images)
            dpi=300,
            max_pages=1,
            keep_images=False
        )
        
        logger.info("✅ Auto-processing completed!")
        
    except Exception as e:
        logger.error(f"❌ Auto-processing failed: {e}")


def main():
    """Main example function."""
    # Setup logging
    logger.remove()
    logger.add(sys.stderr, level="INFO")
    
    # Check if example PDF exists
    example_pdf = "input/example.pdf"  # You'll need to provide a PDF file here
    
    if not Path(example_pdf).exists():
        logger.warning(f"Example PDF not found: {example_pdf}")
        logger.info("Please place a PDF file in the input directory and update the path")
        logger.info("For now, we'll demonstrate the functions with placeholder paths")
        
        # Create output directories
        Path("output/pdf_images").mkdir(parents=True, exist_ok=True)
        Path("output/pdf_pages").mkdir(parents=True, exist_ok=True)
        
        logger.info("🔧 PDF Conversion Functions Available:")
        logger.info("1. convert_pdf_to_png() - Simple conversion")
        logger.info("2. PDFConverter class - Advanced options")
        logger.info("3. ImageDataExtractor.extract_pdf_to_json() - Full extraction")
        logger.info("4. ImageDataExtractor.auto_extract() - Auto file detection")
        
        logger.info("\n📖 Usage Examples:")
        logger.info("# Simple conversion")
        logger.info("from entocr.pdf_converter import convert_pdf_to_png")
        logger.info("images = convert_pdf_to_png('document.pdf', 'output/', dpi=300)")
        
        logger.info("\n# Full extraction")
        logger.info("from entocr import ImageDataExtractor")
        logger.info("extractor = ImageDataExtractor()")
        logger.info("json_data = extractor.extract_pdf_to_json('document.pdf')")
        
        logger.info("\n# CLI usage")
        logger.info("python -m entocr document.pdf --pdf-dpi 300 --keep-images")
        
        return
    
    try:
        # Run examples
        example_basic_pdf_conversion(example_pdf)
        example_advanced_pdf_conversion(example_pdf)
        example_pdf_to_json_extraction(example_pdf)
        example_auto_detection(example_pdf)
        
        logger.info("🎉 All examples completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Example execution failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
