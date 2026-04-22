from app.adapters import OpenAICompatibleAdapter, QwenApiAdapter
from app.adapters.kimi_cli import KimiCliAdapter
from app.main import (
    _extract_task_fields,
    _extract_usage,
    _format_provider_error,
    _provider_runtime_config,
    _resolve_adapter,
    create_app,
)


def test_extract_usage() -> None:
    prompt, completion, total = _extract_usage(
        {"usage": {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}}
    )
    assert (prompt, completion, total) == (10, 20, 30)


def test_extract_task_fields_prefers_top_level() -> None:
    task_id, stock_code = _extract_task_fields(
        {
            "task_id": "task-1",
            "stock_code": "000001",
            "metadata": {"task_id": "meta-task", "stock_code": "600519"},
        }
    )
    assert task_id == "task-1"
    assert stock_code == "000001"


def test_extract_task_fields_fallback_to_metadata() -> None:
    task_id, stock_code = _extract_task_fields({"metadata": {"task_id": "meta-task", "stock_code": "600519"}})
    assert task_id == "meta-task"
    assert stock_code == "600519"


def test_create_app_registers_codex_cli_adapter() -> None:
    app = create_app()
    assert "codex_cli" in app.state.adapter_registry
    assert isinstance(app.state.adapter_registry["codex_cli"], KimiCliAdapter)


def test_create_app_registers_default_api_adapter() -> None:
    app = create_app()
    assert "__default_api__" in app.state.adapter_registry
    assert isinstance(
        app.state.adapter_registry["__default_api__"], OpenAICompatibleAdapter
    )


def test_resolve_adapter_uses_default_for_generic_api_provider() -> None:
    app = create_app()
    adapter = _resolve_adapter(
        app.state.adapter_registry,
        "custom_openapi",
        provider_type="api",
        provider_config={"base_url": "https://example.com/v1"},
    )
    assert isinstance(adapter, OpenAICompatibleAdapter)


def test_provider_runtime_config_flattens_secret_and_base_url() -> None:
    runtime = _provider_runtime_config(
        {
            "base_url": "https://example.com/v1",
            "api_key": "sk-test",
            "config": {"timeout_sec": 30, "chat_endpoint": "/chat/completions"},
        }
    )
    assert runtime == {
        "timeout_sec": 30,
        "chat_endpoint": "/chat/completions",
        "base_url": "https://example.com/v1",
        "api_key": "sk-test",
    }


def test_format_provider_error_prefers_message() -> None:
    assert _format_provider_error(RuntimeError("boom")) == "boom"


def test_format_provider_error_falls_back_to_exception_name() -> None:
    class SilentError(Exception):
        def __str__(self) -> str:
            return ""

    assert _format_provider_error(SilentError()) == "SilentError"


def test_qwen_api_adapter_alias_still_points_to_openai_compatible_adapter() -> None:
    assert QwenApiAdapter is OpenAICompatibleAdapter
