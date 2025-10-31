"""
LLM client for Grok Kimi 2 API integration.

Provides async HTTP client for transaction analysis with retry logic.
"""

import logging
import asyncio
from typing import Any
import httpx

from config import settings

# Configure logging
logger = logging.getLogger(__name__)


class GrokClient:
    """
    Async HTTP client for Grok Kimi 2 API.

    Features:
    - JSON mode output for structured responses
    - Retry logic with exponential backoff
    - Graceful error handling for FR-018
    """

    def __init__(self, api_key: str | None = None):
        """
        Initialize Grok client.

        Args:
            api_key: Grok API key. Defaults to settings.grok_api_key
        """
        self.api_key = api_key or settings.grok_api_key
        self.base_url = "https://api.x.ai/v1"
        self.max_retries = 3
        self.initial_retry_delay = 1.0  # seconds

    async def analyze_transactions(
        self, transactions: list[dict], prompt: str
    ) -> dict[str, Any]:
        """
        Analyze transactions using Grok Kimi 2 LLM.

        Args:
            transactions: List of transaction records as dicts
            prompt: Formatted analysis prompt with instructions

        Returns:
            Dict with LLM response (should conform to AnalysisResult schema)

        Raises:
            httpx.HTTPError: If API call fails after retries
            ValueError: If response is malformed
        """
        logger.info(f"Analyzing {len(transactions)} transactions with Grok Kimi 2")

        # Build request payload
        payload = {
            "model": "grok-2-1212",  # Grok Kimi 2 model identifier
            "messages": [
                {
                    "role": "system",
                    "content": "You are an AML compliance expert analyzing financial transactions. "
                    "Always respond with valid JSON matching the requested schema.",
                },
                {"role": "user", "content": prompt},
            ],
            "response_format": {"type": "json_object"},  # Request JSON mode
            "temperature": 0.3,  # Lower temperature for more consistent structured output
        }

        # Execute with retry logic
        for attempt in range(self.max_retries):
            try:
                async with httpx.AsyncClient(timeout=60.0) as client:
                    response = await client.post(
                        f"{self.base_url}/chat/completions",
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json",
                        },
                    )
                    response.raise_for_status()

                    # Parse response
                    result = response.json()
                    if "choices" not in result or len(result["choices"]) == 0:
                        raise ValueError("LLM response missing 'choices' field")

                    content = result["choices"][0]["message"]["content"]
                    logger.info("LLM analysis completed successfully")

                    # Parse JSON content
                    import json

                    analysis_result = json.loads(content)
                    return analysis_result

            except httpx.HTTPStatusError as e:
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

            except (httpx.RequestError, ValueError, KeyError) as e:
                logger.error(f"LLM request error: {e}")
                if attempt < self.max_retries - 1:
                    delay = self.initial_retry_delay * (2**attempt)
                    await asyncio.sleep(delay)
                else:
                    raise


# Global client instance
grok_client = GrokClient()
