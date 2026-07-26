from __future__ import annotations

import asyncio
from unittest.mock import patch

import httpx
import pytest

from app.adapters.base import AdapterError
from app.adapters.openai_compatible import OpenAICompatibleAdapter
from app.config import Settings


class _Response:
    def __init__(self, status_code: int = 200, payload: dict | None = None) -> None:
        self.status_code = status_code
        self._payload = payload or {"id": "ok", "choices": [{"message": {"content": "ok"}}]}
        self.text = "ok"

    def json(self) -> dict:
        return self._payload


class _ClientFactory:
    def __init__(self, side_effects: list[object]) -> None:
        self._side_effects = list(side_effects)
        self.calls = 0
        self.kwargs: list[dict] = []

    def __call__(self, *args, **kwargs):  # noqa: ANN002,ANN003
        factory = self
        factory.kwargs.append(kwargs)

        class _Client:
            async def __aenter__(self):  # noqa: ANN202
                return self

            async def __aexit__(self, exc_type, exc, tb):  # noqa: ANN001,ANN201
                return False

            async def post(self, *args, **kwargs):  # noqa: ANN002,ANN003,ANN202
                factory.calls += 1
                effect = factory._side_effects.pop(0)
                if isinstance(effect, Exception):
                    raise effect
                return effect

        return _Client()


class _StreamClientFactory:
    def __init__(self, enter_effects: list[object]) -> None:
        self._enter_effects = list(enter_effects)
        self.calls = 0
        self.closed = 0

    def __call__(self, *args, **kwargs):  # noqa: ANN002,ANN003
        factory = self

        class _StreamResponse:
            status_code = 200

            async def aiter_lines(self):
                yield "data: ok"

        class _StreamContext:
            async def __aenter__(self):
                factory.calls += 1
                effect = factory._enter_effects.pop(0)
                if isinstance(effect, Exception):
                    raise effect
                return effect

            async def __aexit__(self, exc_type, exc, tb):  # noqa: ANN001,ANN201
                return False

        class _Client:
            def stream(self, *args, **kwargs):  # noqa: ANN002,ANN003
                return _StreamContext()

            async def aclose(self):
                factory.closed += 1

        return _Client()

    @staticmethod
    def response():
        class _StreamResponse:
            status_code = 200

            async def aiter_lines(self):
                yield "data: ok"

        return _StreamResponse()


def test_chat_retries_on_connect_error_then_succeeds() -> None:
    adapter = OpenAICompatibleAdapter(Settings())
    payload = {"model": "Kimi-K2.6", "messages": [{"role": "user", "content": "hi"}]}
    provider_config = {"base_url": "https://example.com/v1", "api_key": "k"}
    factory = _ClientFactory(
        [
            httpx.ConnectError("boom"),
            _Response(),
        ]
    )

    with patch("app.adapters.openai_compatible.httpx.AsyncClient", side_effect=factory):
        result = asyncio.run(adapter.chat(payload, provider_config))

    assert factory.calls == 2
    assert factory.kwargs == [
        {"timeout": Settings().openai_compatible_timeout_sec, "trust_env": False},
        {"timeout": Settings().openai_compatible_timeout_sec, "trust_env": False},
    ]
    assert result["choices"][0]["message"]["content"] == "ok"


def test_chat_raises_adapter_error_after_exhausting_connect_retries() -> None:
    adapter = OpenAICompatibleAdapter(Settings())
    payload = {"model": "Kimi-K2.6", "messages": [{"role": "user", "content": "hi"}]}
    provider_config = {"base_url": "https://example.com/v1", "api_key": "k", "connect_retries": 1}
    factory = _ClientFactory(
        [
            httpx.ConnectError("boom-1"),
            httpx.ConnectError("boom-2"),
        ]
    )

    with patch("app.adapters.openai_compatible.httpx.AsyncClient", side_effect=factory):
        try:
            asyncio.run(adapter.chat(payload, provider_config))
        except AdapterError as exc:
            message = str(exc)
        else:
            raise AssertionError("AdapterError was not raised")

    assert factory.calls == 2
    assert "connect failed after 2 attempts" in message


def test_chat_allows_zero_connect_retries() -> None:
    adapter = OpenAICompatibleAdapter(Settings())
    payload = {"model": "Kimi-K2.6", "messages": [{"role": "user", "content": "hi"}]}
    provider_config = {
        "base_url": "https://example.com/v1",
        "api_key": "k",
        "connect_retries": 0,
        "retry_backoff_sec": 0,
    }
    factory = _ClientFactory([httpx.ConnectError("boom")])

    with (
        patch("app.adapters.openai_compatible.httpx.AsyncClient", side_effect=factory),
        pytest.raises(AdapterError, match="after 1 attempts"),
    ):
        asyncio.run(adapter.chat(payload, provider_config))

    assert factory.calls == 1


def test_prepare_stream_retries_connection_before_response_starts() -> None:
    adapter = OpenAICompatibleAdapter(Settings())
    factory = _StreamClientFactory(
        [httpx.ConnectError("boom"), _StreamClientFactory.response()]
    )

    with patch("app.adapters.openai_compatible.httpx.AsyncClient", side_effect=factory):
        handle = asyncio.run(
            adapter.prepare_stream(
                {"model": "demo", "messages": [{"role": "user", "content": "hi"}]},
                {"base_url": "https://example.com/v1", "api_key": "k", "connect_retries": 1},
            )
        )

    assert factory.calls == 2
    asyncio.run(handle.close())


def test_prepare_stream_closes_client_on_non_connection_error() -> None:
    adapter = OpenAICompatibleAdapter(Settings())
    factory = _StreamClientFactory([httpx.ReadTimeout("slow headers")])

    with (
        patch("app.adapters.openai_compatible.httpx.AsyncClient", side_effect=factory),
        pytest.raises(httpx.ReadTimeout),
    ):
        asyncio.run(
            adapter.prepare_stream(
                {"model": "demo", "messages": [{"role": "user", "content": "hi"}]},
                {"base_url": "https://example.com/v1", "api_key": "k"},
            )
        )

    assert factory.closed == 1


def test_build_request_forces_provider_temperature() -> None:
    adapter = OpenAICompatibleAdapter(Settings())

    url, headers, body, timeout = adapter._build_request(
        {
            "model": "k3",
            "messages": [{"role": "user", "content": "hi"}],
            "temperature": 0,
        },
        {
            "base_url": "https://example.com/v1",
            "api_key": "k",
            "force_temperature": 1,
        },
        stream=False,
    )

    assert url == "https://example.com/v1/chat/completions"
    assert headers["Authorization"] == "Bearer k"
    assert body["model"] == "k3"
    assert body["temperature"] == 1.0
    assert timeout == Settings().openai_compatible_timeout_sec
