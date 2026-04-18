"""Prompt templates for final report generation.

All prompts used by the report generation pipeline are centralised here.
"""

from __future__ import annotations

REPORT_GENERATION_PROMPT: str = """
You are a clinical trial feasibility report writer. Generate a comprehensive
executive summary based on the following trial evaluation data.

Protocol:
{protocol_summary}

Country Scores:
{country_scores}

Site Scores:
{site_scores}

Risk Assessment:
{risk_scores}

Investigators:
{investigators}

Feasibility Score: {feasibility_score}
Compliance Issues: {compliance_flags}
Human Review Status: {approval_status}
Human Feedback: {human_feedback}

Write a structured executive summary covering:
1. Overall feasibility assessment
2. Recommended countries and sites
3. Key risks and mitigation strategies
4. Investigator readiness
5. Compliance status
6. Final recommendation (proceed / conditional / not recommended)

Return the summary as a JSON object with sections as keys.
""".strip()

RECOMMENDATION_PROMPT: str = """
You are a clinical trial advisor. Based on the feasibility score of
{feasibility_score} and the following data, provide a final go/no-go
recommendation.

Countries evaluated: {num_countries}
Sites selected: {num_sites}
Investigators matched: {num_investigators}
Compliance issues: {num_compliance_issues}
High-risk entities: {num_high_risk}

Return a JSON object with:
- decision: string ("GO", "CONDITIONAL_GO", "NO_GO")
- confidence: float (0.0 - 1.0)
- rationale: string (2-3 sentences)
- conditions: list of strings (if conditional)
""".strip()
