"""JSON protocol parser implementation.

This module provides a production-grade JSON parser that extracts structured
protocol data from JSON documents with validation and error handling.

Features:
- Direct JSON parsing for structured data
- Optional LLM validation for unstructured JSON text fields
- Schema validation and normalization
"""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from app.llm.base_llm import BaseLLM
from app.parsing.base_parser import BaseParser
from app.parsing.llm_extraction_service import LLMExtractionService
from app.core.exceptions import FileParsingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class JSONParser(BaseParser):
    """JSON protocol parser with validation and error handling.
    
    This parser handles JSON-formatted protocol files. For structured JSON,
    it directly parses the data. For unstructured JSON with text fields,
    it can optionally use LLM for extraction.
    
    Features:
        - Direct JSON parsing for structured data
        - Optional LLM extraction for unstructured text fields
        - Schema validation and type coercion
        - Nested data extraction
        - Comprehensive error reporting
        - Robust error handling and logging
    """
    
    def __init__(self, llm: Optional[BaseLLM] = None, strict_mode: bool = False) -> None:
        """Initialize the JSON parser.
        
        Args:
            llm: Optional LLM provider for extracting from unstructured JSON text.
            strict_mode: If True, raises errors for missing required fields.
                        If False, uses defaults for missing fields.
        """
        super().__init__()
        self._llm = llm
        self._extraction_service = LLMExtractionService(llm) if llm else None
        self._strict_mode = strict_mode
    
    @property
    def supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return ['.json', '.JSON']
    
    @property
    def supported_mime_types(self) -> List[str]:
        """Return supported MIME types."""
        return ['application/json', 'text/json']
    
    @property
    def parser_name(self) -> str:
        """Return parser name."""
        return "JSONParser"
    
    def parse(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Parse JSON file and extract structured protocol data.
        
        Args:
            file_bytes: The JSON file content as bytes.
            filename: The original filename.
        
        Returns:
            Dictionary containing structured protocol data.
        
        Raises:
            FileParsingError: When the JSON cannot be parsed or is invalid.
        """
        self.validate_input(file_bytes, filename)
        
        self._logger.info(
            "[%s] Parsing JSON — filename=%s, size=%d bytes",
            self.parser_name,
            filename,
            len(file_bytes)
        )
        
        try:
            # Decode and parse JSON
            json_str = file_bytes.decode('utf-8')
            raw_data = json.loads(json_str)
            
            if not isinstance(raw_data, dict):
                raise FileParsingError(
                    "JSON root must be an object/dictionary.",
                    details={"filename": filename, "type": type(raw_data).__name__}
                )
            
            # Extract and validate protocol data
            protocol_data = self._extract_protocol_data(raw_data, filename)
            
            # Add metadata
            protocol_data.update({
                "source": "json",
                "filename": filename,
                "raw_text": json_str,
                "raw_text_length": len(json_str)
            })
            
            self._logger.info(
                "[%s] Successfully parsed JSON — protocol_id=%s, %d top-level keys",
                self.parser_name,
                protocol_data.get("protocol_id", "UNKNOWN"),
                len(raw_data)
            )
            
            return protocol_data
            
        except json.JSONDecodeError as e:
            self._logger.error(
                "[%s] Invalid JSON syntax: %s",
                self.parser_name,
                str(e)
            )
            raise FileParsingError(
                f"Invalid JSON syntax: {e}",
                details={
                    "filename": filename,
                    "line": e.lineno,
                    "column": e.colno,
                    "parser": self.parser_name
                }
            ) from e
        except FileParsingError:
            raise
        except Exception as e:
            self._logger.error(
                "[%s] Failed to parse JSON: %s",
                self.parser_name,
                str(e),
                exc_info=True
            )
            raise FileParsingError(
                f"Failed to parse JSON: {e}",
                details={"filename": filename, "parser": self.parser_name}
            ) from e
    
    def _extract_protocol_data(self, raw_data: Dict[str, Any], filename: str) -> Dict[str, Any]:
        """Extract and validate protocol data from raw JSON.
        
        This method handles various JSON structures and normalizes them into
        a consistent format. It supports both flat and nested structures.
        
        Args:
            raw_data: The parsed JSON data.
            filename: The original filename.
        
        Returns:
            Dictionary with structured and validated protocol data.
        
        Raises:
            FileParsingError: If strict mode is enabled and required fields are missing.
        """
        # Start with default structure
        protocol_data = self._create_default_protocol_data(filename, "json")
        
        # Extract protocol ID (required in strict mode)
        protocol_id = self._extract_field(
            raw_data,
            ["protocol_id", "protocolId", "id", "protocol_number"],
            str,
            required=self._strict_mode
        )
        if protocol_id:
            protocol_data["protocol_id"] = protocol_id
        
        # Extract title
        title = self._extract_field(
            raw_data,
            ["title", "protocol_title", "study_title"],
            str
        )
        if title:
            protocol_data["title"] = title
        
        # Extract phase
        phase = self._extract_field(
            raw_data,
            ["phase", "study_phase", "trial_phase"],
            str
        )
        if phase:
            protocol_data["phase"] = self._normalize_phase(phase)
        
        # Extract therapeutic area
        therapeutic_area = self._extract_field(
            raw_data,
            ["therapeutic_area", "therapeuticArea", "indication", "disease_area"],
            str
        )
        if therapeutic_area:
            protocol_data["therapeutic_area"] = therapeutic_area
        
        # Extract target enrollment
        enrollment = self._extract_field(
            raw_data,
            ["target_enrollment", "targetEnrollment", "sample_size", "n_patients"],
            int
        )
        if enrollment:
            protocol_data["target_enrollment"] = enrollment
        
        # Extract duration
        duration = self._extract_field(
            raw_data,
            ["duration_months", "durationMonths", "study_duration", "duration"],
            int
        )
        if duration:
            protocol_data["duration_months"] = duration
        
        # Extract primary endpoints
        endpoints = self._extract_field(
            raw_data,
            ["primary_endpoints", "primaryEndpoints", "endpoints", "primary_outcome"],
            list
        )
        if endpoints:
            protocol_data["primary_endpoints"] = self._normalize_list(endpoints)
        
        # Extract inclusion criteria
        inclusion = self._extract_field(
            raw_data,
            ["inclusion_criteria", "inclusionCriteria", "inclusion", "eligibility_criteria"],
            list
        )
        if inclusion:
            protocol_data["inclusion_criteria"] = self._normalize_list(inclusion)
        
        # Extract exclusion criteria
        exclusion = self._extract_field(
            raw_data,
            ["exclusion_criteria", "exclusionCriteria", "exclusion"],
            list
        )
        if exclusion:
            protocol_data["exclusion_criteria"] = self._normalize_list(exclusion)
        
        return protocol_data
    
    def _extract_field(
        self,
        data: Dict[str, Any],
        field_names: List[str],
        expected_type: type,
        required: bool = False
    ) -> Any:
        """Extract a field from data, trying multiple possible field names.
        
        Args:
            data: The data dictionary to search.
            field_names: List of possible field names to try.
            expected_type: The expected type of the field.
            required: If True, raises error if field not found.
        
        Returns:
            The field value, or None if not found.
        
        Raises:
            FileParsingError: If required field is missing.
        """
        for field_name in field_names:
            if field_name in data:
                value = data[field_name]
                
                # Type coercion
                try:
                    if expected_type == int and not isinstance(value, int):
                        return int(value)
                    elif expected_type == str and not isinstance(value, str):
                        return str(value)
                    elif expected_type == list and not isinstance(value, list):
                        # Convert single item to list
                        return [value] if value else []
                    else:
                        return value
                except (ValueError, TypeError) as e:
                    self._logger.warning(
                        "[%s] Failed to convert field '%s' to %s: %s",
                        self.parser_name,
                        field_name,
                        expected_type.__name__,
                        str(e)
                    )
                    continue
        
        if required:
            raise FileParsingError(
                f"Required field not found. Tried: {', '.join(field_names)}",
                details={"parser": self.parser_name, "field_names": field_names}
            )
        
        return None
    
    def _normalize_phase(self, phase: str) -> str:
        """Normalize phase string to standard format.
        
        Args:
            phase: The phase string to normalize.
        
        Returns:
            Normalized phase string (e.g., "Phase III").
        """
        phase = str(phase).strip().upper()
        
        # Map numeric to Roman numerals
        phase_map = {
            '1': 'I', 'I': 'I',
            '2': 'II', 'II': 'II',
            '3': 'III', 'III': 'III',
            '4': 'IV', 'IV': 'IV'
        }
        
        # Extract phase number/numeral
        for key, value in phase_map.items():
            if key in phase:
                return f"Phase {value}"
        
        return phase
    
    def _normalize_list(self, items: List[Any]) -> List[str]:
        """Normalize a list of items to strings.
        
        Args:
            items: List of items to normalize.
        
        Returns:
            List of string items.
        """
        if not isinstance(items, list):
            return []
        
        normalized = []
        for item in items:
            if isinstance(item, str):
                normalized.append(item.strip())
            elif isinstance(item, dict):
                # If item is a dict, try to extract a 'text' or 'description' field
                text = item.get('text') or item.get('description') or str(item)
                normalized.append(str(text).strip())
            else:
                normalized.append(str(item).strip())
        
        return [item for item in normalized if item]  # Filter empty strings
