from __future__ import annotations

import pytest

from app.provider_runtime_config import (
    ProviderRuntimeConfigError,
    merge_runtime_config,
    split_runtime_config,
)


def test_split_runtime_config_for_api_provider_preserves_extras() -> None:
    runtime_config, runtime_config_extras = split_runtime_config(
        "api",
        {
            "timeout_sec": 420,
            "connect_retries": 2,
            "retry_backoff_sec": 0.5,
            "chat_endpoint": "/chat/completions",
            "upstream_model": "glm-5.1-fp8",
            "custom_header": "x-demo",
        },
    )

    assert runtime_config == {
        "timeout_sec": 420,
        "connect_retries": 2,
        "retry_backoff_sec": 0.5,
        "chat_endpoint": "/chat/completions",
        "upstream_model": "glm-5.1-fp8",
    }
    assert runtime_config_extras == {"custom_header": "x-demo"}


def test_merge_runtime_config_round_trips_api_config_without_dropping_unknown_keys() -> None:
    merged = merge_runtime_config(
        "api",
        config={"custom_header": "x-demo", "timeout_sec": 120},
        runtime_config={"timeout_sec": 420, "connect_retries": 3},
        runtime_config_extras={"custom_header": "x-updated"},
    )

    assert merged == {
        "custom_header": "x-updated",
        "timeout_sec": 420,
        "connect_retries": 3,
    }


def test_merge_runtime_config_for_cli_provider_keeps_supported_fields() -> None:
    merged = merge_runtime_config(
        "cli",
        runtime_config={
            "timeout_sec": 240,
            "command": "codex",
            "args": ["exec"],
            "use_stdin_prompt": True,
        },
        runtime_config_extras={"custom_env": "demo"},
    )

    assert merged == {
        "custom_env": "demo",
        "timeout_sec": 240,
        "command": "codex",
        "args": ["exec"],
        "use_stdin_prompt": True,
    }


def test_merge_runtime_config_rejects_invalid_timeout() -> None:
    with pytest.raises(ProviderRuntimeConfigError):
        merge_runtime_config("api", runtime_config={"timeout_sec": 0})


def test_merge_runtime_config_rejects_invalid_chat_endpoint() -> None:
    with pytest.raises(ProviderRuntimeConfigError):
        merge_runtime_config("api", runtime_config={"chat_endpoint": "chat/completions"})
