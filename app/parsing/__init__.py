"""Parsing package for protocol file ingestion.

This package provides a modular, extensible architecture for parsing clinical trial
protocol files in various formats (PDF, DOCX, JSON). All parsers implement the
BaseParser interface, ensuring consistency and enabling polymorphic behavior.

Usage:
    from app.parsing import parse_protocol_file
    
    protocol_data = parse_protocol_file(file_bytes, filename, mime_type)

Or use the factory directly:
    from app.parsing import ParserFactory
    
    factory = ParserFactory()
    parser = factory.get_parser(filename="protocol.pdf")
    protocol_data = parser.parse(file_bytes, filename)
"""

from app.parsing.base_parser import BaseParser
from app.parsing.docx_parser_class import DOCXParser
from app.parsing.json_parser_class import JSONParser
from app.parsing.parser_factory import (
    ParserFactory,
    get_parser_factory,
    parse_protocol_file,
)
from app.parsing.pdf_parser_class import PDFParser

__all__ = [
    # Base class
    "BaseParser",
    # Concrete parsers
    "PDFParser",
    "DOCXParser",
    "JSONParser",
    # Factory
    "ParserFactory",
    "get_parser_factory",
    # Convenience function
    "parse_protocol_file",
]
