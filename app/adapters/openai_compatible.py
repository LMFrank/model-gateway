from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from typing import Any

import httpx

from app.adapters.base import AdapterError, StreamHandle
from app.config import Settings

ALLOWED_CHAT_FIELDS = {
    "messages",
    "model",
    "temperature",
    "top_p",
    "max_tokens",
    "stream",
    "stop",
    "presence_penalty",
    "frequency_penalty",
    "n",
    "tools",
    "tool_choice",
    "response_format",
    "seed",
    "logit_bias",
    "user",
}


class OpenAICompatibleAdapter:
    DEFAULT_CONNECT_RETRIES = 2
    DEFAULT_RETRY_BACKOFF_SEC = 0.5

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def chat(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> dict[str, Any]:
        url, headers, body, timeout = self._build_request(
            payload, provider_config, stream=False
        )

        response = await self._post_with_connect_retry(
            url,
            headers=headers,
            body=body,
            timeout=timeout,
            provider_config=provider_config,
        )

        if response.status_code >= 400:
            raise AdapterError(
                f"openai-compatible upstream error {response.status_code}: {response.text}"
            )

        try:
            return response.json()
        except ValueError as exc:
            raise AdapterError("openai-compatible upstream returned invalid json") from exc

    async def prepare_stream(
        self, payload: dict[str, Any], provider_config: dict[str, Any]
    ) -> StreamHandle:
        url, headers, body, timeout = self._build_request(
            payload, provider_config, stream=True
        )

        client = httpx.AsyncClient(timeout=timeout)
        stream_ctx = client.stream("POST", url, headers=headers, json=body)
        response = await stream_ctx.__aenter__()

        if response.status_code >= 400:
            text = (await response.aread()).decode("utf-8", errors="ignore")
            await stream_ctx.__aexit__(None, None, None)
            await client.aclose()
            raise AdapterError(
                f"openai-compatible upstream error {response.status_code}: {text}"
            )

        closed = False

        async def close() -> None:
            nonlocal closed
            if closed:
                return
            closed = True
            await stream_ctx.__aexit__(None, None, None)
            await client.aclose()

        async def iterator() -> AsyncIterator[bytes]:
            try:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    yield f"{line}\n\n".encode("utf-8")
            finally:
                await close()

        return StreamHandle(iterator=iterator(), close=close)

    def _build_request(
        self,
        payload: dict[str, Any],
        provider_config: dict[str, Any],
        stream: bool,
    ) -> tuple[str, dict[str, str], dict[str, Any], float]:
        base_url = str(provider_config.get("base_url", "")).rstrip("/")
        if not base_url:
            raise AdapterError("provider config missing base_url")

        endpoint = str(provider_config.get("chat_endpoint", "/chat/completions"))
        url = f"{base_url}{endpoint}"

        api_key = str(provider_config.get("api_key", "")).strip()
        if not api_key:
            raise AdapterError("provider config missing api_key")

        body: dict[str, Any] = {}
        for key, value in payload.items():
            if key in ALLOWED_CHAT_FIELDS:
                body[key] = value

        body["stream"] = stream
        upstream_model = provider_config.get("upstream_model")
        if upstream_model:
            body["model"] = str(upstream_model)

        if not body.get("model"):
            raise AdapterError("chat payload missing model")

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

        timeout = float(
            provider_config.get(
                "timeout_sec", self.settings.openai_compatible_timeout_sec
            )
        )
        return url, headers, body, timeout

    async def _post_with_connect_retry(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: dict[str, Any],
        timeout: float,
        provider_config: dict[str, Any],
    ) -> httpx.Response:
        retries = int(
            provider_config.get("connect_retries", self.DEFAULT_CONNECT_RETRIES)
            or self.DEFAULT_CONNECT_RETRIES
        )
        backoff_sec = float(
            provider_config.get("retry_backoff_sec", self.DEFAULT_RETRY_BACKOFF_SEC)
            or self.DEFAULT_RETRY_BACKOFF_SEC
        )
        max_attempts = max(1, retries + 1)
        last_error: httpx.HTTPError | None = None

        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    return await client.post(url, headers=headers, json=body)
            except (httpx.ConnectError, httpx.ConnectTimeout) as exc:
                last_error = exc
                if attempt >= max_attempts:
                    break
                await asyncio.sleep(backoff_sec * attempt)

        raise AdapterError(
            "openai-compatible upstream connect failed "
            f"after {max_attempts} attempts: {last_error.__class__.__name__ if last_error else 'unknown'}"
        )
