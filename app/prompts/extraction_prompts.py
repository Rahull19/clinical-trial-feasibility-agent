"""Prompts for LLM-powered protocol data extraction.

This module contains all prompts used for extracting structured data
from unstructured clinical trial protocol documents.
"""

from __future__ import annotations


def get_protocol_extraction_prompt(text: str) -> str:
    """Build the extraction prompt for protocol data.
    
    Args:
        text: The raw text extracted from the protocol document.
    
    Returns:
        Formatted prompt for LLM extraction.
    """
    prompt = f"""You are a clinical trial protocol data extraction expert. Extract structured information from the following clinical trial protocol text.

PROTOCOL TEXT:
{text}

INSTRUCTIONS:
Extract the following fields and return them as a JSON object. If a field is not found, use appropriate default values.

Required fields:
- protocol_id: The protocol/trial ID or number (string). Look for patterns like "Protocol ID", "Trial ID", "Study Number", etc.
- title: The study title, objective, or description (string)
- phase: The trial phase (string). Format as "Phase I", "Phase II", "Phase III", or "Phase IV"
- therapeutic_area: The disease area, indication, or therapeutic focus (string)
- indication: The specific disease or condition being studied (string). Often part of therapeutic_area.
- target_enrollment: Number of patients to enroll (integer, use 0 if not found)
- duration_months: Study duration in months (integer, use 0 if not found)
- primary_endpoints: List of primary endpoints or outcomes (array of strings)
- inclusion_criteria: List of inclusion/eligibility criteria (array of strings, extract up to 10)
- exclusion_criteria: List of exclusion criteria (array of strings, extract up to 10)
- geographic_scope: List of countries where the trial will be conducted (array of strings)

EXTRACTION GUIDELINES:
1. Be thorough - extract all relevant information from the text
2. For criteria, extract complete sentences or bullet points
3. Normalize phase to standard format (e.g., "Phase III" not "phase 3" or "III")
4. If multiple IDs exist, use the most prominent one
5. For therapeutic area, include both disease type and specific indication if available
6. Extract endpoints exactly as stated in the document

OUTPUT FORMAT:
Return ONLY valid JSON with no additional text, explanations, or markdown formatting.
Use these exact field names and structure:

{{
  "protocol_id": "string",
  "title": "string",
  "phase": "string",
  "therapeutic_area": "string",
  "indication": "string",
  "target_enrollment": number,
  "duration_months": number,
  "primary_endpoints": ["string"],
  "inclusion_criteria": ["string"],
  "exclusion_criteria": ["string"],
  "geographic_scope": ["string"]
}}

IMPORTANT:
- Use "UNKNOWN" for protocol_id if not found
- Use "Unknown" for phase if not found
- Use "Unknown" for therapeutic_area if not found
- Use empty arrays [] for lists if not found
- Be precise and extract actual values from the text

JSON OUTPUT:"""
    
    return prompt


def get_criteria_extraction_prompt(text: str, criteria_type: str) -> str:
    """Build a focused prompt for extracting specific criteria.
    
    Args:
        text: The raw text from the protocol.
        criteria_type: Either "inclusion" or "exclusion".
    
    Returns:
        Formatted prompt for criteria extraction.
    """
    criteria_label = "Inclusion" if criteria_type == "inclusion" else "Exclusion"
    
    prompt = f"""Extract {criteria_label} Criteria from the following clinical trial protocol text.

PROTOCOL TEXT:
{text}

INSTRUCTIONS:
Find and extract all {criteria_label.lower()} criteria from the text. These may be labeled as:
- "{criteria_label} Criteria"
- "Key {criteria_label} Criteria"
- "{criteria_label}"
- "Eligibility Criteria" (for inclusion)

Extract each criterion as a separate item. Include:
- Bullet points or numbered items
- Complete sentences describing requirements
- Age ranges, diagnostic criteria, performance status, etc.

Return as a JSON array of strings. Extract up to 15 criteria.

OUTPUT FORMAT:
Return ONLY a valid JSON array with no additional text:

["criterion 1", "criterion 2", "criterion 3"]

JSON OUTPUT:"""
    
    return prompt


def get_field_extraction_prompt(text: str, field_name: str, field_description: str) -> str:
    """Build a focused prompt for extracting a specific field.
    
    Args:
        text: The raw text from the protocol.
        field_name: The name of the field to extract.
        field_description: Description of what to look for.
    
    Returns:
        Formatted prompt for field extraction.
    """
    prompt = f"""Extract the {field_name} from the following clinical trial protocol text.

PROTOCOL TEXT:
{text}

INSTRUCTIONS:
Find and extract the {field_name}. {field_description}

Return ONLY the extracted value as plain text, no JSON, no additional formatting.

If not found, return "UNKNOWN" for IDs or "Unknown" for other fields.

EXTRACTED VALUE:"""
    
    return prompt
