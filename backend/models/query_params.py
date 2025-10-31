"""
Query parameters model for payment history searches.

Supports OR logic: returns transactions matching ANY provided identifier.
"""

from pydantic import BaseModel, Field


class QueryParameters(BaseModel):
    """
    Search criteria for querying payment history.
    Supports OR logic: returns transactions matching ANY provided field.
    """

    originator_name: str | None = Field(
        None,
        description="Originator name (case-insensitive exact match)",
        example="Jennifer Parker",
    )
    originator_account: str | None = Field(
        None,
        description="Originator account number (case-insensitive exact match)",
        example="GB39OOLA52427580832378",
    )
    beneficiary_name: str | None = Field(
        None,
        description="Beneficiary name (case-insensitive exact match)",
        example="George Brown",
    )
    beneficiary_account: str | None = Field(
        None,
        description="Beneficiary account number (case-insensitive exact match)",
        example="GB88KUDJ48147748190437",
    )

    @property
    def has_filters(self) -> bool:
        """Check if at least one filter is provided."""
        return any([
            self.originator_name,
            self.originator_account,
            self.beneficiary_name,
            self.beneficiary_account,
        ])

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "originator_name": "Jennifer Parker",
                    "beneficiary_account": "GB88KUDJ48147748190437",
                }
            ]
        }
    }
