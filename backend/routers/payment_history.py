"""
Payment history API endpoints.

Provides endpoints for querying transaction data and performing risk analysis.
"""

import logging
from fastapi import APIRouter, HTTPException, status

from models.query_params import QueryParameters
from models.transaction import PaymentHistory
from services.transaction_service import transaction_service

# Configure logging
logger = logging.getLogger(__name__)

router = APIRouter()


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
