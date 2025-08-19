"""Pytest configuration and shared fixtures."""

from typing import TYPE_CHECKING
import pytest
from pathlib import Path
import tempfile
import shutil
from unittest.mock import Mock

if TYPE_CHECKING:
    from _pytest.fixtures import FixtureRequest
    from _pytest.capture import CaptureFixture
    from _pytest.logging import LogCaptureFixture
    from _pytest.monkeypatch import MonkeyPatch
    from pytest_mock.plugin import MockerFixture

# Test data directory
TEST_DATA_DIR = Path(__file__).parent / "test_data"


@pytest.fixture
def test_data_dir() -> Path:
    """Provide path to test data directory."""
    return TEST_DATA_DIR


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test outputs."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_image_path(test_data_dir: Path) -> Path:
    """Provide path to sample test image."""
    # Create test image if it doesn't exist
    sample_path = test_data_dir / "sample_test.png"
    if not sample_path.exists():
        test_data_dir.mkdir(exist_ok=True)
        # Create a simple test image using PIL
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a white image with some text
            img = Image.new('RGB', (400, 200), color='white')
            draw = ImageDraw.Draw(img)
            
            # Add some test text
            try:
                # Try to use a default font
                font = ImageFont.load_default()
            except:
                font = None
            
            draw.text((20, 20), "Test Document", fill='black', font=font)
            draw.text((20, 50), "Name: John Doe", fill='black', font=font)
            draw.text((20, 80), "Amount: $1,234.56", fill='black', font=font)
            draw.text((20, 110), "Date: 2024-01-15", fill='black', font=font)
            
            img.save(sample_path)
        except ImportError:
            # If PIL is not available, create empty file
            sample_path.touch()
    
    return sample_path


@pytest.fixture
def mock_ocr_result():
    """Provide a mock OCR result for testing."""
    from src.entocr.models import OCRResult, TextBox
    
    text_boxes = [
        TextBox(
            coordinates=[[20, 20], [150, 20], [150, 40], [20, 40]],
            text="Test Document",
            confidence=0.95
        ),
        TextBox(
            coordinates=[[20, 50], [120, 50], [120, 70], [20, 70]],
            text="Name: John Doe",
            confidence=0.92
        ),
        TextBox(
            coordinates=[[20, 80], [140, 80], [140, 100], [20, 100]],
            text="Amount: $1,234.56",
            confidence=0.88
        ),
        TextBox(
            coordinates=[[20, 110], [130, 110], [130, 130], [20, 130]],
            text="Date: 2024-01-15",
            confidence=0.91
        )
    ]
    
    return OCRResult(
        text_boxes=text_boxes,
        processing_time=1.5,
        image_size=(400, 200)
    )


@pytest.fixture
def mock_ocr_service(mock_ocr_result):
    """Provide a mock OCR service for testing."""
    from src.entocr.ocr_service import OCRService
    
    service = Mock(spec=OCRService)
    service.extract_text.return_value = mock_ocr_result
    service.batch_extract_text.return_value = [mock_ocr_result]
    
    return service


@pytest.fixture
def image_extractor(mock_ocr_service):
    """Provide an ImageDataExtractor with mocked OCR service."""
    from src.entocr.extractor import ImageDataExtractor
    
    return ImageDataExtractor(ocr_service=mock_ocr_service)
