"""Prompt templates for risk scoring and assessment.

All prompts used by the risk scoring pipeline are centralised here.
"""

from __future__ import annotations

RISK_ASSESSMENT_PROMPT: str = """
You are a clinical trial risk analyst. Evaluate the risk profile for the
following trial configuration.

Country Data:
{country_data}

Site Data:
{site_data}

Protocol Criteria:
{parsed_criteria}

For each entity (country or site), provide a risk score between 0.0 and 1.0
where higher values indicate greater risk. Consider:
1. Regulatory complexity and approval timelines
2. Patient recruitment difficulty
3. Site operational capability
4. Data quality and monitoring challenges
5. Geopolitical and logistical risks

Return a JSON object mapping entity identifiers to risk scores.
""".strip()

RISK_MITIGATION_PROMPT: str = """
You are a clinical trial risk mitigation specialist.

Given the following risk scores and compliance flags, suggest concrete
mitigation strategies for each high-risk entity.

Risk Scores:
{risk_scores}

Compliance Flags:
{compliance_flags}

Return a JSON object with:
- high_risk_entities: list of entity identifiers with risk > 0.7
- mitigation_strategies: dict mapping entity → list of strategy strings
- overall_risk_level: string ("low", "medium", "high", "critical")
""".strip()
