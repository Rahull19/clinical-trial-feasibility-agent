"""LLM-powered extraction service for robust protocol data extraction.

This service uses LLMs to extract structured data from unstructured text,
making it robust to any format, layout, or structure variations.
"""

from __future__ import annotations

import json
from typing import Any, Dict, Optional

from app.llm.base_llm import BaseLLM
from app.prompts.extraction_prompts import get_protocol_extraction_prompt
from app.core.logging import get_logger

logger = get_logger(__name__)


class LLMExtractionService:
    """Service for extracting structured protocol data using LLMs.
    
    This service provides robust extraction that works with any text format
    by leveraging LLM's natural language understanding capabilities.
    """
    
    def __init__(self, llm: Optional[BaseLLM] = None) -> None:
        """Initialize the extraction service.
        
        Args:
            llm: Optional LLM provider. If None, extraction will fail gracefully.
        """
        self._llm = llm
        self._logger = get_logger(self.__class__.__name__)
    
    def extract_protocol_data(self, text: str, filename: str) -> Dict[str, Any]:
        """Extract structured protocol data from text using LLM.
        
        Args:
            text: The raw text extracted from the document.
            filename: The original filename for context.
        
        Returns:
            Dictionary with structured protocol data.
        """
        if not self._llm:
            self._logger.warning(
                "[LLMExtractionService] No LLM provided, cannot extract data"
            )
            return self._create_empty_protocol(filename)
        
        if not text or len(text.strip()) < 50:
            self._logger.warning(
                "[LLMExtractionService] Text too short for extraction: %d chars",
                len(text)
            )
            return self._create_empty_protocol(filename)
        
        try:
            self._logger.info(
                "[LLMExtractionService] Extracting protocol data using %s",
                self._llm.provider_name
            )
            
            prompt = self._build_extraction_prompt(text)
            response = self._llm.generate(prompt, temperature=0.1, max_tokens=2000)
            
            # Parse JSON response
            protocol_data = self._parse_llm_response(response, filename)
            
            self._logger.info(
                "[LLMExtractionService] Successfully extracted protocol_id=%s, phase=%s, geographic_scope=%s",
                protocol_data.get("protocol_id", "UNKNOWN"),
                protocol_data.get("phase", "Unknown"),
                protocol_data.get("geographic_scope")
            )
            
            return protocol_data
            
        except Exception as e:
            self._logger.error(
                "[LLMExtractionService] Extraction failed: %s",
                str(e),
                exc_info=True
            )
            return self._create_empty_protocol(filename)
    
    def _build_extraction_prompt(self, text: str) -> str:
        """Build the extraction prompt for the LLM.
        
        Args:
            text: The document text to extract from.
        
        Returns:
            Formatted prompt string from prompts module.
        """
        return get_protocol_extraction_prompt(text)
    
    def _parse_llm_response(self, response: str, filename: str) -> Dict[str, Any]:
        """Parse the LLM's JSON response.
        
        Args:
            response: The LLM's response text.
            filename: The original filename.
        
        Returns:
            Parsed protocol data dictionary.
        """
        try:
            # Try to find JSON in the response
            response = response.strip()
            
            # Remove markdown code blocks if present
            if response.startswith("```"):
                lines = response.split("\n")
                response = "\n".join(lines[1:-1]) if len(lines) > 2 else response
                response = response.replace("```json", "").replace("```", "").strip()
            
            # Parse JSON
            data = json.loads(response)
            
            # Validate and normalize
            protocol_data = {
                "protocol_id": str(data.get("protocol_id", "UNKNOWN")),
                "title": str(data.get("title", f"Protocol from {filename}")),
                "phase": self._normalize_phase(data.get("phase", "Unknown")),
                "therapeutic_area": str(data.get("therapeutic_area", "Unknown")),
                "indication": str(data.get("indication", "Unknown")),
                "target_enrollment": int(data.get("target_enrollment", 0)),
                "duration_months": int(data.get("duration_months", 0)),
                "primary_endpoints": self._normalize_list(data.get("primary_endpoints", [])),
                "inclusion_criteria": self._normalize_list(data.get("inclusion_criteria", []))[:10],
                "exclusion_criteria": self._normalize_list(data.get("exclusion_criteria", []))[:10],
                "geographic_scope": self._normalize_list(data.get("geographic_scope", [])),
            }
            
            return protocol_data
            
        except json.JSONDecodeError as e:
            self._logger.error(
                "[LLMExtractionService] Failed to parse JSON response: %s",
                str(e)
            )
            self._logger.debug("Response was: %s", response[:500])
            return self._create_empty_protocol(filename)
        except Exception as e:
            self._logger.error(
                "[LLMExtractionService] Error parsing response: %s",
                str(e)
            )
            return self._create_empty_protocol(filename)
    
    def _normalize_phase(self, phase: str) -> str:
        """Normalize phase string to standard format.
        
        Args:
            phase: The phase string to normalize.
        
        Returns:
            Normalized phase string.
        """
        phase = str(phase).strip().upper()
        
        # Map to standard format
        phase_map = {
            "1": "Phase I", "I": "Phase I", "PHASE 1": "Phase I", "PHASE I": "Phase I",
            "2": "Phase II", "II": "Phase II", "PHASE 2": "Phase II", "PHASE II": "Phase II",
            "3": "Phase III", "III": "Phase III", "PHASE 3": "Phase III", "PHASE III": "Phase III",
            "4": "Phase IV", "IV": "Phase IV", "PHASE 4": "Phase IV", "PHASE IV": "Phase IV",
        }
        
        return phase_map.get(phase, phase.title() if phase else "Unknown")
    
    def _normalize_list(self, items: Any) -> list:
        """Normalize a list of items to strings.
        
        Args:
            items: List or other iterable to normalize.
        
        Returns:
            List of string items.
        """
        if not isinstance(items, list):
            return []
        
        normalized = []
        for item in items:
            if isinstance(item, str) and item.strip():
                normalized.append(item.strip())
            elif item:
                normalized.append(str(item).strip())
        
        return normalized
    
    def _create_empty_protocol(self, filename: str) -> Dict[str, Any]:
        """Create an empty protocol data structure.
        
        Args:
            filename: The original filename.
        
        Returns:
            Empty protocol data dictionary.
        """
        return {
            "protocol_id": "UNKNOWN",
            "title": f"Protocol from {filename}",
            "phase": "Unknown",
            "therapeutic_area": "Unknown",
            "indication": "Unknown",
            "target_enrollment": 0,
            "duration_months": 0,
            "primary_endpoints": [],
            "inclusion_criteria": [],
            "exclusion_criteria": [],
            "geographic_scope": [],
        }
