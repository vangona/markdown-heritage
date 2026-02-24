"""Tests for LLM client using respx mocks."""

from __future__ import annotations

import json

import httpx
import pytest
import respx

from markdown_frontmatterer.config import Settings
from markdown_frontmatterer.llm import LLMClient

MOCK_RESPONSE = {
    "title": "Python 비동기 가이드",
    "tags": ["python", "async", "httpx"],
    "category": "technology",
    "doc_type": "tutorial",
    "summary": "Python asyncio를 사용한 비동기 프로그래밍 가이드",
    "entities": [{"name": "김철수", "type": "person"}],
    "related_topics": ["web-development", "concurrency"],
}


def _make_settings(**overrides) -> Settings:
    return Settings(
        llm_api_key="test-key",
        llm_base_url="https://test-api.example.com/v1",
        llm_model="test-model",
        concurrency=2,
        max_retries=2,
        **overrides,
    )


def _chat_response(content: dict | str) -> httpx.Response:
    text = content if isinstance(content, str) else json.dumps(content)
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": text}}],
        },
    )


@pytest.mark.asyncio
@respx.mock
async def test_analyze_success() -> None:
    respx.post("https://test-api.example.com/v1/chat/completions").mock(
        return_value=_chat_response(MOCK_RESPONSE)
    )

    async with LLMClient(_make_settings()) as client:
        result = await client.analyze("# Test document\nSome content")

    assert result.title == "Python 비동기 가이드"
    assert result.category == "technology"
    assert result.doc_type == "tutorial"
    assert len(result.entities) == 1
    assert result.entities[0].name == "김철수"


@pytest.mark.asyncio
@respx.mock
async def test_analyze_retry_on_429() -> None:
    route = respx.post("https://test-api.example.com/v1/chat/completions")
    route.side_effect = [
        httpx.Response(429, text="rate limited"),
        _chat_response(MOCK_RESPONSE),
    ]

    async with LLMClient(_make_settings()) as client:
        result = await client.analyze("# Test")

    assert result.title == "Python 비동기 가이드"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_analyze_fails_after_retries() -> None:
    respx.post("https://test-api.example.com/v1/chat/completions").mock(
        return_value=httpx.Response(429, text="rate limited")
    )

    async with LLMClient(_make_settings()) as client:
        with pytest.raises(RuntimeError, match="failed after 2 retries"):
            await client.analyze("# Test")


# --- 5xx retry ---


@pytest.mark.asyncio
@respx.mock
async def test_retry_on_502() -> None:
    route = respx.post("https://test-api.example.com/v1/chat/completions")
    route.side_effect = [
        httpx.Response(502, text="bad gateway"),
        _chat_response(MOCK_RESPONSE),
    ]

    async with LLMClient(_make_settings()) as client:
        result = await client.analyze("# Test")

    assert result.title == "Python 비동기 가이드"
    assert route.call_count == 2


# --- Validation retry ---


@pytest.mark.asyncio
@respx.mock
async def test_validation_retry_on_truncated_json() -> None:
    """Truncated JSON on first attempt → corrected on retry."""
    route = respx.post("https://test-api.example.com/v1/chat/completions")
    route.side_effect = [
        _chat_response('{"title": "Test", "tags": ["a"]'),  # truncated
        _chat_response(MOCK_RESPONSE),  # corrected
    ]

    async with LLMClient(_make_settings()) as client:
        result = await client.analyze("# Test")

    assert result.title == "Python 비동기 가이드"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_validation_retry_on_bad_enum() -> None:
    """Invalid enum that BeforeValidator can't fix → retry with error feedback."""
    bad_response = {**MOCK_RESPONSE, "created_at": "not-a-date"}
    route = respx.post("https://test-api.example.com/v1/chat/completions")
    route.side_effect = [
        _chat_response(bad_response),
        _chat_response(MOCK_RESPONSE),
    ]

    async with LLMClient(_make_settings()) as client:
        result = await client.analyze("# Test")

    assert result.title == "Python 비동기 가이드"
    assert route.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_validation_fails_after_all_retries() -> None:
    """Always returns truncated JSON → raises ValueError."""
    respx.post("https://test-api.example.com/v1/chat/completions").mock(
        return_value=_chat_response('{"title": "incomplete')
    )

    async with LLMClient(_make_settings()) as client:
        with pytest.raises(ValueError, match="invalid output after 3 attempts"):
            await client.analyze("# Test")


@pytest.mark.asyncio
@respx.mock
async def test_payload_includes_max_tokens() -> None:
    """Verify max_tokens is sent in the request payload."""
    route = respx.post("https://test-api.example.com/v1/chat/completions").mock(
        return_value=_chat_response(MOCK_RESPONSE)
    )

    async with LLMClient(_make_settings()) as client:
        await client.analyze("# Test")

    sent_payload = json.loads(route.calls[0].request.content)
    assert sent_payload["max_tokens"] == 1024
