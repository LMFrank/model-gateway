from __future__ import annotations

import asyncio
from unittest.mock import patch

import httpx

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

    def __call__(self, *args, **kwargs):  # noqa: ANN002,ANN003
        factory = self

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
