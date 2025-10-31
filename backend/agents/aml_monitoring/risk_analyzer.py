"""
LangGraph agent for AML risk analysis.

Orchestrates multi-step workflow: format → call LLM → parse → error handling.
"""

import json
import logging
from datetime import datetime

from langgraph.graph import StateGraph, END
from agents.aml_monitoring.states import RiskAnalysisState
from services.llm_client import grok_client
from models.transaction import TransactionRecord
from models.analysis_result import AnalysisResult, FlaggedTransaction, IdentifiedPattern
from models.rules import RulesData

# Configure logging
logger = logging.getLogger(__name__)


# ============================================================================
# Node Functions
# ============================================================================


def format_data(state: RiskAnalysisState) -> RiskAnalysisState:
    """
    Node: Transform transaction data into LLM-friendly prompt.

    Implements FR-007 (data formatting) and includes prompt engineering
    for pattern identification per FR-009.
    """
    logger.info(f"Formatting {len(state['transactions'])} transactions for LLM analysis")

    transactions = state["transactions"]

    # Build structured prompt with analysis instructions
    prompt = f"""# AML Risk Analysis Task

You are analyzing {len(transactions)} payment transactions for anti-money laundering compliance.

## Analysis Instructions

Identify suspicious patterns and flag high-risk transactions based on:

1. **Transaction Frequency**: Unusual volume or frequency patterns
2. **Amount Patterns**: Round amounts, structuring below thresholds, unusually large transfers
3. **High-Risk Jurisdictions**: Transactions involving sanctioned or high-risk countries
4. **PEP Involvement**: Transactions involving Politically Exposed Persons
5. **Sanctions Hits**: Confirmed or potential sanctions screening matches
6. **Similar Names**: Name variations that may indicate evasion (e.g., "John Smith" vs "Jon Smyth")
7. **Travel Rule Violations**: Missing required originator/beneficiary information
8. **KYC/EDD Issues**: Expired KYC, missing EDD when required, undocumented source of wealth
9. **FX Anomalies**: Unusual FX spreads or rates
10. **Product Suitability**: Complex products for low-risk clients, mismatches

## Transaction Data (JSON)

```json
{json.dumps(transactions, indent=2, default=str)}
```

## Required Output Format (JSON)

Respond with a valid JSON object matching this schema:

```json
{{
  "overall_risk_score": <float 0-10>,
  "risk_category": "<Low|Medium|High|Critical>",
  "flagged_transactions": [
    {{
      "transaction_id": "<transaction_id>",
      "reason": "<specific reason for flagging>",
      "risk_level": "<Low|Medium|High|Critical>"
    }}
  ],
  "identified_patterns": [
    {{
      "pattern_type": "<volume_spike|round_amounts|high_risk_jurisdiction|similar_names|etc>",
      "description": "<human-readable pattern description>",
      "affected_transactions": ["<transaction_id>", ...],
      "severity": "<Low|Medium|High>"
    }}
  ],
  "narrative_summary": "<concise summary of findings>",
  "analyzed_transaction_count": {len(transactions)},
  "analysis_timestamp": "{datetime.utcnow().isoformat()}Z"
}}
```

Provide your analysis as valid JSON only (no markdown, no preamble).
"""

    state["formatted_prompt"] = prompt
    logger.debug("Prompt formatted successfully")
    return state


async def call_llm(state: RiskAnalysisState) -> RiskAnalysisState:
    """
    Node: Call Grok Kimi 2 LLM with formatted prompt.

    Handles exceptions for graceful degradation (FR-018).
    """
    logger.info("Calling Grok Kimi 2 LLM for risk analysis")

    try:
        prompt = state["formatted_prompt"]
        transactions = state["transactions"]

        # Call LLM with retry logic
        response = await grok_client.analyze_transactions(transactions, prompt)

        state["llm_raw_response"] = json.dumps(response)
        state["error"] = None
        logger.info("LLM call completed successfully")

    except Exception as e:
        # Graceful degradation: capture error, continue to error handler
        logger.error(f"LLM call failed: {e}", exc_info=True)
        state["llm_raw_response"] = None
        state["error"] = f"LLM unavailable: {str(e)}"

    return state


def parse_response(state: RiskAnalysisState) -> RiskAnalysisState:
    """
    Node: Parse LLM response into AnalysisResult schema.

    Validates structured JSON output against Pydantic model.
    """
    logger.info("Parsing LLM response")

    try:
        raw_response = state["llm_raw_response"]
        if raw_response is None:
            raise ValueError("No LLM response to parse")

        # Parse JSON
        response_dict = json.loads(raw_response) if isinstance(raw_response, str) else raw_response

        # Validate against AnalysisResult schema
        # Add metadata fields if missing
        if "analyzed_transaction_count" not in response_dict:
            response_dict["analyzed_transaction_count"] = len(state["transactions"])
        if "analysis_timestamp" not in response_dict:
            response_dict["analysis_timestamp"] = datetime.utcnow().isoformat() + "Z"
        if "error" not in response_dict:
            response_dict["error"] = None

        # Validate with Pydantic
        analysis_result = AnalysisResult(**response_dict)
        state["analysis_result"] = analysis_result.model_dump()
        logger.info("LLM response parsed successfully")

    except Exception as e:
        logger.error(f"Failed to parse LLM response: {e}", exc_info=True)
        # Route to error handler
        state["analysis_result"] = None
        state["error"] = f"Failed to parse LLM output: {str(e)}"

    return state


def handle_error(state: RiskAnalysisState) -> RiskAnalysisState:
    """
    Node: Handle LLM failures with graceful degradation.

    Creates partial AnalysisResult with error field populated (FR-018).
    """
    logger.warning("Handling LLM error with graceful degradation")

    error_message = state.get("error") or "Unknown error during analysis"

    # Create partial result with error
    partial_result = AnalysisResult(
        overall_risk_score=None,
        risk_category=None,
        flagged_transactions=[],
        identified_patterns=[],
        narrative_summary=f"Analysis could not be completed: {error_message}. Transaction data is available but LLM analysis failed.",
        analyzed_transaction_count=len(state["transactions"]),
        analysis_timestamp=datetime.utcnow(),
        error=error_message,
    )

    state["analysis_result"] = partial_result.model_dump()
    logger.info("Created partial analysis result with error information")
    return state


def validate_rules(state: RiskAnalysisState) -> RiskAnalysisState:
    """
    Node: Apply regulatory rules validation to transactions (FR-012, FR-013).

    Validates transactions against:
    - Threshold rules (amount limits)
    - Prohibited jurisdictions (sanctions, high-risk countries)
    - Documentation requirements (KYC, EDD, SOW)

    Merges rule violations with LLM analysis results (FR-013).
    If rules_data is None, skips validation (graceful degradation).
    """
    rules_data_dict = state.get("rules_data")

    # Graceful degradation: skip if no rules provided
    if rules_data_dict is None:
        logger.info("No rules data provided, skipping rules validation (graceful degradation)")
        return state

    try:
        # Parse rules data
        rules_data = RulesData(**rules_data_dict)

        # Check if rules are empty
        if rules_data.is_empty:
            logger.info("Rules data is empty, skipping validation")
            return state

        logger.info(
            f"Validating transactions against {len(rules_data.threshold_rules)} threshold rules, "
            f"{len(rules_data.prohibited_jurisdictions)} jurisdiction rules, "
            f"{len(rules_data.documentation_requirements)} documentation rules"
        )

        # Get current analysis result
        analysis_dict = state.get("analysis_result")
        if analysis_dict is None:
            logger.warning("No analysis result to merge rules with, skipping validation")
            return state

        analysis_result = AnalysisResult(**analysis_dict)
        transactions = state["transactions"]

        # Track rule violations
        rule_violations: list[FlaggedTransaction] = []
        rule_patterns: list[IdentifiedPattern] = []

        # 1. Check threshold rules
        for rule in rules_data.threshold_rules:
            violated_tx_ids = []
            for tx in transactions:
                if (
                    tx.get("currency") == rule.currency
                    and float(tx.get("amount", 0)) > float(rule.threshold_amount)
                ):
                    violated_tx_ids.append(tx["transaction_id"])
                    rule_violations.append(
                        FlaggedTransaction(
                            transaction_id=tx["transaction_id"],
                            reason=f"Exceeds {rule.rule_name}: {tx.get('amount')} {rule.currency} > {rule.threshold_amount} {rule.currency}",
                            risk_level=rule.violation_severity,
                        )
                    )

            if violated_tx_ids:
                rule_patterns.append(
                    IdentifiedPattern(
                        pattern_type="threshold_violation",
                        description=f"Threshold rule violation: {rule.rule_name}",
                        affected_transactions=violated_tx_ids,
                        severity=rule.violation_severity,
                    )
                )

        # 2. Check prohibited jurisdictions
        prohibited_country_codes = {j.country_code for j in rules_data.prohibited_jurisdictions}
        if prohibited_country_codes:
            violated_tx_ids = []
            for tx in transactions:
                originator_country = tx.get("originator_country")
                beneficiary_country = tx.get("beneficiary_country")

                if originator_country in prohibited_country_codes:
                    violated_tx_ids.append(tx["transaction_id"])
                    jurisdiction = next(
                        (j for j in rules_data.prohibited_jurisdictions if j.country_code == originator_country),
                        None,
                    )
                    rule_violations.append(
                        FlaggedTransaction(
                            transaction_id=tx["transaction_id"],
                            reason=f"Originator from prohibited jurisdiction: {jurisdiction.country_name if jurisdiction else originator_country}",
                            risk_level=jurisdiction.risk_level if jurisdiction else "High",
                        )
                    )

                if beneficiary_country in prohibited_country_codes:
                    violated_tx_ids.append(tx["transaction_id"])
                    jurisdiction = next(
                        (j for j in rules_data.prohibited_jurisdictions if j.country_code == beneficiary_country),
                        None,
                    )
                    rule_violations.append(
                        FlaggedTransaction(
                            transaction_id=tx["transaction_id"],
                            reason=f"Beneficiary in prohibited jurisdiction: {jurisdiction.country_name if jurisdiction else beneficiary_country}",
                            risk_level=jurisdiction.risk_level if jurisdiction else "High",
                        )
                    )

            if violated_tx_ids:
                rule_patterns.append(
                    IdentifiedPattern(
                        pattern_type="prohibited_jurisdiction",
                        description="Transactions involving prohibited or high-risk jurisdictions",
                        affected_transactions=list(set(violated_tx_ids)),  # Deduplicate
                        severity="High",
                    )
                )

        # 3. Check documentation requirements
        for req in rules_data.documentation_requirements:
            violated_tx_ids = []
            for tx in transactions:
                product_type = tx.get("product_type")
                if product_type in req.applies_to_product_types:
                    # Check if required documentation is present
                    missing_docs = []
                    if "edd_report" in req.required_documents and not tx.get("edd_performed"):
                        missing_docs.append("EDD")
                    if "source_of_wealth" in req.required_documents and not tx.get("sow_documented"):
                        missing_docs.append("Source of Wealth")

                    if missing_docs:
                        violated_tx_ids.append(tx["transaction_id"])
                        rule_violations.append(
                            FlaggedTransaction(
                                transaction_id=tx["transaction_id"],
                                reason=f"Missing required documentation: {', '.join(missing_docs)} ({req.requirement_name})",
                                risk_level=req.violation_severity,
                            )
                        )

            if violated_tx_ids:
                rule_patterns.append(
                    IdentifiedPattern(
                        pattern_type="documentation_violation",
                        description=f"Documentation requirement violation: {req.requirement_name}",
                        affected_transactions=violated_tx_ids,
                        severity=req.violation_severity,
                    )
                )

        # Merge rule violations with LLM analysis (FR-013)
        logger.info(
            f"Rules validation found {len(rule_violations)} violations and {len(rule_patterns)} patterns"
        )

        # Append rule violations to flagged transactions
        merged_flagged = analysis_result.flagged_transactions + rule_violations

        # Append rule patterns to identified patterns
        merged_patterns = analysis_result.identified_patterns + rule_patterns

        # Update risk score if rule violations found
        updated_risk_score = analysis_result.overall_risk_score
        if rule_violations and updated_risk_score is not None:
            # Increase risk score by 10% for each high/critical rule violation
            high_severity_count = sum(
                1 for v in rule_violations if v.risk_level in ["High", "Critical"]
            )
            score_increase = min(high_severity_count * 0.5, 2.0)  # Cap at +2.0
            updated_risk_score = min(updated_risk_score + score_increase, 10.0)
            logger.info(
                f"Risk score increased from {analysis_result.overall_risk_score} to {updated_risk_score} due to rule violations"
            )

        # Update risk category if needed
        updated_risk_category = analysis_result.risk_category
        if updated_risk_score is not None:
            if updated_risk_score >= 8.0:
                updated_risk_category = "Critical"
            elif updated_risk_score >= 6.0:
                updated_risk_category = "High"
            elif updated_risk_score >= 4.0:
                updated_risk_category = "Medium"
            else:
                updated_risk_category = "Low"

        # Create updated analysis result
        updated_result = AnalysisResult(
            overall_risk_score=updated_risk_score,
            risk_category=updated_risk_category,
            flagged_transactions=merged_flagged,
            identified_patterns=merged_patterns,
            narrative_summary=analysis_result.narrative_summary
            + (
                f"\n\nRegulatory Rules Validation: {len(rule_violations)} rule violations detected across {len(rule_patterns)} violation types."
                if rule_violations
                else "\n\nRegulatory Rules Validation: No rule violations detected."
            ),
            analyzed_transaction_count=analysis_result.analyzed_transaction_count,
            analysis_timestamp=analysis_result.analysis_timestamp,
            error=analysis_result.error,
        )

        state["analysis_result"] = updated_result.model_dump()
        logger.info("Rules validation complete, results merged with LLM analysis")

    except Exception as e:
        logger.error(f"Rules validation failed: {e}", exc_info=True)
        # Don't fail entire workflow, just log and continue
        logger.warning("Continuing without rules validation due to error")

    return state


# ============================================================================
# Conditional Routing
# ============================================================================


def route_after_llm(state: RiskAnalysisState) -> str:
    """
    Conditional edge: Route to parse_response or handle_error based on LLM success.
    """
    if state.get("error") is not None:
        logger.debug("Routing to handle_error node")
        return "handle_error"
    else:
        logger.debug("Routing to parse_response node")
        return "parse_response"


def route_after_parse(state: RiskAnalysisState) -> str:
    """
    Conditional edge: Route to validate_rules, END, or handle_error based on parse success.
    """
    if state.get("analysis_result") is not None and state.get("error") is None:
        # Check if rules data provided
        if state.get("rules_data") is not None:
            logger.debug("Routing to validate_rules node")
            return "validate_rules"
        else:
            logger.debug("Routing to END (no rules to validate)")
            return END
    else:
        logger.debug("Routing to handle_error node")
        return "handle_error"


# ============================================================================
# StateGraph Construction
# ============================================================================


def create_risk_analysis_graph() -> StateGraph:
    """
    Create LangGraph StateGraph for risk analysis workflow.

    Flow:
    START → format_data → call_llm → [conditional]
                                     ├─ parse_response → [conditional]
                                     │                   ├─ validate_rules → END (if rules provided)
                                     │                   ├─ END (no rules)
                                     │                   └─ handle_error → END
                                     └─ handle_error → END
    """
    workflow = StateGraph(RiskAnalysisState)

    # Add nodes
    workflow.add_node("format_data", format_data)
    workflow.add_node("call_llm", call_llm)
    workflow.add_node("parse_response", parse_response)
    workflow.add_node("handle_error", handle_error)
    workflow.add_node("validate_rules", validate_rules)

    # Set entry point
    workflow.set_entry_point("format_data")

    # Add edges
    workflow.add_edge("format_data", "call_llm")
    workflow.add_conditional_edges("call_llm", route_after_llm)
    workflow.add_conditional_edges("parse_response", route_after_parse)
    workflow.add_edge("handle_error", END)
    workflow.add_edge("validate_rules", END)

    logger.debug("Risk analysis StateGraph created with rules validation")
    return workflow


# ============================================================================
# Public API
# ============================================================================


async def run_risk_analysis(
    transactions: list[TransactionRecord], rules_data: RulesData | None = None
) -> AnalysisResult:
    """
    Execute risk analysis workflow on transaction list.

    Entry point for running LangGraph agent on payment history.

    Args:
        transactions: List of TransactionRecord objects to analyze
        rules_data: Optional regulatory rules for validation (FR-012). If None, rules validation is skipped.

    Returns:
        AnalysisResult with risk scores, flagged transactions, patterns, and summary

    Raises:
        ValueError: If transactions list is empty
    """
    if not transactions:
        raise ValueError("Cannot analyze empty transaction list")

    logger.info(
        f"Starting risk analysis workflow for {len(transactions)} transactions"
        + (f" with rules validation" if rules_data else " (no rules validation)")
    )

    # Convert TransactionRecords to dicts for LLM
    transaction_dicts = [t.model_dump(mode="json") for t in transactions]

    # Convert rules_data to dict if provided
    rules_dict = rules_data.model_dump() if rules_data else None

    # Initialize state
    initial_state: RiskAnalysisState = {
        "transactions": transaction_dicts,
        "rules_data": rules_dict,
        "formatted_prompt": None,
        "llm_raw_response": None,
        "analysis_result": None,
        "error": None,
    }

    # Create and compile graph
    graph = create_risk_analysis_graph()
    compiled_graph = graph.compile()

    # Execute workflow
    logger.info("Executing LangGraph workflow")
    final_state = await compiled_graph.ainvoke(initial_state)

    # Extract result
    analysis_dict = final_state["analysis_result"]
    if analysis_dict is None:
        # Should not happen (handle_error creates partial result), but handle defensively
        logger.error("Workflow completed but analysis_result is None")
        return AnalysisResult(
            overall_risk_score=None,
            risk_category=None,
            flagged_transactions=[],
            identified_patterns=[],
            narrative_summary="Analysis workflow failed unexpectedly",
            analyzed_transaction_count=len(transactions),
            analysis_timestamp=datetime.utcnow(),
            error="Workflow error: no result produced",
        )

    result = AnalysisResult(**analysis_dict)
    logger.info(
        f"Risk analysis completed: overall_risk_score={result.overall_risk_score}, "
        f"flagged_transactions={len(result.flagged_transactions)}, "
        f"patterns={len(result.identified_patterns)}"
    )
    return result
