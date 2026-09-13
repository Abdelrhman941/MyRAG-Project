from __future__ import annotations

import asyncio
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

import httpx

from ...core import Settings
from ...core.exceptions import LLMProviderError

logger = logging.getLogger(__name__)


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

    async def _retry_backoff(
        self, attempt: int, max_retries: int, error: Exception
    ) -> None:
        if attempt < max_retries - 1:
            wait_time = 2**attempt
            logger.warning(
                "LLM Provider error (attempt %d/%d), retrying in %ds: %s",
                attempt + 1,
                max_retries,
                wait_time,
                error,
            )
            await asyncio.sleep(wait_time)
        else:
            logger.error(
                "LLM Provider failed after %d attempts: %s", max_retries, error
            )
            raise LLMProviderError() from error

    def _log_client_error(self, e: httpx.HTTPStatusError) -> None:
        """Log a 4xx provider error without touching a streaming response body.

        Never reads ``e.response.text`` here: on streaming responses the body
        may be unread, and accessing it raises ``httpx.ResponseNotRead`` —
        which used to mask the original provider error behind a second
        traceback.
        """
        status = e.response.status_code
        if status == 404:
            # With a correct completions URL, a 404 from an OpenAI-compatible
            # provider almost always means the model id no longer exists
            # (renamed/retired), not a bad endpoint.
            logger.error(
                "LLM provider returned 404 — model '%s' was not found at %s. "
                "It was likely renamed or retired by the provider; check "
                "LLM_MODEL against the provider's current model list.",
                self.settings.LLM_MODEL,
                self.settings.LLM_BASE_URL,
            )
            return
        logger.error("LLM Provider %s error: %s", status, e)

    async def generate(
        self, messages: list[dict[str, str]], temperature: float = 0.7
    ) -> str:
        payload = {
            "model": self.settings.LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
        }

        max_retries = self.settings.LLM_MAX_RETRIES
        for attempt in range(max_retries):
            try:
                response = await self._call_api(payload)
                response.raise_for_status()
                break
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500:
                    # Non-streaming responses are fully read, so .text is safe.
                    if e.response.status_code == 404:
                        self._log_client_error(e)
                    else:
                        logger.error(
                            "LLM Provider %s error: %s",
                            e.response.status_code,
                            e.response.text[:1000],
                        )
                    raise LLMProviderError() from e
                await self._retry_backoff(attempt, max_retries, e)
            except Exception as e:
                await self._retry_backoff(attempt, max_retries, e)
        else:
            # _retry_backoff raises on the final attempt, so this line is
            # unreachable at runtime — it exists so the type checker can prove
            # `response` is bound below (fixes "response is possibly unbound").
            raise LLMProviderError()

        try:
            data = response.json()
            return str(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, ValueError) as e:
            logger.error(f"Failed to parse LLM response: {response.text}")
            raise LLMProviderError(
                message="Malformed response from LLM provider"
            ) from e

    async def _stream_attempt(
        self, payload: dict[str, Any]
    ) -> AsyncGenerator[str, None]:
        async with self.client.stream(
            "POST",
            self.endpoint,
            headers=self.headers,
            json=payload,
            timeout=self.settings.LLM_TIMEOUT_S,
        ) as response:
            if response.status_code >= 400:
                # Read the error body BEFORE the stream context closes and
                # BEFORE raise_for_status(). Accessing response.text on an
                # unread streaming response raises httpx.ResponseNotRead,
                # which used to hide the real provider error.
                body = (await response.aread()).decode("utf-8", errors="replace")
                raise httpx.HTTPStatusError(
                    f"HTTP {response.status_code}: {body[:500]}",
                    request=response.request,
                    response=response,
                )

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
    ) -> AsyncGenerator[str, None]:
        payload = {
            "model": self.settings.LLM_MODEL,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        tokens_emitted = 0
        max_retries = self.settings.LLM_MAX_RETRIES

        for attempt in range(max_retries):
            try:
                async for token in self._stream_attempt(payload):
                    tokens_emitted += 1
                    yield token
                return  # Success
            except httpx.HTTPStatusError as e:
                if e.response.status_code < 500:
                    self._log_client_error(e)
                    raise LLMProviderError() from e
                if tokens_emitted > 0:
                    logger.error(f"LLM stream failed mid-stream: {e}")
                    raise LLMProviderError() from e
                await self._retry_backoff(attempt, max_retries, e)
            except Exception as e:
                if tokens_emitted > 0:
                    logger.error(f"LLM stream failed mid-stream: {e}")
                    raise LLMProviderError() from e
                await self._retry_backoff(attempt, max_retries, e)
