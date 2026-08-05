from __future__ import annotations

from fastapi.testclient import TestClient
from prometheus_client import generate_latest

import app.main as main
from app.adapters.base import AdapterError, StreamHandle


def test_gateway_call_metrics_expose_route_provider_model_outcome_and_tokens() -> None:
    assert hasattr(main, "_observe_gateway_call")

    main._observe_gateway_call(
        route="observability-test-route",
        provider="observability-test-provider",
        model="observability-test-model",
        outcome="success",
        duration_seconds=1.25,
        prompt_tokens=11,
        completion_tokens=7,
    )

    payload = generate_latest().decode()
    labels = (
        'model="observability-test-model",outcome="success",'
        'provider="observability-test-provider",route="observability-test-route"'
    )
    token_labels = (
        'direction="prompt",model="observability-test-model",'
        'provider="observability-test-provider",route="observability-test-route"'
    )
    assert f"model_gateway_calls_total{{{labels}}} 1.0" in payload
    assert f"model_gateway_call_duration_seconds_count{{{labels}}} 1.0" in payload
    assert f"model_gateway_tokens_total{{{token_labels}}} 11.0" in payload
    assert (
        'model_gateway_tokens_total{direction="completion",'
        'model="observability-test-model",'
        'provider="observability-test-provider",'
        'route="observability-test-route"} 7.0'
    ) in payload


def test_gateway_call_metrics_normalize_missing_dimensions_without_ids() -> None:
    assert hasattr(main, "_observe_gateway_call")

    main._observe_gateway_call(
        route="",
        provider=None,
        model=None,
        outcome="failed",
        duration_seconds=-1,
    )

    payload = generate_latest().decode()
    labels = 'model="unknown",outcome="failed",provider="none",route="unknown"'
    assert f"model_gateway_calls_total{{{labels}}} 1.0" in payload
    assert f"model_gateway_call_duration_seconds_sum{{{labels}}} 0.0" in payload
    assert "task_id=" not in payload
    assert "stock_code=" not in payload


def test_chat_completion_records_selected_route_provider_model_and_usage() -> None:
    app = main.create_app()
    app.state.settings.gateway_client_token = "client-token"

    class SuccessfulAdapter:
        async def chat(self, payload, provider_config):
            return {
                "id": "chatcmpl-observability",
                "object": "chat.completion",
                "model": payload["model"],
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "ok"},
                    }
                ],
                "usage": {
                    "prompt_tokens": 13,
                    "completion_tokens": 5,
                    "total_tokens": 18,
                },
            }

    app.state.repository.get_model_by_key = lambda model_key: {
        "upstream_model": "observability-upstream",
        "default_params": {},
        "provider": {"name": "observability-provider"},
    }
    app.state.repository.get_route_rule = lambda model_key: {
        "model_name": model_key,
        "primary_provider": "observability-provider",
        "fallback_provider": None,
        "fallback_model_key": None,
        "is_enabled": True,
    }
    app.state.repository.get_provider_config = lambda provider_name: {
        "config": {"api_key": "test"},
        "is_enabled": True,
    }
    app.state.repository.insert_call_log = lambda payload: 1
    app.state.adapter_registry["observability-provider"] = SuccessfulAdapter()

    response = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer client-token"},
        json={
            "model": "observability-route",
            "messages": [{"role": "user", "content": "ping"}],
        },
    )

    assert response.status_code == 200
    payload = generate_latest().decode()
    labels = (
        'model="observability-upstream",outcome="success",'
        'provider="observability-provider",route="observability-route"'
    )
    assert f"model_gateway_calls_total{{{labels}}} 1.0" in payload
    assert (
        'model_gateway_tokens_total{direction="prompt",'
        'model="observability-upstream",provider="observability-provider",'
        'route="observability-route"} 13.0'
    ) in payload


def test_failed_chat_completion_records_failed_route_metric() -> None:
    app = main.create_app()
    app.state.settings.gateway_client_token = "client-token"

    class FailingAdapter:
        async def chat(self, payload, provider_config):
            raise AdapterError("upstream rejected request")

    app.state.repository.get_model_by_key = lambda model_key: {
        "upstream_model": "observability-failed-upstream",
        "default_params": {},
        "provider": {"name": "observability-failed-provider"},
    }
    app.state.repository.get_route_rule = lambda model_key: {
        "model_name": model_key,
        "primary_provider": "observability-failed-provider",
        "fallback_provider": None,
        "fallback_model_key": None,
        "is_enabled": True,
    }
    app.state.repository.get_provider_config = lambda provider_name: {
        "config": {"api_key": "test"},
        "is_enabled": True,
    }
    app.state.repository.insert_call_log = lambda payload: 1
    app.state.adapter_registry["observability-failed-provider"] = FailingAdapter()

    response = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer client-token"},
        json={
            "model": "observability-failed-route",
            "messages": [{"role": "user", "content": "ping"}],
        },
    )

    assert response.status_code == 502
    payload = generate_latest().decode()
    labels = (
        'model="observability-failed-upstream",outcome="failed",'
        'provider="observability-failed-provider",'
        'route="observability-failed-route"'
    )
    assert f"model_gateway_calls_total{{{labels}}} 1.0" in payload


def test_stream_completion_records_metric_after_stream_closes() -> None:
    app = main.create_app()
    app.state.settings.gateway_client_token = "client-token"

    class StreamingAdapter:
        async def prepare_stream(self, payload, provider_config):
            async def iterator():
                yield b'data: {"choices":[{"delta":{"content":"ok"}}]}\n\n'

            async def close() -> None:
                return None

            return StreamHandle(iterator=iterator(), close=close)

    app.state.repository.get_model_by_key = lambda model_key: {
        "upstream_model": "observability-stream-upstream",
        "default_params": {},
        "provider": {"name": "observability-stream-provider"},
    }
    app.state.repository.get_route_rule = lambda model_key: {
        "model_name": model_key,
        "primary_provider": "observability-stream-provider",
        "fallback_provider": None,
        "fallback_model_key": None,
        "is_enabled": True,
    }
    app.state.repository.get_provider_config = lambda provider_name: {
        "config": {"api_key": "test"},
        "is_enabled": True,
    }
    app.state.repository.insert_call_log = lambda payload: 1
    app.state.adapter_registry["observability-stream-provider"] = StreamingAdapter()

    response = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer client-token"},
        json={
            "model": "observability-stream-route",
            "messages": [{"role": "user", "content": "ping"}],
            "stream": True,
        },
    )

    assert response.status_code == 200
    assert b'"content":"ok"' in response.content
    payload = generate_latest().decode()
    labels = (
        'model="observability-stream-upstream",outcome="success",'
        'provider="observability-stream-provider",'
        'route="observability-stream-route"'
    )
    assert f"model_gateway_calls_total{{{labels}}} 1.0" in payload


def test_missing_route_records_route_not_found_metric_without_provider() -> None:
    app = main.create_app()
    app.state.settings.gateway_client_token = "client-token"
    app.state.repository.get_model_by_key = lambda model_key: None
    app.state.repository.get_route_rule = lambda model_key: None
    app.state.repository.insert_call_log = lambda payload: 1

    response = TestClient(app).post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer client-token"},
        json={
            "model": "observability-missing-route",
            "messages": [{"role": "user", "content": "ping"}],
        },
    )

    assert response.status_code == 400
    payload = generate_latest().decode()
    labels = (
        'model="unknown",outcome="route_not_found",'
        'provider="none",route="unmatched"'
    )
    assert f"model_gateway_calls_total{{{labels}}} 1.0" in payload
    assert 'route="observability-missing-route"' not in payload
