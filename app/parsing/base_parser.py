"""Abstract base class for protocol file parsers.

This module defines the interface that all protocol parsers must implement,
ensuring consistency and enabling polymorphic behavior across different file formats.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from app.core.exceptions import FileParsingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class BaseParser(ABC):
    """Abstract base class for protocol file parsers.
    
    All concrete parser implementations (PDF, DOCX, JSON) must inherit from this class
    and implement the required abstract methods. This ensures a consistent interface
    for parsing different file formats.
    
    Attributes:
        supported_extensions: List of file extensions this parser can handle.
        supported_mime_types: List of MIME types this parser can handle.
    """
    
    def __init__(self) -> None:
        """Initialize the parser."""
        self._logger = get_logger(self.__class__.__name__)
    
    @property
    @abstractmethod
    def supported_extensions(self) -> List[str]:
        """Return list of supported file extensions (e.g., ['.pdf', '.PDF']).
        
        Returns:
            List of file extensions this parser supports.
        """
        pass
    
    @property
    @abstractmethod
    def supported_mime_types(self) -> List[str]:
        """Return list of supported MIME types.
        
        Returns:
            List of MIME types this parser supports.
        """
        pass
    
    @property
    @abstractmethod
    def parser_name(self) -> str:
        """Return the name of this parser.
        
        Returns:
            Human-readable name of the parser.
        """
        pass
    
    @abstractmethod
    def parse(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Parse the file and extract structured protocol data.
        
        This is the main method that concrete parsers must implement. It should:
        1. Validate the input
        2. Extract text/data from the file
        3. Structure the data into a consistent format
        4. Handle errors gracefully
        
        Args:
            file_bytes: The file content as bytes.
            filename: The original filename (for logging and error reporting).
        
        Returns:
            Dictionary containing structured protocol data with keys:
                - protocol_id: str
                - title: str
                - phase: str
                - therapeutic_area: str
                - target_enrollment: int
                - duration_months: int
                - primary_endpoints: List[str]
                - inclusion_criteria: List[str]
                - exclusion_criteria: List[str]
                - source: str (file format)
                - filename: str
                - raw_text_length: int (optional)
        
        Raises:
            FileParsingError: When the file cannot be parsed.
        """
        pass
    
    def validate_input(self, file_bytes: bytes, filename: str) -> None:
        """Validate input parameters before parsing.
        
        Args:
            file_bytes: The file content to validate.
            filename: The filename to validate.
        
        Raises:
            FileParsingError: If validation fails.
        """
        if not file_bytes:
            raise FileParsingError(
                "Empty file provided.",
                details={"filename": filename, "parser": self.parser_name}
            )
        
        if not filename:
            raise FileParsingError(
                "Filename is required.",
                details={"parser": self.parser_name}
            )
        
        self._logger.debug(
            "[%s] Validated input — filename=%s, size=%d bytes",
            self.parser_name,
            filename,
            len(file_bytes)
        )
    
    def can_parse(self, filename: str, mime_type: Optional[str] = None) -> bool:
        """Check if this parser can handle the given file.
        
        Args:
            filename: The filename to check.
            mime_type: Optional MIME type to check.
        
        Returns:
            True if this parser can handle the file, False otherwise.
        """
        # Check file extension
        if any(filename.lower().endswith(ext.lower()) for ext in self.supported_extensions):
            return True
        
        # Check MIME type if provided
        if mime_type and mime_type in self.supported_mime_types:
            return True
        
        return False
    
    def _create_default_protocol_data(self, filename: str, source: str) -> Dict[str, Any]:
        """Create a default protocol data structure.
        
        This provides a consistent baseline structure that all parsers can extend.
        
        Args:
            filename: The original filename.
            source: The source format (pdf, docx, json).
        
        Returns:
            Dictionary with default protocol structure.
        """
        return {
            "protocol_id": "UNKNOWN",
            "title": f"Protocol from {filename}",
            "phase": "Unknown",
            "therapeutic_area": "Unknown",
            "target_enrollment": 0,
            "duration_months": 0,
            "primary_endpoints": [],
            "inclusion_criteria": [],
            "exclusion_criteria": [],
            "source": source,
            "filename": filename
        }
    
    def __repr__(self) -> str:
        """Return string representation of the parser."""
        return f"{self.__class__.__name__}(name='{self.parser_name}')"
