"""Async LLM client with concurrency control and retry logic."""

from __future__ import annotations

import asyncio
import json
import logging

import httpx
from pydantic import ValidationError

from markdown_frontmatterer.config import Settings
from markdown_frontmatterer.models import Frontmatter
from markdown_frontmatterer.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)

_RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
_MAX_VALIDATION_RETRIES = 2
_DEFAULT_MAX_TOKENS = 4096


class LLMClient:
    """OpenAI-compatible async LLM client."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._semaphore = asyncio.Semaphore(settings.concurrency)
        self._client: httpx.AsyncClient | None = None

    async def __aenter__(self) -> LLMClient:
        self._client = httpx.AsyncClient(
            base_url=self._settings.llm_base_url,
            headers={"Authorization": f"Bearer {self._settings.llm_api_key}"},
            timeout=httpx.Timeout(60.0),
        )
        return self

    async def __aexit__(self, *exc: object) -> None:
        if self._client:
            await self._client.aclose()

    async def analyze(self, content: str, *, model: str | None = None) -> Frontmatter:
        """Send document content to LLM and return parsed Frontmatter.

        Retries up to _MAX_VALIDATION_RETRIES times on JSON/validation errors.
        Distinguishes truncation (finish_reason=length) from validation errors:
        - Truncation: retry with original messages (adding feedback would worsen it)
        - Validation: feed error back to LLM for self-correction
        """
        model = model or self._settings.llm_model
        user_prompt = build_user_prompt(content, max_chars=self._settings.llm_max_content_chars)

        base_messages: list[dict[str, str]] = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]
        messages = base_messages

        last_exc: Exception | None = None
        for attempt in range(_MAX_VALIDATION_RETRIES + 1):
            payload = {
                "model": model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.1,
                "max_tokens": _DEFAULT_MAX_TOKENS,
            }

            async with self._semaphore:
                data = await self._request_with_retry(payload)

            raw_text = data["choices"][0]["message"]["content"]
            finish_reason = data["choices"][0].get("finish_reason")

            try:
                return Frontmatter.model_validate_json(raw_text)
            except (ValidationError, json.JSONDecodeError) as exc:
                last_exc = exc
                if attempt < _MAX_VALIDATION_RETRIES:
                    if finish_reason == "length":
                        # Truncated — retry with original messages; adding the
                        # broken response would only increase input and worsen it.
                        logger.warning(
                            "Response truncated (attempt %d/%d), retrying",
                            attempt + 1,
                            _MAX_VALIDATION_RETRIES + 1,
                        )
                        messages = base_messages
                    else:
                        # Model finished but output is invalid — feed error back
                        logger.warning(
                            "Validation failed (attempt %d/%d): %s",
                            attempt + 1,
                            _MAX_VALIDATION_RETRIES + 1,
                            exc,
                        )
                        messages = [
                            *base_messages,
                            {"role": "assistant", "content": raw_text},
                            {
                                "role": "user",
                                "content": (
                                    f"Your previous response caused an error:\n{exc}\n\n"
                                    "Please return a corrected, complete JSON object."
                                ),
                            },
                        ]

        raise ValueError(
            f"LLM returned invalid output after {_MAX_VALIDATION_RETRIES + 1} attempts"
        ) from last_exc

    async def _request_with_retry(self, payload: dict) -> dict:
        """POST to /chat/completions with exponential backoff on retryable errors."""
        assert self._client is not None

        last_exc: Exception | None = None
        for attempt in range(self._settings.max_retries):
            try:
                resp = await self._client.post("/chat/completions", json=payload)
                if resp.status_code in _RETRYABLE_STATUS_CODES:
                    wait = 2**attempt
                    logger.warning(
                        "Server returned %d, retrying in %ds...",
                        resp.status_code,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code in _RETRYABLE_STATUS_CODES:
                    wait = 2**attempt
                    logger.warning(
                        "Server returned %d, retrying in %ds...",
                        exc.response.status_code,
                        wait,
                    )
                    await asyncio.sleep(wait)
                    last_exc = exc
                    continue
                raise
            except httpx.TransportError as exc:
                wait = 2**attempt
                logger.warning("Transport error: %s, retrying in %ds...", exc, wait)
                await asyncio.sleep(wait)
                last_exc = exc
                continue

        raise RuntimeError(
            f"LLM request failed after {self._settings.max_retries} retries"
        ) from last_exc
