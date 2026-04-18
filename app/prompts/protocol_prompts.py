"""Prompt templates for protocol parsing and analysis.

All prompts used by the protocol parsing pipeline are centralised here
to keep node and service code free of inline prompt strings.
"""

from __future__ import annotations

PROTOCOL_EXTRACTION_PROMPT: str = """
You are a clinical trial protocol analyst. Extract the following structured
fields from the provided protocol document text.

Return a JSON object with these keys:
- protocol_id: string
- title: string
- phase: string (e.g. "Phase I", "Phase II", "Phase III", "Phase IV")
- therapeutic_area: string
- indication: string
- target_enrollment: integer
- age_range: object with "min" and "max" integer fields
- gender: string ("all", "male", "female")
- inclusion_criteria: list of strings
- exclusion_criteria: list of strings
- primary_endpoint: string
- duration_weeks: integer

If a field cannot be determined, use null.

Protocol Text:
{protocol_text}
""".strip()

CRITERIA_VALIDATION_PROMPT: str = """
You are a clinical trial eligibility criteria validator.

Given the following parsed eligibility criteria, identify any:
1. Missing required fields
2. Inconsistencies between inclusion and exclusion criteria
3. Potential regulatory issues

Parsed Criteria:
{parsed_criteria}

Return a JSON object with:
- is_valid: boolean
- issues: list of issue description strings
- suggestions: list of improvement suggestions
""".strip()
