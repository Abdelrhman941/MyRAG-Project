import logging
from typing import Any

import httpx

from ...core import Settings
from ...core.exceptions import AppError

logger = logging.getLogger(__name__)


class LLMProviderError(AppError):
    status_code = 502
    code = "llm_provider_error"
    message = "The LLM provider encountered an error."


class OpenAICompatibleLLM:
    """Adapter for OpenAI-compatible chat completions API."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.headers = {
            "Authorization": f"Bearer {self.settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        self.base_url = self.settings.LLM_BASE_URL.rstrip("/")
        if not self.base_url.endswith("/chat/completions"):
            self.endpoint = f"{self.base_url}/chat/completions"
        else:
            self.endpoint = self.base_url

    async def _call_api(
        self, client: httpx.AsyncClient, payload: dict[str, Any]
    ) -> httpx.Response:
        return await client.post(
            self.endpoint,
            headers=self.headers,
            json=payload,
            timeout=self.settings.LLM_TIMEOUT_S,
        )

    async def generate(
        self, messages: list[dict[str, str]], temperature: float = 0.7
    ) -> str:
        payload = {
            "model": self.settings.LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await self._call_api(client, payload)
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                if e.response.status_code >= 500:
                    logger.warning(f"LLM Provider 5xx error, retrying once: {e}")
                    try:
                        response = await self._call_api(client, payload)
                        response.raise_for_status()
                    except Exception as retry_e:
                        logger.error(f"LLM Provider retry failed: {retry_e}")
                        raise LLMProviderError() from retry_e
                else:
                    logger.error(f"LLM Provider 4xx error: {e.response.text}")
                    raise LLMProviderError() from e
            except httpx.RequestError as e:
                logger.warning(f"LLM Provider network error, retrying once: {e}")
                try:
                    response = await self._call_api(client, payload)
                    response.raise_for_status()
                except Exception as retry_e:
                    logger.error(f"LLM Provider retry failed: {retry_e}")
                    raise LLMProviderError() from retry_e

        try:
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {response.text}")
            raise LLMProviderError(
                message="Malformed response from LLM provider"
            ) from e
