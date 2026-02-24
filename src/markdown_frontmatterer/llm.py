"""Async LLM client with concurrency control and retry logic."""

from __future__ import annotations

import asyncio
import json
import logging

import httpx

from markdown_frontmatterer.config import Settings
from markdown_frontmatterer.models import Frontmatter
from markdown_frontmatterer.prompts import SYSTEM_PROMPT, build_user_prompt

logger = logging.getLogger(__name__)


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
        """Send document content to LLM and return parsed Frontmatter."""
        model = model or self._settings.llm_model
        user_prompt = build_user_prompt(content, max_chars=self._settings.llm_max_content_chars)

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        }

        async with self._semaphore:
            data = await self._request_with_retry(payload)

        raw_text = data["choices"][0]["message"]["content"]
        return Frontmatter.model_validate_json(raw_text)

    async def _request_with_retry(self, payload: dict) -> dict:
        """POST to /chat/completions with exponential backoff on 429."""
        assert self._client is not None

        last_exc: Exception | None = None
        for attempt in range(self._settings.max_retries):
            try:
                resp = await self._client.post("/chat/completions", json=payload)
                if resp.status_code == 429:
                    wait = 2**attempt
                    logger.warning("Rate limited (429), retrying in %ds...", wait)
                    await asyncio.sleep(wait)
                    continue
                resp.raise_for_status()
                return resp.json()
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    wait = 2**attempt
                    logger.warning("Rate limited (429), retrying in %ds...", wait)
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
