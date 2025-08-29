"""Data models for OCR results and extraction."""

from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field, validator


class TextBox(BaseModel):
    """Represents a detected text box with coordinates and content."""
    
    coordinates: List[List[int]] = Field(
        ..., 
        description="Four corner coordinates of the text box [[x1,y1], [x2,y2], [x3,y3], [x4,y4]]"
    )
    text: str = Field(..., description="Extracted text content")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Recognition confidence score")
    
    @validator("coordinates")
    def validate_coordinates(cls, v: List[List[int]]) -> List[List[int]]:
        """Validate that coordinates form a proper quadrilateral."""
        if len(v) != 4:
            raise ValueError("Coordinates must have exactly 4 points")
        for point in v:
            if len(point) != 2:
                raise ValueError("Each coordinate point must have x,y values")
        return v

    @property
    def bbox(self) -> Tuple[int, int, int, int]:
        """Get bounding box as (x_min, y_min, x_max, y_max)."""
        x_coords = [point[0] for point in self.coordinates]
        y_coords = [point[1] for point in self.coordinates]
        return (min(x_coords), min(y_coords), max(x_coords), max(y_coords))

    @property
    def center(self) -> Tuple[float, float]:
        """Get center point of the text box."""
        x_coords = [point[0] for point in self.coordinates]
        y_coords = [point[1] for point in self.coordinates] 
        return (sum(x_coords) / 4, sum(y_coords) / 4)


class OCRResult(BaseModel):
    """Represents the complete OCR result for an image."""
    
    text_boxes: List[TextBox] = Field(default_factory=list, description="Detected text boxes")
    processing_time: float = Field(..., ge=0.0, description="Processing time in seconds")
    image_size: Tuple[int, int] = Field(..., description="Original image size (width, height)")
    
    @property
    def total_text(self) -> str:
        """Get all text concatenated with newlines."""
        return "\n".join(box.text for box in self.text_boxes)

    @property
    def text_count(self) -> int:
        """Get total number of detected text boxes."""
        return len(self.text_boxes)

    @property
    def average_confidence(self) -> float:
        """Get average confidence score across all text boxes."""
        if not self.text_boxes:
            return 0.0
        return sum(box.confidence for box in self.text_boxes) / len(self.text_boxes)
    
    def replace_text_boxes(self, text_boxes: List[TextBox]) -> None:
        self.text_boxes = text_boxes


class ExtractionResult(BaseModel):
    """Represents the final extraction result with structured data."""
    
    source_image: str = Field(..., description="Source image file path")
    ocr_result: OCRResult = Field(..., description="Raw OCR results")
    structured_data: Dict[str, Any] = Field(
        default_factory=dict, 
        description="Structured data extracted from OCR"
    )
    extraction_metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Metadata about the extraction process"
    )
    
    @property
    def success(self) -> bool:
        """Check if extraction was successful."""
        return len(self.ocr_result.text_boxes) > 0

    def to_json_dict(self) -> Dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "source_image": self.source_image,
            "success": self.success,
            "ocr_summary": {
                "text_count": self.ocr_result.text_count,
                "average_confidence": self.ocr_result.average_confidence,
                "processing_time": self.ocr_result.processing_time,
                "image_size": self.ocr_result.image_size,
            },
            "text_boxes": [
                {
                    "text": box.text,
                    "confidence": box.confidence,
                    "coordinates": box.coordinates,
                    "bbox": box.bbox,
                    "center": box.center,
                }
                for box in self.ocr_result.text_boxes
            ],
            "structured_data": self.structured_data,
            "extraction_metadata": self.extraction_metadata,
        }
