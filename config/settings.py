"""Application settings and configuration management."""

import os
from typing import List, Optional

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # OCR Configuration
    ocr_language: str = Field(default="korean", env="OCR_LANGUAGE")
    ocr_use_angle_cls: bool = Field(default=True, env="OCR_USE_ANGLE_CLS") 
    ocr_use_gpu: bool = Field(default=False, env="OCR_USE_GPU")
    ocr_det_limit_side_len: int = Field(default=960, env="OCR_DET_LIMIT_SIDE_LEN")
    ocr_rec_batch_num: int = Field(default=6, env="OCR_REC_BATCH_NUM")

    # Logging Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="logs/entocr.log", env="LOG_FILE")

    # Output Configuration
    output_format: str = Field(default="json", env="OUTPUT_FORMAT")
    output_indent: int = Field(default=2, env="OUTPUT_INDENT")
    output_ensure_ascii: bool = Field(default=False, env="OUTPUT_ENSURE_ASCII")

    # Image Processing Configuration
    max_image_size: int = Field(default=2048, env="MAX_IMAGE_SIZE")
    supported_formats: str = Field(default="jpg,jpeg,png,bmp,tiff", env="SUPPORTED_FORMATS")

    # Application Configuration
    debug: bool = Field(default=False, env="DEBUG")

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level value."""
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        if v.upper() not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v.upper()

    @field_validator("output_format")
    @classmethod
    def validate_output_format(cls, v: str) -> str:
        """Validate output format value."""
        valid_formats = ["json"]
        if v.lower() not in valid_formats:
            raise ValueError(f"Output format must be one of {valid_formats}")
        return v.lower()

    @property
    def supported_formats_list(self) -> List[str]:
        """Get supported image formats as a list."""
        return [fmt.strip().lower() for fmt in self.supported_formats.split(",")]

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# Global settings instance
settings = Settings()
