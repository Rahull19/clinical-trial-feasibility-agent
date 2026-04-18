"""LangGraph builder (v2) — Clean Architecture compliant.

All services are injected via the DI container. The graph layer only
orchestrates; it contains ZERO business logic.
"""

from __future__ import annotations

from typing import Optional

from langgraph.graph import END, StateGraph

from app.core.config import AppConfig
from app.core.logging import get_logger
from app.domain.interfaces.llm import LLMPort
from app.domain.interfaces.rag import RAGPort
from app.graph.state import TrialState
from app.infrastructure.db.session import DatabaseSession

logger = get_logger(__name__)

# ── Node Names ────────────────────────────────────────────────────────────────
NODE_PROTOCOL_PARSER = "protocol_parser_node"
NODE_DATA_ENRICHMENT = "data_enrichment_node"
NODE_COUNTRY_FEASIBILITY = "country_feasibility_node"
NODE_SITE_SELECTION = "site_selection_node"
NODE_INVESTIGATOR_MATCHING = "investigator_matching_node"
NODE_RISK_SCORING = "risk_scoring_node"
NODE_COMPLIANCE_VALIDATOR = "compliance_validator_node"
NODE_FEASIBILITY_SCORING = "feasibility_scoring_node"
NODE_REPORT_GENERATOR = "report_generator_node"
NODE_HUMAN_REVIEW = "human_review_node"

# ── Human Review Actions ──────────────────────────────────────────────────────
ACTION_APPROVE = "approve"
ACTION_REJECT = "reject"
ACTION_REQUEST_CHANGES = "request_changes"

_END = "__end__"


# ── Edge Routing Functions ────────────────────────────────────────────────────

def _route_after_enrichment(state: TrialState, config: AppConfig) -> str:
    if state.missing_data_flags:
        if state.enrichment_retry_count < config.max_enrichment_retries:
            logger.info("route_after_enrichment → retry enrichment (attempt %d)", state.enrichment_retry_count + 1)
            return NODE_DATA_ENRICHMENT
        logger.info("route_after_enrichment → human_review (retries exhausted)")
        return NODE_HUMAN_REVIEW
    logger.info("route_after_enrichment → country_feasibility")
    return NODE_COUNTRY_FEASIBILITY


def _route_after_country(state: TrialState) -> str:
    if not state.country_scores:
        logger.info("route_after_country → END (no valid countries)")
        return _END
    logger.info("route_after_country → site_selection")
    return NODE_SITE_SELECTION


def _route_after_risk(state: TrialState, config: AppConfig) -> str:
    high_risks = {k: v for k, v in state.risk_scores.items() if v > config.risk_score_threshold}
    if high_risks:
        logger.info("route_after_risk → human_review (high-risk: %s)", list(high_risks.keys()))
        return NODE_HUMAN_REVIEW
    logger.info("route_after_risk → compliance_validator")
    return NODE_COMPLIANCE_VALIDATOR


def _route_after_compliance(state: TrialState, config: AppConfig) -> str:
    if state.compliance_flags:
        if state.compliance_retry_count < config.max_compliance_retries:
            logger.info("route_after_compliance → retry country_feasibility")
            return NODE_COUNTRY_FEASIBILITY
        logger.info("route_after_compliance → END (retries exhausted)")
        return _END
    logger.info("route_after_compliance → feasibility_scoring")
    return NODE_FEASIBILITY_SCORING


def _route_after_feasibility(state: TrialState, config: AppConfig) -> str:
    if state.feasibility_score < config.feasibility_score_threshold:
        if state.site_reselection_retry_count < config.max_site_reselection_retries:
            logger.info("route_after_feasibility → retry site_selection")
            return NODE_SITE_SELECTION
        logger.info("route_after_feasibility → human_review (low score, retries exhausted)")
        return NODE_HUMAN_REVIEW
    logger.info("route_after_feasibility → human_review (for approval)")
    return NODE_HUMAN_REVIEW


def _route_after_human_review(state: TrialState) -> str:
    action = state.approval_status or ""
    if action == ACTION_APPROVE:
        logger.info("route_after_human_review → report_generator (approved)")
        return NODE_REPORT_GENERATOR
    if action == ACTION_REJECT:
        logger.info("route_after_human_review → risk_scoring (rejected)")
        return NODE_RISK_SCORING
    if action == ACTION_REQUEST_CHANGES:
        logger.info("route_after_human_review → site_selection (changes requested)")
        return NODE_SITE_SELECTION
    logger.warning("route_after_human_review → risk_scoring (unknown action: %s)", action)
    return NODE_RISK_SCORING


# ── Graph Builder ─────────────────────────────────────────────────────────────

def build_graph(
    config: AppConfig,
    db_session: DatabaseSession,
    llm: Optional[LLMPort] = None,
    rag: Optional[RAGPort] = None,
    reviewer_mode: str = "api",
) -> StateGraph:
    """Construct and compile the clinical trial feasibility graph.

    All service instances are created here with injected dependencies.
    The graph layer only orchestrates — zero business logic inside nodes.
    """
    from app.application.services.protocol_parser import ProtocolParser
    from app.application.services.enrichment_engine import EnrichmentEngine
    from app.application.services.scoring_engine import CountryScorer, FeasibilityScorer
    from app.application.services.site_selector import SiteSelector
    from app.application.services.investigator_matcher import InvestigatorMatcher
    from app.application.services.risk_engine import RiskEngine
    from app.application.services.compliance_engine import ComplianceEngine
    from app.application.services.report_generator import ReportGenerator
    from app.human.reviewer import HumanReviewer

    logger.info("Building clinical trial feasibility graph (v2) …")

    # ── Instantiate Services (DI) ─────────────────────────────────────────
    protocol_parser = ProtocolParser(config=config)
    enrichment_engine = EnrichmentEngine(db_session=db_session, rag=rag, config=config)
    country_scorer = CountryScorer(config=config)
    site_selector = SiteSelector(db_session=db_session, rag=rag, config=config)
    investigator_matcher = InvestigatorMatcher(db_session=db_session, rag=rag, config=config)
    risk_engine = RiskEngine(config=config)
    compliance_engine = ComplianceEngine(config=config)
    feasibility_scorer = FeasibilityScorer(config=config)
    report_gen = ReportGenerator(config=config)
    reviewer = HumanReviewer(mode=reviewer_mode)

    # ── Thin Node Functions ───────────────────────────────────────────────

    import asyncio

    def _run_async(coro):
        """Helper: run async coroutine from sync LangGraph node."""
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = None
        if loop and loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(asyncio.run, coro).result()
        return asyncio.run(coro)

    def node_protocol_parser(state: TrialState):
        logger.info("[ProtocolParserNode] START")
        try:
            parsed, flags = _run_async(protocol_parser.parse(state.protocol_data))
            combined = list(set(state.missing_data_flags + flags))
            logger.info("[ProtocolParserNode] END — missing_flags=%d", len(combined))
            return {"parsed_criteria": parsed, "missing_data_flags": combined}
        except Exception as exc:
            logger.error("[ProtocolParserNode] FAILED — %s", exc)
            return {"parsed_criteria": {}, "missing_data_flags": [f"protocol_parsing_error:{exc}"]}

    def node_enrichment(state: TrialState):
        logger.info("[DataEnrichmentNode] START")
        retry = state.enrichment_retry_count
        try:
            countries, flags = _run_async(enrichment_engine.enrich(state.parsed_criteria))
            logger.info("[DataEnrichmentNode] END — countries=%d", len(countries))
            return {"countries": countries, "missing_data_flags": flags, "enrichment_retry_count": retry + 1}
        except Exception as exc:
            logger.error("[DataEnrichmentNode] FAILED — %s", exc)
            return {"countries": [], "missing_data_flags": [f"enrichment_error:{exc}"], "enrichment_retry_count": retry + 1}

    def node_country(state: TrialState):
        logger.info("[CountryFeasibilityNode] START")
        try:
            scores = _run_async(country_scorer.evaluate(state.countries, state.parsed_criteria, config.country_score_threshold))
            logger.info("[CountryFeasibilityNode] END — passing=%d", len(scores))
            return {"country_scores": scores}
        except Exception as exc:
            logger.error("[CountryFeasibilityNode] FAILED — %s", exc)
            return {"country_scores": {}}

    def node_site(state: TrialState):
        logger.info("[SiteSelectionNode] START")
        retry = state.site_reselection_retry_count
        try:
            sites, scores = _run_async(site_selector.select(state.country_scores, state.parsed_criteria, config.site_score_threshold))
            logger.info("[SiteSelectionNode] END — sites=%d", len(sites))
            return {"sites": sites, "site_scores": scores, "site_reselection_retry_count": retry}
        except Exception as exc:
            logger.error("[SiteSelectionNode] FAILED — %s", exc)
            return {"sites": [], "site_scores": {}, "site_reselection_retry_count": retry + 1}

    def node_investigator(state: TrialState):
        logger.info("[InvestigatorMatchingNode] START")
        try:
            investigators = _run_async(investigator_matcher.match(state.sites, state.parsed_criteria))
            logger.info("[InvestigatorMatchingNode] END — investigators=%d", len(investigators))
            return {"investigators": investigators}
        except Exception as exc:
            logger.error("[InvestigatorMatchingNode] FAILED — %s", exc)
            return {"investigators": []}

    def node_risk(state: TrialState):
        logger.info("[RiskScoringNode] START")
        try:
            scores = _run_async(risk_engine.compute(state.countries, state.sites, state.country_scores, state.site_scores))
            logger.info("[RiskScoringNode] END — entities=%d", len(scores))
            return {"risk_scores": scores}
        except Exception as exc:
            logger.error("[RiskScoringNode] FAILED — %s", exc)
            return {"risk_scores": {}}

    def node_compliance(state: TrialState):
        logger.info("[ComplianceValidatorNode] START")
        retry = state.compliance_retry_count
        try:
            flags = _run_async(compliance_engine.validate(state.countries, state.country_scores, state.sites, state.parsed_criteria))
            logger.info("[ComplianceValidatorNode] END — flags=%d", len(flags))
            return {"compliance_flags": flags, "compliance_retry_count": retry}
        except Exception as exc:
            logger.error("[ComplianceValidatorNode] FAILED — %s", exc)
            return {"compliance_flags": [f"compliance_error:{exc}"], "compliance_retry_count": retry + 1}

    def node_feasibility(state: TrialState):
        logger.info("[FeasibilityScoringNode] START")
        try:
            score = _run_async(feasibility_scorer.compute(state.country_scores, state.site_scores, state.risk_scores, state.investigators, state.compliance_flags))
            logger.info("[FeasibilityScoringNode] END — score=%.4f", score)
            return {"feasibility_score": score}
        except Exception as exc:
            logger.error("[FeasibilityScoringNode] FAILED — %s", exc)
            return {"feasibility_score": 0.0}

    def node_report(state: TrialState):
        logger.info("[ReportGeneratorNode] START")
        try:
            report = _run_async(report_gen.generate(
                state.parsed_criteria, state.country_scores, state.site_scores,
                state.risk_scores, state.investigators, state.feasibility_score,
                state.compliance_flags, state.approval_status, state.human_feedback, state.sites,
            ))
            logger.info("[ReportGeneratorNode] END")
            return {"final_recommendation": report}
        except Exception as exc:
            logger.error("[ReportGeneratorNode] FAILED — %s", exc)
            return {"final_recommendation": {"error": str(exc)}}

    def node_human(state: TrialState):
        logger.info("[HumanReviewNode] START")
        try:
            action, feedback = reviewer.solicit_review(state.feasibility_score, state.compliance_flags, state.risk_scores)
            logger.info("[HumanReviewNode] END — action=%s", action)
            return {"approval_status": action, "human_feedback": feedback}
        except Exception as exc:
            logger.error("[HumanReviewNode] FAILED — %s", exc)
            return {"approval_status": "reject", "human_feedback": f"Review failed: {exc}"}

    # ── Build Graph ───────────────────────────────────────────────────────
    graph = StateGraph(TrialState)

    graph.add_node(NODE_PROTOCOL_PARSER, node_protocol_parser)
    graph.add_node(NODE_DATA_ENRICHMENT, node_enrichment)
    graph.add_node(NODE_COUNTRY_FEASIBILITY, node_country)
    graph.add_node(NODE_SITE_SELECTION, node_site)
    graph.add_node(NODE_INVESTIGATOR_MATCHING, node_investigator)
    graph.add_node(NODE_RISK_SCORING, node_risk)
    graph.add_node(NODE_COMPLIANCE_VALIDATOR, node_compliance)
    graph.add_node(NODE_FEASIBILITY_SCORING, node_feasibility)
    graph.add_node(NODE_REPORT_GENERATOR, node_report)
    graph.add_node(NODE_HUMAN_REVIEW, node_human)

    graph.set_entry_point(NODE_PROTOCOL_PARSER)

    # Static edges
    graph.add_edge(NODE_PROTOCOL_PARSER, NODE_DATA_ENRICHMENT)
    graph.add_edge(NODE_SITE_SELECTION, NODE_INVESTIGATOR_MATCHING)
    graph.add_edge(NODE_INVESTIGATOR_MATCHING, NODE_RISK_SCORING)
    graph.add_edge(NODE_REPORT_GENERATOR, END)

    # Conditional edges (closure captures config)
    graph.add_conditional_edges(
        NODE_DATA_ENRICHMENT,
        lambda s: _route_after_enrichment(s, config),
        {NODE_DATA_ENRICHMENT: NODE_DATA_ENRICHMENT, NODE_HUMAN_REVIEW: NODE_HUMAN_REVIEW, NODE_COUNTRY_FEASIBILITY: NODE_COUNTRY_FEASIBILITY},
    )
    graph.add_conditional_edges(
        NODE_COUNTRY_FEASIBILITY,
        _route_after_country,
        {_END: END, NODE_SITE_SELECTION: NODE_SITE_SELECTION},
    )
    graph.add_conditional_edges(
        NODE_RISK_SCORING,
        lambda s: _route_after_risk(s, config),
        {NODE_HUMAN_REVIEW: NODE_HUMAN_REVIEW, NODE_COMPLIANCE_VALIDATOR: NODE_COMPLIANCE_VALIDATOR},
    )
    graph.add_conditional_edges(
        NODE_COMPLIANCE_VALIDATOR,
        lambda s: _route_after_compliance(s, config),
        {NODE_COUNTRY_FEASIBILITY: NODE_COUNTRY_FEASIBILITY, _END: END, NODE_FEASIBILITY_SCORING: NODE_FEASIBILITY_SCORING},
    )
    graph.add_conditional_edges(
        NODE_FEASIBILITY_SCORING,
        lambda s: _route_after_feasibility(s, config),
        {NODE_SITE_SELECTION: NODE_SITE_SELECTION, NODE_HUMAN_REVIEW: NODE_HUMAN_REVIEW},
    )
    graph.add_conditional_edges(
        NODE_HUMAN_REVIEW,
        _route_after_human_review,
        {NODE_REPORT_GENERATOR: NODE_REPORT_GENERATOR, NODE_RISK_SCORING: NODE_RISK_SCORING, NODE_SITE_SELECTION: NODE_SITE_SELECTION},
    )

    compiled = graph.compile()
    logger.info("Graph (v2) compiled successfully.")
    return compiled
