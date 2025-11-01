"""
LLM client for Groq API integration.

Provides async client for transaction analysis with retry logic.
"""

import logging
import asyncio
from typing import Any
from groq import Groq
from groq.types.chat import ChatCompletion

from config import settings

# Configure logging
logger = logging.getLogger(__name__)


class GroqClient:
    """
    Client for Groq LLM API.

    Features:
    - Structured responses
    - Retry logic with exponential backoff
    - Graceful error handling
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize Groq client.

        Args:
            api_key: Groq API key. Defaults to settings.groq_api_key
        """
        self.api_key = api_key or settings.groq_api_key
        self.client = Groq(api_key=self.api_key)
        self.model = settings.groq_model
        self.max_retries = 3
        self.initial_retry_delay = 1.0  # seconds

    async def analyze_transactions(
        self, transactions: list[dict], prompt: str
    ) -> dict[str, Any]:
        """
        Analyze transactions using Groq LLM.

        Args:
            transactions: List of transaction records as dicts
            prompt: Formatted analysis prompt with instructions

        Returns:
            Dict with LLM response (should conform to AnalysisResult schema)

        Raises:
            Exception: If API call fails after retries
            ValueError: If response is malformed
        """
        logger.info(f"Analyzing {len(transactions)} transactions with Groq")

        # Build messages array
        messages = [
            {
                "role": "system",
                "content": "You are an AML compliance expert analyzing financial transactions. "
                "Always respond with valid JSON matching the requested schema.",
            },
            {"role": "user", "content": prompt},
        ]

        # Execute with retry logic
        for attempt in range(self.max_retries):
            try:
                completion: ChatCompletion = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.3,  # Lower temperature for more consistent output
                )

                content = completion.choices[0].message.content
                logger.info("LLM analysis completed successfully")

                # Parse JSON content
                import json
                analysis_result = json.loads(content)
                return analysis_result

            except Exception as e:
                logger.warning(
                    f"LLM API request failed (attempt {attempt + 1}/{self.max_retries}): {e}"
                )
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logger.error("LLM API request failed after all retries")
                    raise


# Global client instance
grok_client = GroqClient()
