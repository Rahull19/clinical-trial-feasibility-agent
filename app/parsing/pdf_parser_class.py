"""PDF protocol parser implementation using pdfplumber.

This module provides a production-grade PDF parser that extracts structured
protocol data from PDF documents using the pdfplumber library.

Features:
- Primary: LLM-powered extraction for robust handling of any format
- Fallback: Regex-based extraction for when LLM is unavailable
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import pdfplumber

from app.llm.base_llm import BaseLLM
from app.parsing.base_parser import BaseParser
from app.parsing.llm_extraction_service import LLMExtractionService
from app.core.exceptions import FileParsingError
from app.core.logging import get_logger

logger = get_logger(__name__)


class PDFParser(BaseParser):
    """PDF protocol parser using pdfplumber for text extraction.
    
    This parser extracts text from PDF files and uses LLM-powered extraction
    as the primary method for robust handling of any format. Falls back to
    regex-based extraction if LLM is unavailable.
    
    Features:
        - Multi-page text extraction with pdfplumber
        - LLM-powered structured data extraction (primary)
        - Regex-based extraction (fallback)
        - Handles any PDF format or layout
        - Robust error handling and logging
    """
    
    def __init__(self, llm: Optional[BaseLLM] = None) -> None:
        """Initialize the PDF parser.
        
        Args:
            llm: Optional LLM provider for intelligent extraction.
                 If None, falls back to regex-based extraction.
        """
        super().__init__()
        self._llm = llm
        self._extraction_service = LLMExtractionService(llm) if llm else None
    
    @property
    def supported_extensions(self) -> List[str]:
        """Return supported file extensions."""
        return ['.pdf', '.PDF']
    
    @property
    def supported_mime_types(self) -> List[str]:
        """Return supported MIME types."""
        return ['application/pdf']
    
    @property
    def parser_name(self) -> str:
        """Return parser name."""
        return "PDFParser"
    
    def parse(self, file_bytes: bytes, filename: str) -> Dict[str, Any]:
        """Parse PDF file and extract structured protocol data.
        
        Args:
            file_bytes: The PDF file content as bytes.
            filename: The original filename.
        
        Returns:
            Dictionary containing structured protocol data.
        
        Raises:
            FileParsingError: When the PDF cannot be parsed.
        """
        self.validate_input(file_bytes, filename)
        
        self._logger.info(
            "[%s] Parsing PDF — filename=%s, size=%d bytes",
            self.parser_name,
            filename,
            len(file_bytes)
        )
        
        try:
            # Extract text from PDF
            text = self._extract_text_from_pdf(file_bytes)
            
            if not text or len(text.strip()) < 10:
                raise FileParsingError(
                    "PDF appears to be empty or contains no extractable text.",
                    details={"filename": filename, "text_length": len(text)}
                )
            
            # Extract structured data using LLM (primary) or regex (fallback)
            if self._extraction_service:
                self._logger.info(
                    "[%s] Using LLM-powered extraction for robust parsing",
                    self.parser_name
                )
                protocol_data = self._extraction_service.extract_protocol_data(text, filename)
            else:
                self._logger.info(
                    "[%s] Using regex-based extraction (LLM not available)",
                    self.parser_name
                )
                protocol_data = self._extract_protocol_from_text(text, filename)
            
            # Add metadata
            protocol_data.update({
                "source": "pdf",
                "filename": filename,
                "raw_text": text,
                "raw_text_length": len(text)
            })
            
            self._logger.info(
                "[%s] Successfully parsed PDF — extracted %d characters, protocol_id=%s",
                self.parser_name,
                len(text),
                protocol_data.get("protocol_id", "UNKNOWN")
            )
            
            return protocol_data
            
        except FileParsingError:
            raise
        except Exception as e:
            self._logger.error(
                "[%s] Failed to parse PDF: %s",
                self.parser_name,
                str(e),
                exc_info=True
            )
            raise FileParsingError(
                f"Failed to parse PDF: {e}",
                details={"filename": filename, "parser": self.parser_name}
            ) from e
    
    def _extract_text_from_pdf(self, file_bytes: bytes) -> str:
        """Extract all text from PDF file bytes.
        
        Args:
            file_bytes: The PDF content as bytes.
        
        Returns:
            Extracted text from all pages.
        
        Raises:
            Exception: If PDF cannot be opened or read.
        """
        from io import BytesIO
        
        text = ""
        
        try:
            # Wrap bytes in BytesIO for pdfplumber
            pdf_stream = BytesIO(file_bytes)
            with pdfplumber.open(pdf_stream) as pdf:
                total_pages = len(pdf.pages)
                self._logger.debug("[%s] Processing %d pages", self.parser_name, total_pages)
                
                for page_num, page in enumerate(pdf.pages, 1):
                    page_text = page.extract_text()
                    if page_text:
                        text += f"\n--- Page {page_num} of {total_pages} ---\n"
                        text += page_text + "\n"
                    else:
                        self._logger.warning(
                            "[%s] Page %d contains no extractable text",
                            self.parser_name,
                            page_num
                        )
        except Exception as e:
            self._logger.error("[%s] Error reading PDF: %s", self.parser_name, str(e))
            raise
        
        return text
    
    def _extract_protocol_from_text(self, text: str, filename: str) -> Dict[str, Any]:
        """Extract structured protocol data from text using heuristics.
        
        This method uses regex patterns to identify key protocol fields.
        For production use with complex protocols, consider:
        1. Using an LLM for more accurate extraction
        2. Training a custom NER model
        3. Using template-based extraction for known formats
        
        Args:
            text: The extracted text from PDF.
            filename: The original filename.
        
        Returns:
            Dictionary with structured protocol data.
        """
        # Start with default structure
        protocol_data = self._create_default_protocol_data(filename, "pdf")
        
        lines = text.split('\n')
        
        # Extract protocol ID
        protocol_id = self._extract_protocol_id(lines)
        if protocol_id:
            protocol_data["protocol_id"] = protocol_id
        
        # Extract phase
        phase = self._extract_phase(lines)
        if phase:
            protocol_data["phase"] = phase
        
        # Extract therapeutic area
        therapeutic_area = self._extract_therapeutic_area(lines)
        if therapeutic_area:
            protocol_data["therapeutic_area"] = therapeutic_area
        
        # Extract target enrollment
        enrollment = self._extract_target_enrollment(lines)
        if enrollment:
            protocol_data["target_enrollment"] = enrollment
        
        # Extract title
        title = self._extract_title(lines)
        if title:
            protocol_data["title"] = title
        
        # Extract criteria sections
        protocol_data["inclusion_criteria"] = self._extract_section(
            text,
            ["inclusion criteria", "key inclusion criteria", "inclusion"]
        )
        
        protocol_data["exclusion_criteria"] = self._extract_section(
            text,
            ["exclusion criteria", "key exclusion criteria", "exclusion"]
        )
        
        # Extract endpoints
        protocol_data["primary_endpoints"] = self._extract_section(
            text,
            ["primary endpoint", "primary endpoints", "primary outcome"]
        )
        
        return protocol_data
    
    def _extract_protocol_id(self, lines: List[str]) -> str:
        """Extract protocol ID from text lines."""
        for i, line in enumerate(lines):
            line = line.strip()
            # Pattern: "Protocol ID: ABC-123" or "Trial ID" followed by ID on next line
            match = re.search(
                r'(?:protocol|trial)\s*(?:id|number|no\.?)[:\s]*([A-Z0-9-]{3,})?',
                line,
                re.IGNORECASE
            )
            if match:
                # If ID is on same line
                if match.group(1):
                    return match.group(1)
                # If ID is on next line
                elif i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    id_match = re.match(r'^([A-Z0-9-]{3,})$', next_line)
                    if id_match:
                        return id_match.group(1)
        return ""
    
    def _extract_phase(self, lines: List[str]) -> str:
        """Extract study phase from text lines."""
        for i, line in enumerate(lines):
            line = line.strip()
            # Pattern: "Phase III" or "Trial Phase" followed by phase on next line
            if re.search(r'(?:trial\s*)?phase', line, re.IGNORECASE):
                # Check same line first
                match = re.search(r'phase\s*(I{1,3}|IV|1|2|3|4)', line, re.IGNORECASE)
                if match:
                    phase = match.group(1).upper()
                    phase_map = {'1': 'I', '2': 'II', '3': 'III', '4': 'IV'}
                    return f"Phase {phase_map.get(phase, phase)}"
                # Check next line
                elif i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    match = re.search(r'phase\s*(I{1,3}|IV|1|2|3|4)', next_line, re.IGNORECASE)
                    if match:
                        phase = match.group(1).upper()
                        phase_map = {'1': 'I', '2': 'II', '3': 'III', '4': 'IV'}
                        return f"Phase {phase_map.get(phase, phase)}"
        return ""
    
    def _extract_therapeutic_area(self, lines: List[str]) -> str:
        """Extract therapeutic area from text lines."""
        for i, line in enumerate(lines):
            line = line.strip()
            # Pattern: "Therapeutic Area: Oncology" or header followed by value
            match = re.search(
                r'(?:therapeutic\s*area|indication|disease\s*area)[:\s]*([A-Za-z\s-]+)?',
                line,
                re.IGNORECASE
            )
            if match:
                # If area is on same line
                if match.group(1) and len(match.group(1).strip()) > 2:
                    area = match.group(1).strip()
                    words = area.split()[:5]
                    return ' '.join(words)
                # If area is on next line
                elif i + 1 < len(lines):
                    next_line = lines[i + 1].strip()
                    if next_line and not re.match(r'^(?:trial|phase|inclusion|exclusion)', next_line, re.IGNORECASE):
                        words = next_line.split()[:5]
                        return ' '.join(words)
        return ""
    
    def _extract_target_enrollment(self, lines: List[str]) -> int:
        """Extract target enrollment number from text lines."""
        for line in lines:
            line = line.strip()
            # Pattern: "Target Enrollment: 500" or "Sample Size: 500"
            match = re.search(
                r'(?:target\s*enrollment|sample\s*size|number\s*of\s*patients)[:\s]+(\d+)',
                line,
                re.IGNORECASE
            )
            if match:
                return int(match.group(1))
        return 0
    
    def _extract_title(self, lines: List[str]) -> str:
        """Extract protocol title from text lines."""
        # Look for common title patterns in first 20 lines
        for line in lines[:20]:
            line = line.strip()
            # Skip very short lines
            if len(line) < 20:
                continue
            # Look for lines that might be titles (all caps or title case)
            if line.isupper() or line.istitle():
                # Skip if it looks like a header
                if any(keyword in line.lower() for keyword in ['page', 'confidential', 'protocol']):
                    continue
                return line[:200]  # Limit title length
        return ""
    
    def _extract_section(self, text: str, section_headers: List[str]) -> List[str]:
        """Extract bullet points or numbered items from a section.
        
        Args:
            text: The full text to search.
            section_headers: List of possible section header names.
        
        Returns:
            List of extracted items (up to 10).
        """
        # Find the section
        section_text = ""
        for header in section_headers:
            # Pattern to find section and capture content until next major section
            pattern = rf"{header}[:\s]*\n([\s\S]*?)(?=\n\s*[A-Z][A-Za-z\s]{{10,}}:|\n\s*\d+\.\s*[A-Z]|$)"
            match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
            if match:
                section_text = match.group(1)
                break
        
        if not section_text:
            return []
        
        items = []
        
        # Extract bullet points (•, -, *, ·)
        bullets = re.findall(r'^\s*[•·\-\*]\s*(.+)$', section_text, re.MULTILINE)
        items.extend(bullets)
        
        # Extract numbered items
        numbered = re.findall(r'^\s*\d+\.\s*(.+)$', section_text, re.MULTILINE)
        items.extend(numbered)
        
        # If no structured items found, split by newlines
        if not items:
            lines = [line.strip() for line in section_text.split('\n') if line.strip()]
            items = [line for line in lines if len(line) > 15][:10]
        
        # Clean up items
        cleaned_items = []
        for item in items[:10]:  # Limit to 10 items
            item = item.strip()
            # Remove leading bullets/numbers
            item = re.sub(r'^[•·\-\*\d\.]+\s*', '', item)
            # Remove trailing punctuation
            item = item.rstrip('.,;')
            if item and len(item) > 10:
                cleaned_items.append(item)
        
        return cleaned_items
