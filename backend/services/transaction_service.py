"""
Transaction service for querying payment history from CSV.

Implements OR logic with case-insensitive search and deduplication.
"""

import logging
import time
from datetime import datetime
from pathlib import Path
import pandas as pd

from models.query_params import QueryParameters
from models.transaction import TransactionRecord, PaymentHistory
from config import settings

# Configure logging
logger = logging.getLogger(__name__)


class TransactionService:
    """Service for querying transaction data from CSV file."""

    def __init__(self, csv_path: str | None = None):
        """
        Initialize transaction service.

        Args:
            csv_path: Path to CSV file. Defaults to settings.csv_file_path
        """
        self.csv_path = csv_path or settings.csv_file_path
        self._df: pd.DataFrame | None = None

    def _load_csv(self) -> pd.DataFrame:
        """Load CSV file into pandas DataFrame (cached)."""
        if self._df is None:
            csv_file = Path(self.csv_path)
            if not csv_file.exists():
                raise FileNotFoundError(f"CSV file not found: {self.csv_path}")

            logger.info(f"Loading CSV file: {self.csv_path}")
            self._df = pd.read_csv(csv_file)
            logger.info(f"Loaded {len(self._df)} transactions from CSV")

        return self._df

    def query(self, params: QueryParameters) -> PaymentHistory:
        """
        Query transactions matching search criteria.

        Implements OR logic: returns transactions matching ANY provided identifier.
        Results are deduplicated by transaction_id.

        Args:
            params: Query parameters with optional filters

        Returns:
            PaymentHistory with matching transactions

        Raises:
            ValueError: If no filters provided
        """
        start_time = time.time()

        # Validate at least one filter provided
        if not params.has_filters:
            raise ValueError("At least one search parameter must be provided")

        # Load CSV data
        df = self._load_csv()

        # Build OR filters (case-insensitive)
        filters = []

        if params.originator_name:
            filters.append(
                df["originator_name"].str.lower() == params.originator_name.lower()
            )
            logger.debug(f"Filter: originator_name={params.originator_name}")

        if params.originator_account:
            filters.append(
                df["originator_account"].str.lower() == params.originator_account.lower()
            )
            logger.debug(f"Filter: originator_account={params.originator_account}")

        if params.beneficiary_name:
            filters.append(
                df["beneficiary_name"].str.lower() == params.beneficiary_name.lower()
            )
            logger.debug(f"Filter: beneficiary_name={params.beneficiary_name}")

        if params.beneficiary_account:
            filters.append(
                df["beneficiary_account"].str.lower() == params.beneficiary_account.lower()
            )
            logger.debug(f"Filter: beneficiary_account={params.beneficiary_account}")

        # Combine with OR logic
        combined_filter = filters[0]
        for f in filters[1:]:
            combined_filter = combined_filter | f

        # Apply filter and deduplicate by transaction_id
        result_df = df[combined_filter].drop_duplicates(subset=["transaction_id"])

        # Convert to TransactionRecord objects
        transactions = []
        for _, row in result_df.iterrows():
            try:
                # Convert row to dict and create TransactionRecord
                record_dict = row.to_dict()
                # Handle datetime parsing
                record_dict["booking_datetime"] = pd.to_datetime(record_dict["booking_datetime"])
                if pd.notna(record_dict.get("suspicion_determined_datetime")):
                    record_dict["suspicion_determined_datetime"] = pd.to_datetime(
                        record_dict["suspicion_determined_datetime"]
                    )
                if pd.notna(record_dict.get("str_filed_datetime")):
                    record_dict["str_filed_datetime"] = pd.to_datetime(record_dict["str_filed_datetime"])

                transaction = TransactionRecord(**record_dict)
                transactions.append(transaction)
            except Exception as e:
                logger.warning(f"Failed to parse transaction {row.get('transaction_id')}: {e}")
                continue

        # Calculate date range
        if transactions:
            dates = [t.booking_datetime for t in transactions]
            date_range = (min(dates), max(dates))
        else:
            date_range = (None, None)

        # Create PaymentHistory
        payment_history = PaymentHistory(
            transactions=transactions,
            total_count=len(transactions),
            date_range=date_range,
        )

        # Log query results
        execution_time = time.time() - start_time
        logger.info(
            f"Query completed: {len(transactions)} transactions found "
            f"(execution time: {execution_time:.3f}s)"
        )

        return payment_history


# Global service instance
transaction_service = TransactionService()
