from __future__ import annotations

from fastapi.testclient import TestClient

from app.config import Settings
from app.crypto import generate_key
from app.main import create_app
from app.repository import PostgresRepository


def _build_app():
    app = create_app()
    app.state.settings.gateway_admin_token = "admin-token"
    app.state.settings.gateway_client_token = "client-token"
    return app


def test_admin_endpoint_requires_bearer_token() -> None:
    app = _build_app()
    app.state.repository.list_providers = lambda: []
    client = TestClient(app)

    response = client.get("/api/providers")

    assert response.status_code == 401
    assert response.json()["detail"] == "missing bearer token"


def test_admin_endpoint_accepts_configured_token() -> None:
    app = _build_app()
    app.state.repository.list_providers = lambda: []
    client = TestClient(app)

    response = client.get(
        "/api/providers",
        headers={"Authorization": "Bearer admin-token"},
    )

    assert response.status_code == 200
    assert response.json() == {"items": []}


def test_admin_routes_reject_fallback_provider() -> None:
    app = _build_app()
    client = TestClient(app)

    response = client.post(
        "/admin/routes",
        headers={"Authorization": "Bearer admin-token"},
        json={
            "rules": [
                {
                    "model_name": "demo-model",
                    "primary_provider": "demo-provider",
                    "fallback_provider": "unused-fallback",
                }
            ]
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "fallback_provider is not supported"


def test_client_endpoint_rejects_wrong_scope_token() -> None:
    app = _build_app()
    client = TestClient(app)

    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer admin-token"},
        json={"model": "demo-model", "messages": [{"role": "user", "content": "ping"}]},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "invalid token"


def test_client_endpoint_accepts_client_token() -> None:
    app = _build_app()

    class DummyAdapter:
        async def chat(self, payload, provider_config):
            assert provider_config["api_key"] == "sk-provider-1234"
            return {
                "id": "chatcmpl-test",
                "object": "chat.completion",
                "model": payload["model"],
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "stop",
                        "message": {"role": "assistant", "content": "ok"},
                    }
                ],
            }

    app.state.repository.get_model_by_key = lambda model_key: {
        "upstream_model": "upstream-demo-model"
    }
    app.state.repository.get_route_rule = lambda model_key: {
        "model_name": model_key,
        "primary_provider": "test_api",
        "fallback_provider": None,
        "is_enabled": True,
    }
    app.state.repository.get_provider_config = lambda provider_name: {
        "config": {"api_key": "sk-provider-1234"},
        "is_enabled": True,
    }
    app.state.repository.insert_call_log = lambda payload: 1
    app.state.adapter_registry["test_api"] = DummyAdapter()

    client = TestClient(app)
    response = client.post(
        "/v1/chat/completions",
        headers={"Authorization": "Bearer client-token"},
        json={"model": "demo-model", "messages": [{"role": "user", "content": "ping"}]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["model"] == "upstream-demo-model"
    assert body["choices"][0]["message"]["content"] == "ok"


def test_client_models_endpoint_requires_client_token() -> None:
    app = _build_app()
    app.state.repository.list_model_routes = lambda: []
    client = TestClient(app)

    response = client.get("/v1/models")

    assert response.status_code == 401


def test_client_models_endpoint_lists_only_active_models() -> None:
    app = _build_app()
    app.state.repository.list_model_routes = lambda: [
        {
            "model_key": "qwen3-max",
            "is_enabled": True,
            "model": {"display_name": "Qwen3 Max", "is_active": True},
            "provider": {"name": "bailian_coding_api"},
        },
        {
            "model_key": "disabled-model",
            "is_enabled": False,
            "model": {"display_name": "Disabled", "is_active": True},
            "provider": {"name": "bailian_api"},
        },
    ]
    client = TestClient(app)

    response = client.get(
        "/v1/models",
        headers={"Authorization": "Bearer client-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "object": "list",
        "data": [
            {
                "id": "qwen3-max",
                "object": "model",
                "owned_by": "bailian_coding_api",
                "display_name": "Qwen3 Max",
            }
        ],
    }


def test_provider_projection_masks_and_decrypts_secret() -> None:
    settings = Settings(
        api_key_encryption_key=generate_key(),
        encrypt_api_keys=True,
    )
    repository = PostgresRepository(settings)
    encrypted = repository._encrypt_api_key("sk-provider-1234")

    row = {
        "id": 1,
        "name": "demo",
        "display_name": "Demo",
        "provider_type": "api",
        "base_url": "https://example.com/v1",
        "api_key": encrypted,
        "config_json": {"timeout_sec": 30},
        "description": "demo provider",
        "is_enabled": True,
        "created_at": None,
        "updated_at": None,
    }

    public_item = repository._provider_row_to_dict(row)
    assert public_item["api_key"] is None
    assert public_item["has_api_key"] is True
    assert public_item["masked_api_key"] == "sk-***1234"

    private_item = repository._provider_row_to_dict(row, include_secret=True)
    assert private_item["api_key"] == "sk-provider-1234"


def test_repository_healthcheck_requires_current_schema_tables() -> None:
    settings = Settings()
    repository = PostgresRepository(settings)

    class FakeCursor:
        def __init__(self) -> None:
            self._rows = [
                {"tablename": "providers"},
                {"tablename": "models"},
            ]

        def execute(self, sql, params) -> None:
            return None

        def fetchall(self):
            return self._rows

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class FakeConn:
        def cursor(self):
            return FakeCursor()

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    repository._get_conn = lambda: FakeConn()  # type: ignore[method-assign]

    assert repository.healthcheck() is False
