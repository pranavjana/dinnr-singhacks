"""
Payment history API endpoints.

Provides endpoints for querying transaction data and performing risk analysis.
"""

import logging
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from models.query_params import QueryParameters
from models.transaction import PaymentHistory
from models.analysis_result import AnalysisResult
from models.rules import RulesData
from services.transaction_service import transaction_service
from agents.aml_monitoring.risk_analyzer import run_risk_analysis

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


# Request model for analysis endpoint
class AnalyzeRequest(BaseModel):
    """Request model for payment history analysis with optional rules."""

    query: QueryParameters = Field(..., description="Search criteria for transactions")
    rules_data: RulesData | None = Field(
        None, description="Optional regulatory rules for validation (FR-012, FR-013)"
    )


@router.post("/payment-history/query", response_model=PaymentHistory)
async def query_payment_history(query: QueryParameters) -> PaymentHistory:
    """
    Query payment history by customer identifiers.

    Uses OR logic: returns transactions matching ANY provided identifier.
    Results are deduplicated by transaction_id.

    Args:
        query: Search criteria (at least one field required)

    Returns:
        PaymentHistory with matching transactions

    Raises:
        HTTPException 400: If no search parameters provided
        HTTPException 404: If no transactions found
        HTTPException 500: If query execution fails
    """
    try:
        # Validate at least one filter provided (T016)
        if not query.has_filters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one search parameter must be provided",
            )

        # Execute query
        logger.info(f"Executing payment history query: {query.model_dump(exclude_none=True)}")
        payment_history = transaction_service.query(query)

        # Handle empty results (T017)
        if payment_history.is_empty:
            logger.info("Query returned no results")
            # Return empty result with informative message rather than 404
            # This allows client to distinguish between "no matches" vs "error"
            return PaymentHistory(
                transactions=[],
                total_count=0,
                date_range=(None, None),
            )

        logger.info(f"Query successful: {payment_history.total_count} transactions returned")
        return payment_history

    except ValueError as e:
        # Input validation errors
        logger.warning(f"Query validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileNotFoundError as e:
        # CSV file not found
        logger.error(f"CSV file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transaction data source not available",
        )
    except Exception as e:
        # Unexpected errors
        logger.error(f"Query execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Query execution failed: {str(e)}",
        )


@router.post("/payment-history/analyze", response_model=AnalysisResult)
async def analyze_payment_history(request: AnalyzeRequest) -> AnalysisResult:
    """
    Query payment history and perform LLM-powered risk analysis.

    Combines transaction retrieval with AI pattern detection and risk scoring.
    Uses LangGraph workflow with graceful degradation (FR-018).
    Supports optional rules validation (FR-012, FR-013).

    Args:
        request: Analysis request with query parameters and optional rules_data

    Returns:
        AnalysisResult with risk scores, flagged transactions, and patterns

    Raises:
        HTTPException 400: If no search parameters provided
        HTTPException 404: If no transactions found to analyze
        HTTPException 500: If query or analysis fails
    """
    try:
        query = request.query
        rules_data = request.rules_data

        # Validate at least one filter provided
        if not query.has_filters:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one search parameter must be provided",
            )

        # Execute query to retrieve transactions
        logger.info(
            f"Querying payment history for analysis: {query.model_dump(exclude_none=True)}"
            + (f" with rules validation" if rules_data else "")
        )
        payment_history = transaction_service.query(query)

        # Check if transactions found
        if payment_history.is_empty:
            logger.info("Query returned no results for analysis")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No transactions found matching query criteria",
            )

        # Run LangGraph risk analysis agent with optional rules
        logger.info(
            f"Running risk analysis on {payment_history.total_count} transactions"
            + (f" with {len(rules_data.threshold_rules) if rules_data else 0} threshold rules, "
               f"{len(rules_data.prohibited_jurisdictions) if rules_data else 0} jurisdiction rules"
               if rules_data else " (no rules validation)")
        )
        analysis_result = await run_risk_analysis(
            payment_history.transactions, rules_data=rules_data
        )

        # Log results
        if analysis_result.error:
            logger.warning(
                f"Analysis completed with error (graceful degradation): {analysis_result.error}"
            )
        else:
            logger.info(
                f"Analysis successful: risk_score={analysis_result.overall_risk_score}, "
                f"flagged={len(analysis_result.flagged_transactions)}, "
                f"patterns={len(analysis_result.identified_patterns)}"
            )

        return analysis_result

    except HTTPException:
        # Re-raise HTTP exceptions (already formatted)
        raise
    except ValueError as e:
        # Input validation errors
        logger.warning(f"Analysis validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except FileNotFoundError as e:
        # CSV file not found
        logger.error(f"CSV file not found: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Transaction data source not available",
        )
    except Exception as e:
        # Unexpected errors (note: LLM failures are handled gracefully within agent)
        logger.error(f"Analysis execution failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis execution failed: {str(e)}",
        )
