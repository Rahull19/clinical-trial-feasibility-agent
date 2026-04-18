"""Parser factory for dynamic parser selection and instantiation.

This module implements the Factory pattern to provide a centralized way to
select and instantiate the appropriate parser based on file type.

The factory supports LLM injection for robust, intelligent parsing.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Type

from app.llm.base_llm import BaseLLM
from app.parsing.base_parser import BaseParser
from app.parsing.docx_parser_class import DOCXParser
from app.parsing.json_parser_class import JSONParser
from app.parsing.pdf_parser_class import PDFParser
from app.core.exceptions import UnsupportedFileTypeError
from app.core.logging import get_logger

logger = get_logger(__name__)


class ParserFactory:
    """Factory class for creating and managing protocol file parsers.
    
    This factory implements the Factory pattern to provide a clean interface
    for parser instantiation and selection. It maintains a registry of available
    parsers and can automatically select the appropriate parser based on file
    type or MIME type.
    
    Supports LLM injection for intelligent, robust parsing of any format.
    
    Usage:
        factory = ParserFactory(llm=llm_provider)
        parser = factory.get_parser(filename="protocol.pdf")
        protocol_data = parser.parse(file_bytes, filename)
    
    Or use the convenience method:
        factory = ParserFactory(llm=llm_provider)
        protocol_data = factory.parse_file(file_bytes, filename, mime_type)
    """
    
    def __init__(self, llm: Optional[BaseLLM] = None) -> None:
        """Initialize the parser factory with default parsers.
        
        Args:
            llm: Optional LLM provider for intelligent extraction.
                 If provided, parsers will use LLM for robust parsing.
        """
        self._logger = get_logger(self.__class__.__name__)
        self._llm = llm
        self._parsers: Dict[str, BaseParser] = {}
        self._parser_classes: Dict[str, Type[BaseParser]] = {}
        
        # Register default parsers
        self._register_default_parsers()
    
    def _register_default_parsers(self) -> None:
        """Register the default set of parsers."""
        self.register_parser("pdf", PDFParser)
        self.register_parser("docx", DOCXParser)
        self.register_parser("json", JSONParser)
        
        self._logger.info(
            "[ParserFactory] Registered %d default parsers: %s",
            len(self._parser_classes),
            ", ".join(self._parser_classes.keys())
        )
    
    def register_parser(self, name: str, parser_class: Type[BaseParser]) -> None:
        """Register a new parser class.
        
        This allows for runtime registration of custom parsers without
        modifying the factory code.
        
        Args:
            name: Unique name for the parser (e.g., "pdf", "docx").
            parser_class: The parser class to register (must inherit from BaseParser).
        
        Raises:
            TypeError: If parser_class doesn't inherit from BaseParser.
        """
        if not issubclass(parser_class, BaseParser):
            raise TypeError(
                f"Parser class must inherit from BaseParser. Got: {parser_class.__name__}"
            )
        
        self._parser_classes[name.lower()] = parser_class
        self._logger.debug(
            "[ParserFactory] Registered parser: %s -> %s",
            name,
            parser_class.__name__
        )
    
    def get_parser(
        self,
        filename: Optional[str] = None,
        mime_type: Optional[str] = None,
        parser_name: Optional[str] = None
    ) -> BaseParser:
        """Get an appropriate parser instance.
        
        The parser is selected based on (in order of priority):
        1. Explicit parser_name if provided
        2. MIME type if provided
        3. File extension from filename
        
        Args:
            filename: The filename to determine parser from extension.
            mime_type: The MIME type to determine parser.
            parser_name: Explicit parser name (e.g., "pdf", "docx", "json").
        
        Returns:
            An instance of the appropriate parser.
        
        Raises:
            UnsupportedFileTypeError: If no suitable parser is found.
            ValueError: If no identification method is provided.
        """
        # Priority 1: Explicit parser name
        if parser_name:
            parser_name = parser_name.lower()
            if parser_name in self._parser_classes:
                return self._get_or_create_parser(parser_name)
            else:
                raise UnsupportedFileTypeError(
                    f"Unknown parser: {parser_name}",
                    details={"available_parsers": list(self._parser_classes.keys())}
                )
        
        # Priority 2: Try all parsers to see which can handle the file
        if filename or mime_type:
            for name, parser_class in self._parser_classes.items():
                parser = self._get_or_create_parser(name)
                if parser.can_parse(filename or "", mime_type):
                    self._logger.debug(
                        "[ParserFactory] Selected parser: %s for file=%s, mime=%s",
                        parser.parser_name,
                        filename,
                        mime_type
                    )
                    return parser
        
        # No suitable parser found
        raise UnsupportedFileTypeError(
            "No suitable parser found for the given file.",
            details={
                "filename": filename,
                "mime_type": mime_type,
                "available_parsers": list(self._parser_classes.keys())
            }
        )
    
    def _get_or_create_parser(self, name: str) -> BaseParser:
        """Get existing parser instance or create a new one.
        
        This implements a simple caching mechanism to reuse parser instances.
        Parsers are instantiated with LLM if available.
        
        Args:
            name: The parser name.
        
        Returns:
            Parser instance.
        """
        if name not in self._parsers:
            parser_class = self._parser_classes[name]
            
            # Instantiate with LLM if available and parser supports it
            try:
                if self._llm and name in ['pdf', 'docx', 'json']:
                    self._parsers[name] = parser_class(llm=self._llm)
                    self._logger.debug(
                        "[ParserFactory] Created parser with LLM: %s",
                        parser_class.__name__
                    )
                else:
                    self._parsers[name] = parser_class()
                    self._logger.debug(
                        "[ParserFactory] Created parser: %s",
                        parser_class.__name__
                    )
            except TypeError:
                # Parser doesn't accept llm parameter
                self._parsers[name] = parser_class()
                self._logger.debug(
                    "[ParserFactory] Created parser (no LLM support): %s",
                    parser_class.__name__
                )
        
        return self._parsers[name]
    
    def parse_file(
        self,
        file_bytes: bytes,
        filename: str,
        mime_type: Optional[str] = None
    ) -> Dict:
        """Convenience method to parse a file in one call.
        
        This method automatically selects the appropriate parser and parses
        the file, providing a simple one-line interface for file parsing.
        
        Args:
            file_bytes: The file content as bytes.
            filename: The original filename.
            mime_type: Optional MIME type for parser selection.
        
        Returns:
            Dictionary containing structured protocol data.
        
        Raises:
            UnsupportedFileTypeError: If no suitable parser is found.
            FileParsingError: If parsing fails.
        """
        parser = self.get_parser(filename=filename, mime_type=mime_type)
        
        self._logger.info(
            "[ParserFactory] Parsing file with %s — filename=%s",
            parser.parser_name,
            filename
        )
        
        return parser.parse(file_bytes, filename)
    
    def get_supported_extensions(self) -> List[str]:
        """Get list of all supported file extensions.
        
        Returns:
            List of supported file extensions across all registered parsers.
        """
        extensions = []
        for name in self._parser_classes:
            parser = self._get_or_create_parser(name)
            extensions.extend(parser.supported_extensions)
        return list(set(extensions))  # Remove duplicates
    
    def get_supported_mime_types(self) -> List[str]:
        """Get list of all supported MIME types.
        
        Returns:
            List of supported MIME types across all registered parsers.
        """
        mime_types = []
        for name in self._parser_classes:
            parser = self._get_or_create_parser(name)
            mime_types.extend(parser.supported_mime_types)
        return list(set(mime_types))  # Remove duplicates
    
    def list_parsers(self) -> Dict[str, str]:
        """List all registered parsers.
        
        Returns:
            Dictionary mapping parser names to their class names.
        """
        return {
            name: parser_class.__name__
            for name, parser_class in self._parser_classes.items()
        }


# Global singleton instance for convenience
_default_factory: Optional[ParserFactory] = None


def get_parser_factory() -> ParserFactory:
    """Get the default global parser factory instance.
    
    This provides a singleton factory instance for use throughout the application.
    
    Returns:
        The global ParserFactory instance.
    """
    global _default_factory
    if _default_factory is None:
        _default_factory = ParserFactory()
    return _default_factory


def parse_protocol_file(
    file_bytes: bytes,
    filename: str,
    mime_type: Optional[str] = None
) -> Dict:
    """Convenience function to parse a protocol file using the default factory.
    
    This is a simple wrapper around the global factory's parse_file method.
    
    Args:
        file_bytes: The file content as bytes.
        filename: The original filename.
        mime_type: Optional MIME type for parser selection.
    
    Returns:
        Dictionary containing structured protocol data.
    
    Raises:
        UnsupportedFileTypeError: If no suitable parser is found.
        FileParsingError: If parsing fails.
    """
    factory = get_parser_factory()
    return factory.parse_file(file_bytes, filename, mime_type)
