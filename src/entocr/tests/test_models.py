"""Tests for data models."""

from typing import TYPE_CHECKING
import pytest
from pydantic import ValidationError

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureRequest

from src.entocr.models import TextBox, OCRResult, ExtractionResult


class TestTextBox:
    """Test cases for TextBox model."""

    def test_textbox_creation_valid(self) -> None:
        """Test creating a valid TextBox."""
        coordinates = [[10, 10], [100, 10], [100, 30], [10, 30]]
        text = "Sample text"
        confidence = 0.95
        
        text_box = TextBox(
            coordinates=coordinates,
            text=text,
            confidence=confidence
        )
        
        assert text_box.coordinates == coordinates
        assert text_box.text == text
        assert text_box.confidence == confidence

    def test_textbox_bbox_property(self) -> None:
        """Test bbox property calculation."""
        coordinates = [[20, 15], [120, 15], [120, 35], [20, 35]]
        text_box = TextBox(coordinates=coordinates, text="test", confidence=0.9)
        
        bbox = text_box.bbox
        assert bbox == (20, 15, 120, 35)  # (x_min, y_min, x_max, y_max)

    def test_textbox_center_property(self) -> None:
        """Test center property calculation."""
        coordinates = [[20, 20], [60, 20], [60, 40], [20, 40]]
        text_box = TextBox(coordinates=coordinates, text="test", confidence=0.9)
        
        center = text_box.center
        assert center == (40.0, 30.0)  # ((20+60+60+20)/4, (20+20+40+40)/4)

    def test_textbox_invalid_coordinates_count(self) -> None:
        """Test validation error for wrong number of coordinates."""
        with pytest.raises(ValidationError):
            TextBox(
                coordinates=[[10, 10], [100, 10], [100, 30]],  # Only 3 points
                text="test",
                confidence=0.9
            )

    def test_textbox_invalid_coordinate_format(self) -> None:
        """Test validation error for invalid coordinate format."""
        with pytest.raises(ValidationError):
            TextBox(
                coordinates=[[10, 10, 5], [100, 10], [100, 30], [10, 30]],  # 3D point
                text="test",
                confidence=0.9
            )

    def test_textbox_invalid_confidence(self) -> None:
        """Test validation error for invalid confidence values."""
        coordinates = [[10, 10], [100, 10], [100, 30], [10, 30]]
        
        # Test confidence > 1.0
        with pytest.raises(ValidationError):
            TextBox(coordinates=coordinates, text="test", confidence=1.5)
        
        # Test confidence < 0.0
        with pytest.raises(ValidationError):
            TextBox(coordinates=coordinates, text="test", confidence=-0.1)


class TestOCRResult:
    """Test cases for OCRResult model."""

    def test_ocr_result_creation(self) -> None:
        """Test creating a valid OCRResult."""
        text_boxes = [
            TextBox(
                coordinates=[[10, 10], [100, 10], [100, 30], [10, 30]],
                text="Test text 1",
                confidence=0.95
            ),
            TextBox(
                coordinates=[[10, 40], [100, 40], [100, 60], [10, 60]],
                text="Test text 2",
                confidence=0.88
            )
        ]
        
        ocr_result = OCRResult(
            text_boxes=text_boxes,
            processing_time=2.5,
            image_size=(800, 600)
        )
        
        assert len(ocr_result.text_boxes) == 2
        assert ocr_result.processing_time == 2.5
        assert ocr_result.image_size == (800, 600)

    def test_total_text_property(self) -> None:
        """Test total_text property concatenates all text."""
        text_boxes = [
            TextBox(
                coordinates=[[10, 10], [100, 10], [100, 30], [10, 30]],
                text="Line 1",
                confidence=0.95
            ),
            TextBox(
                coordinates=[[10, 40], [100, 40], [100, 60], [10, 60]],
                text="Line 2",
                confidence=0.88
            )
        ]
        
        ocr_result = OCRResult(
            text_boxes=text_boxes,
            processing_time=1.0,
            image_size=(200, 100)
        )
        
        assert ocr_result.total_text == "Line 1\nLine 2"

    def test_text_count_property(self) -> None:
        """Test text_count property returns correct count."""
        text_boxes = [
            TextBox(
                coordinates=[[10, 10], [100, 10], [100, 30], [10, 30]],
                text="Text 1",
                confidence=0.95
            ),
            TextBox(
                coordinates=[[10, 40], [100, 40], [100, 60], [10, 60]],
                text="Text 2",
                confidence=0.88
            )
        ]
        
        ocr_result = OCRResult(
            text_boxes=text_boxes,
            processing_time=1.0,
            image_size=(200, 100)
        )
        
        assert ocr_result.text_count == 2

    def test_average_confidence_property(self) -> None:
        """Test average_confidence property calculation."""
        text_boxes = [
            TextBox(
                coordinates=[[10, 10], [100, 10], [100, 30], [10, 30]],
                text="Text 1",
                confidence=0.9
            ),
            TextBox(
                coordinates=[[10, 40], [100, 40], [100, 60], [10, 60]],
                text="Text 2",
                confidence=0.8
            )
        ]
        
        ocr_result = OCRResult(
            text_boxes=text_boxes,
            processing_time=1.0,
            image_size=(200, 100)
        )
        
        assert ocr_result.average_confidence == 0.85

    def test_average_confidence_empty(self) -> None:
        """Test average_confidence property with no text boxes."""
        ocr_result = OCRResult(
            text_boxes=[],
            processing_time=1.0,
            image_size=(200, 100)
        )
        
        assert ocr_result.average_confidence == 0.0


class TestExtractionResult:
    """Test cases for ExtractionResult model."""

    def test_extraction_result_creation(self) -> None:
        """Test creating a valid ExtractionResult."""
        text_box = TextBox(
            coordinates=[[10, 10], [100, 10], [100, 30], [10, 30]],
            text="Test text",
            confidence=0.95
        )
        
        ocr_result = OCRResult(
            text_boxes=[text_box],
            processing_time=1.5,
            image_size=(400, 300)
        )
        
        structured_data = {"key": "value"}
        metadata = {"processed": True}
        
        extraction_result = ExtractionResult(
            source_image="test.jpg",
            ocr_result=ocr_result,
            structured_data=structured_data,
            extraction_metadata=metadata
        )
        
        assert extraction_result.source_image == "test.jpg"
        assert extraction_result.ocr_result == ocr_result
        assert extraction_result.structured_data == structured_data
        assert extraction_result.extraction_metadata == metadata

    def test_success_property_true(self) -> None:
        """Test success property returns True when text is detected."""
        text_box = TextBox(
            coordinates=[[10, 10], [100, 10], [100, 30], [10, 30]],
            text="Test text",
            confidence=0.95
        )
        
        ocr_result = OCRResult(
            text_boxes=[text_box],
            processing_time=1.5,
            image_size=(400, 300)
        )
        
        extraction_result = ExtractionResult(
            source_image="test.jpg",
            ocr_result=ocr_result
        )
        
        assert extraction_result.success is True

    def test_success_property_false(self) -> None:
        """Test success property returns False when no text is detected."""
        ocr_result = OCRResult(
            text_boxes=[],
            processing_time=1.5,
            image_size=(400, 300)
        )
        
        extraction_result = ExtractionResult(
            source_image="test.jpg",
            ocr_result=ocr_result
        )
        
        assert extraction_result.success is False

    def test_to_json_dict(self) -> None:
        """Test to_json_dict method."""
        text_box = TextBox(
            coordinates=[[10, 10], [100, 10], [100, 30], [10, 30]],
            text="Test text",
            confidence=0.95
        )
        
        ocr_result = OCRResult(
            text_boxes=[text_box],
            processing_time=1.5,
            image_size=(400, 300)
        )
        
        structured_data = {"key": "value"}
        metadata = {"processed": True}
        
        extraction_result = ExtractionResult(
            source_image="test.jpg",
            ocr_result=ocr_result,
            structured_data=structured_data,
            extraction_metadata=metadata
        )
        
        json_dict = extraction_result.to_json_dict()
        
        assert json_dict["source_image"] == "test.jpg"
        assert json_dict["success"] is True
        assert json_dict["structured_data"] == structured_data
        assert json_dict["extraction_metadata"] == metadata
        assert "ocr_summary" in json_dict
        assert "text_boxes" in json_dict
        assert len(json_dict["text_boxes"]) == 1
