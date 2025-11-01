"""
State definitions for LangGraph risk analysis workflow.

Defines TypedDict state objects passed between nodes.
"""

from typing import TypedDict


class RiskAnalysisState(TypedDict):
    """
    State for risk analysis LangGraph workflow.

    Flow: START → format_data → call_llm → parse_response/handle_error → validate_rules (optional) → END
    """

    # Input
    transactions: list[dict]  # TransactionRecords as dicts
    rules_data: dict | None  # RulesData as dict (optional, FR-012)

    # Intermediate
    formatted_prompt: str | None
    llm_raw_response: str | None

    # Output
    analysis_result: dict | None  # AnalysisResult as dict
    error: str | None
