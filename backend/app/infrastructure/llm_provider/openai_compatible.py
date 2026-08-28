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

    def __init__(self, settings: Settings, client: httpx.AsyncClient):
        self.settings = settings
        self.client = client
        self.headers = {
            "Authorization": f"Bearer {self.settings.LLM_API_KEY}",
            "Content-Type": "application/json",
        }
        self.base_url = self.settings.LLM_BASE_URL.rstrip("/")
        if not self.base_url.endswith("/chat/completions"):
            self.endpoint = f"{self.base_url}/chat/completions"
        else:
            self.endpoint = self.base_url

    async def _call_api(self, payload: dict[str, Any]) -> httpx.Response:
        return await self.client.post(
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

        try:
            response = await self._call_api(payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            if e.response.status_code >= 500:
                logger.warning(f"LLM Provider 5xx error, retrying once: {e}")
                try:
                    response = await self._call_api(payload)
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
                response = await self._call_api(payload)
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

    async def _stream_attempt(self, payload: dict[str, Any]) -> Any:
        import json

        async with self.client.stream(
            "POST",
            self.endpoint,
            headers=self.headers,
            json=payload,
            timeout=self.settings.LLM_TIMEOUT_S,
        ) as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue

                data_str = line[len("data: ") :]
                if data_str == "[DONE]":
                    break

                try:
                    chunk = json.loads(data_str)
                    choices = chunk.get("choices", [])
                    if choices:
                        delta = choices[0].get("delta", {})
                        if "content" in delta and delta["content"] is not None:
                            yield delta["content"]
                except json.JSONDecodeError:
                    logger.warning(f"Failed to parse SSE data: {data_str}")
                    continue

    async def generate_stream(
        self, messages: list[dict[str, str]], temperature: float = 0.7
    ) -> Any:
        payload = {
            "model": self.settings.LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        tokens_emitted = 0
        max_retries = 3

        import asyncio

        for attempt in range(max_retries):
            try:
                async for token in self._stream_attempt(payload):
                    tokens_emitted += 1
                    yield token
                break  # Success
            except Exception as e:
                if tokens_emitted > 0:
                    logger.error(f"LLM stream failed mid-stream: {e}")
                    raise LLMProviderError() from e

                if attempt < max_retries - 1:
                    wait_time = 2**attempt  # 1s, 2s
                    logger.warning(
                        "LLM stream failed before tokens (attempt %d/%d), "
                        "retrying in %ds: %s",
                        attempt + 1,
                        max_retries,
                        wait_time,
                        e,
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(
                        "LLM stream failed after %d attempts: %s", max_retries, e
                    )
                    raise LLMProviderError() from e
