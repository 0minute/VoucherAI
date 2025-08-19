"""Tests for the ImageDataExtractor class."""

from typing import TYPE_CHECKING
import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureRequest
    from pytest_mock.plugin import MockerFixture

from src.entocr.extractor import ImageDataExtractor
from src.entocr.models import ExtractionResult, OCRResult, TextBox


class TestImageDataExtractor:
    """Test cases for ImageDataExtractor class."""

    def test_init_with_ocr_service(self, mock_ocr_service) -> None:
        """Test initialization with provided OCR service."""
        extractor = ImageDataExtractor(ocr_service=mock_ocr_service)
        assert extractor.ocr_service == mock_ocr_service

    def test_init_without_ocr_service(self) -> None:
        """Test initialization without OCR service creates one."""
        with patch('src.entocr.extractor.OCRService') as mock_service_class:
            extractor = ImageDataExtractor()
            mock_service_class.assert_called_once()
            assert extractor.ocr_service == mock_service_class.return_value

    def test_extract_key_value_pairs(self, image_extractor) -> None:
        """Test extraction of key-value pairs from text boxes."""
        text_boxes = [
            TextBox(
                coordinates=[[20, 20], [150, 20], [150, 40], [20, 40]],
                text="Name: John Doe",
                confidence=0.95
            ),
            TextBox(
                coordinates=[[20, 50], [150, 50], [150, 70], [20, 70]],
                text="Email: john@example.com",
                confidence=0.92
            ),
            TextBox(
                coordinates=[[20, 80], [80, 80], [80, 100], [20, 100]],
                text="Phone:",
                confidence=0.90
            ),
            TextBox(
                coordinates=[[90, 80], [180, 80], [180, 100], [90, 100]],
                text="123-456-7890",
                confidence=0.88
            )
        ]
        
        result = image_extractor._extract_key_value_pairs(text_boxes)
        
        assert "Name" in result
        assert result["Name"] == "John Doe"
        assert "Email" in result
        assert result["Email"] == "john@example.com"
        assert "Phone" in result
        assert result["Phone"] == "123-456-7890"

    def test_extract_tables(self, image_extractor) -> None:
        """Test extraction of table structures."""
        # Create text boxes that form a table
        text_boxes = [
            # Header row
            TextBox(coordinates=[[20, 20], [80, 20], [80, 40], [20, 40]], text="Name", confidence=0.95),
            TextBox(coordinates=[[100, 20], [160, 20], [160, 40], [100, 40]], text="Age", confidence=0.95),
            TextBox(coordinates=[[180, 20], [240, 20], [240, 40], [180, 40]], text="City", confidence=0.95),
            
            # Data row 1
            TextBox(coordinates=[[20, 50], [80, 50], [80, 70], [20, 70]], text="John", confidence=0.90),
            TextBox(coordinates=[[100, 50], [160, 50], [160, 70], [100, 70]], text="25", confidence=0.90),
            TextBox(coordinates=[[180, 50], [240, 50], [240, 70], [180, 70]], text="NYC", confidence=0.90),
            
            # Data row 2
            TextBox(coordinates=[[20, 80], [80, 80], [80, 100], [20, 100]], text="Jane", confidence=0.88),
            TextBox(coordinates=[[100, 80], [160, 80], [160, 100], [100, 100]], text="30", confidence=0.88),
            TextBox(coordinates=[[180, 80], [240, 80], [240, 100], [180, 100]], text="LA", confidence=0.88),
        ]
        
        result = image_extractor._extract_tables(text_boxes)
        
        assert len(result) == 2
        assert result[0] == {"Name": "John", "Age": "25", "City": "NYC"}
        assert result[1] == {"Name": "Jane", "Age": "30", "City": "LA"}

    def test_extract_numbers_and_amounts(self, image_extractor) -> None:
        """Test extraction of numeric values and amounts."""
        text_boxes = [
            TextBox(
                coordinates=[[20, 20], [120, 20], [120, 40], [20, 40]],
                text="Total: $1,234.56",
                confidence=0.95
            ),
            TextBox(
                coordinates=[[20, 50], [120, 50], [120, 70], [20, 70]],
                text="Discount: 15%",
                confidence=0.90
            ),
            TextBox(
                coordinates=[[20, 80], [120, 80], [120, 100], [20, 100]],
                text="Quantity: 42",
                confidence=0.88
            )
        ]
        
        result = image_extractor._extract_numbers_and_amounts(text_boxes)
        
        # Check that we extracted some numeric values
        assert len(result) > 0
        
        # Check for currency patterns
        currency_found = any("$1,234.56" in str(value) for value in result.values())
        assert currency_found
        
        # Check for percentage patterns
        percentage_found = any("15%" in str(value) for value in result.values())
        assert percentage_found

    def test_extract_dates(self, image_extractor) -> None:
        """Test extraction of date patterns."""
        text_boxes = [
            TextBox(
                coordinates=[[20, 20], [120, 20], [120, 40], [20, 40]],
                text="Date: 2024-01-15",
                confidence=0.95
            ),
            TextBox(
                coordinates=[[20, 50], [120, 50], [120, 70], [20, 70]],
                text="Due: 12/25/2024",
                confidence=0.90
            ),
            TextBox(
                coordinates=[[20, 80], [120, 80], [120, 100], [20, 100]],
                text="Updated: 2024년 3월 10일",
                confidence=0.88
            )
        ]
        
        result = image_extractor._extract_dates(text_boxes)
        
        assert len(result) >= 2  # Should find at least the first two date patterns
        assert "2024-01-15" in result
        assert "12/25/2024" in result

    def test_analyze_layout(self, image_extractor) -> None:
        """Test layout analysis functionality."""
        text_boxes = [
            TextBox(
                coordinates=[[20, 20], [120, 20], [120, 40], [20, 40]],
                text="Header",
                confidence=0.95
            ),
            TextBox(
                coordinates=[[20, 60], [120, 60], [120, 80], [20, 80]],
                text="Content",
                confidence=0.90
            )
        ]
        
        result = image_extractor._analyze_layout(text_boxes)
        
        assert "document_bounds" in result
        assert "text_density" in result
        assert "avg_confidence" in result
        assert "text_sizes" in result
        
        assert result["text_density"] == 2
        assert result["avg_confidence"] == 0.925  # (0.95 + 0.90) / 2

    def test_extract_from_image_success(self, image_extractor, sample_image_path, mock_ocr_result) -> None:
        """Test successful image extraction."""
        result = image_extractor.extract_from_image(sample_image_path)
        
        assert isinstance(result, ExtractionResult)
        assert result.source_image == str(sample_image_path)
        assert result.success is True
        assert "key_value_pairs" in result.structured_data
        assert "tables" in result.structured_data
        assert "numbers_and_amounts" in result.structured_data
        assert "dates" in result.structured_data
        assert "raw_text_lines" in result.structured_data
        assert "layout_analysis" in result.structured_data

    def test_extract_from_image_no_text(self, image_extractor, sample_image_path) -> None:
        """Test extraction when no text is detected."""
        # Mock OCR service to return empty result
        empty_ocr_result = OCRResult(
            text_boxes=[],
            processing_time=1.0,
            image_size=(400, 300)
        )
        image_extractor.ocr_service.extract_text.return_value = empty_ocr_result
        
        result = image_extractor.extract_from_image(sample_image_path)
        
        assert isinstance(result, ExtractionResult)
        assert result.success is False
        assert result.extraction_metadata["processing_successful"] is False
        assert "No text detected" in result.extraction_metadata["error"]

    def test_extract_to_json_with_output_path(self, image_extractor, sample_image_path, temp_dir) -> None:
        """Test extraction to JSON with output file."""
        output_path = temp_dir / "test_output.json"
        
        json_result = image_extractor.extract_to_json(sample_image_path, output_path)
        
        # Check that JSON string is returned
        assert isinstance(json_result, str)
        parsed_json = json.loads(json_result)
        assert "source_image" in parsed_json
        
        # Check that file was created
        assert output_path.exists()
        
        # Check file contents
        with open(output_path, 'r', encoding='utf-8') as f:
            file_content = f.read()
        
        assert file_content == json_result

    def test_extract_to_json_without_output_path(self, image_extractor, sample_image_path) -> None:
        """Test extraction to JSON without output file."""
        json_result = image_extractor.extract_to_json(sample_image_path)
        
        # Check that JSON string is returned
        assert isinstance(json_result, str)
        parsed_json = json.loads(json_result)
        assert "source_image" in parsed_json

    def test_batch_extract_to_json(self, image_extractor, sample_image_path, temp_dir) -> None:
        """Test batch extraction to JSON files."""
        image_paths = [sample_image_path, sample_image_path]  # Use same image twice for testing
        
        results = image_extractor.batch_extract_to_json(image_paths, temp_dir)
        
        assert len(results) == 2
        assert all(isinstance(result, str) for result in results)
        
        # Check that JSON files were created
        json_files = list(temp_dir.glob("*.json"))
        assert len(json_files) == 2

    def test_custom_processors(self, image_extractor, sample_image_path) -> None:
        """Test extraction with custom processors."""
        def custom_processor(text_boxes):
            """Custom processor that counts words."""
            total_words = sum(len(box.text.split()) for box in text_boxes)
            return {"custom_word_count": total_words}
        
        def failing_processor(text_boxes):
            """Custom processor that raises an exception."""
            raise ValueError("Test error")
        
        custom_processors = [custom_processor, failing_processor]
        
        result = image_extractor.extract_from_image(sample_image_path, custom_processors)
        
        # Should include custom data from successful processor
        assert "custom_word_count" in result.structured_data
        assert isinstance(result.structured_data["custom_word_count"], int)
        
        # Should handle failing processor gracefully
        assert result.success is True  # Extraction should still succeed
