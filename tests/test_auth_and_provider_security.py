from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.crypto import generate_key
from app.main import create_app
from app.repository import PostgresRepository, RepositoryError


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


def test_create_provider_api_merges_runtime_config_fields() -> None:
    app = _build_app()
    captured: dict = {}

    app.state.repository.create_provider = lambda data: captured.update(data) or 11
    app.state.repository.get_provider = lambda provider_id: {
        "id": provider_id,
        "name": "qb-glm51",
        "display_name": "QB GLM5.1",
        "provider_type": "api",
        "base_url": "https://example.com/v1",
        "api_key": None,
        "masked_api_key": None,
        "has_api_key": True,
        "config": {
            "timeout_sec": 420,
            "connect_retries": 2,
            "custom_header": "x-demo",
        },
        "runtime_config": {"timeout_sec": 420, "connect_retries": 2},
        "runtime_config_extras": {"custom_header": "x-demo"},
        "description": "demo",
        "is_enabled": True,
        "created_at": None,
        "updated_at": None,
    }
    client = TestClient(app)

    response = client.post(
        "/api/providers",
        headers={"Authorization": "Bearer admin-token"},
        json={
            "name": "qb-glm51",
            "display_name": "QB GLM5.1",
            "provider_type": "api",
            "base_url": "https://example.com/v1",
            "runtime_config": {"timeout_sec": 420, "connect_retries": 2},
            "runtime_config_extras": {"custom_header": "x-demo"},
            "is_enabled": True,
        },
    )

    assert response.status_code == 200
    assert captured["config"] == {
        "timeout_sec": 420,
        "connect_retries": 2,
        "custom_header": "x-demo",
    }
    assert "runtime_config" not in captured
    assert "runtime_config_extras" not in captured


def test_update_provider_api_uses_existing_provider_type_for_runtime_config() -> None:
    app = _build_app()
    captured: dict = {}

    app.state.repository.get_provider = lambda provider_id: {
        "id": provider_id,
        "name": "kimi_cli",
        "display_name": "Kimi CLI",
        "provider_type": "cli",
        "base_url": None,
        "api_key": None,
        "masked_api_key": None,
        "has_api_key": False,
        "config": {"command": "kimi", "timeout_sec": 120},
        "runtime_config": {"command": "kimi", "timeout_sec": 120},
        "runtime_config_extras": {},
        "description": None,
        "is_enabled": True,
        "created_at": None,
        "updated_at": None,
    }
    app.state.repository.update_provider = (
        lambda provider_id, data: captured.update({"provider_id": provider_id, **data})
        or True
    )
    client = TestClient(app)

    response = client.put(
        "/api/providers/7",
        headers={"Authorization": "Bearer admin-token"},
        json={
            "runtime_config": {"timeout_sec": 240, "command": "kimi"},
            "runtime_config_extras": {"custom_env": "demo"},
        },
    )

    assert response.status_code == 200
    assert captured["provider_id"] == 7
    assert captured["config"] == {
        "timeout_sec": 240,
        "command": "kimi",
        "custom_env": "demo",
    }


def test_create_provider_api_rejects_invalid_runtime_config() -> None:
    app = _build_app()
    client = TestClient(app)

    response = client.post(
        "/api/providers",
        headers={"Authorization": "Bearer admin-token"},
        json={
            "name": "broken",
            "display_name": "Broken",
            "provider_type": "api",
            "base_url": "https://example.com/v1",
            "runtime_config": {"chat_endpoint": "chat/completions"},
        },
    )

    assert response.status_code == 400
    assert "chat_endpoint" in response.json()["detail"]


def test_admin_compat_routes_include_deprecation_headers() -> None:
    app = _build_app()
    app.state.repository.list_route_rules = lambda: []
    client = TestClient(app)

    response = client.get(
        "/admin/routes",
        headers={"Authorization": "Bearer admin-token"},
    )

    assert response.status_code == 200
    assert response.headers["X-Model-Gateway-Compat"] == "deprecated"
    assert (
        response.headers["X-Model-Gateway-Compat-Preferred"]
        == "/api/providers,/api/routes"
    )


def test_admin_compat_providers_include_deprecation_headers() -> None:
    app = _build_app()
    app.state.repository.list_provider_configs = lambda: []
    client = TestClient(app)

    response = client.get(
        "/admin/providers",
        headers={"Authorization": "Bearer admin-token"},
    )

    assert response.status_code == 200
    assert response.headers["X-Model-Gateway-Compat"] == "deprecated"
    assert (
        response.headers["X-Model-Gateway-Compat-Preferred"]
        == "/api/providers,/api/routes"
    )


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


def test_admin_routes_reject_provider_binding_change_via_compat_api() -> None:
    app = _build_app()
    app.state.repository.upsert_route_rules = (  # type: ignore[method-assign]
        lambda rules: (_ for _ in ()).throw(
            RepositoryError(
                "compat route rule cannot change model provider binding; model demo-model is bound to current-provider, not requested-provider"
            )
        )
    )
    client = TestClient(app)

    response = client.post(
        "/admin/routes",
        headers={"Authorization": "Bearer admin-token"},
        json={
            "rules": [
                {
                    "model_name": "demo-model",
                    "primary_provider": "requested-provider",
                }
            ]
        },
    )

    assert response.status_code == 400
    assert "cannot change model provider binding" in response.json()["detail"]


def test_admin_providers_reject_creating_provider_via_compat_api() -> None:
    app = _build_app()
    app.state.repository.upsert_provider_configs = (  # type: ignore[method-assign]
        lambda providers: (_ for _ in ()).throw(
            RepositoryError(
                "compat provider config can only update existing providers; create provider via /api/providers first: new-provider"
            )
        )
    )
    client = TestClient(app)

    response = client.post(
        "/admin/providers",
        headers={"Authorization": "Bearer admin-token"},
        json={
            "providers": [
                {
                    "provider_name": "new-provider",
                    "config": {"base_url": "https://example.com/v1"},
                    "is_enabled": True,
                }
            ]
        },
    )

    assert response.status_code == 400
    assert "create provider via /api/providers first" in response.json()["detail"]


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
                "owned_by": "model-gateway",
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


def test_upsert_provider_configs_treats_existing_base_url_provider_as_api() -> None:
    repository = PostgresRepository(Settings())
    updated: dict = {}

    repository.get_provider_by_name = lambda *args, **kwargs: {  # type: ignore[method-assign]
        "id": 7,
        "provider_type": "api",
    }
    repository.update_provider = (  # type: ignore[method-assign]
        lambda provider_id, data: updated.update({"provider_id": provider_id, **data}) or True
    )

    result = repository.upsert_provider_configs(
        [
            {
                "provider_name": "generic-openai",
                "config": {
                    "base_url": "https://example.com/v1",
                    "api_key": "sk-test",
                },
                "is_enabled": True,
            }
        ]
    )

    assert result == 1
    assert updated["provider_id"] == 7
    assert updated["provider_type"] == "api"
    assert updated["base_url"] == "https://example.com/v1"


def test_upsert_provider_configs_preserves_existing_provider_type() -> None:
    repository = PostgresRepository(Settings())
    updated: dict = {}

    repository.get_provider_by_name = lambda *args, **kwargs: {  # type: ignore[method-assign]
        "id": 42,
        "provider_type": "api",
    }
    repository.update_provider = (  # type: ignore[method-assign]
        lambda provider_id, data: updated.update({"provider_id": provider_id, **data}) or True
    )

    result = repository.upsert_provider_configs(
        [
            {
                "provider_name": "existing-provider",
                "config": {"command": "custom-cli"},
                "is_enabled": True,
            }
        ]
    )

    assert result == 1
    assert updated["provider_id"] == 42
    assert updated["provider_type"] == "api"


def test_upsert_provider_configs_rejects_unknown_provider_creation() -> None:
    repository = PostgresRepository(Settings())
    repository.get_provider_by_name = lambda *args, **kwargs: None  # type: ignore[method-assign]

    with pytest.raises(RepositoryError, match="create provider via /api/providers first"):
        repository.upsert_provider_configs(
            [
                {
                    "provider_name": "new-provider",
                    "config": {"base_url": "https://example.com/v1"},
                    "is_enabled": True,
                }
            ]
        )


def test_upsert_route_rules_requires_existing_model_and_matching_provider() -> None:
    repository = PostgresRepository(Settings())
    repository.get_model_by_key = lambda model_key: {  # type: ignore[method-assign]
        "model_key": model_key,
        "provider": {"name": "current-provider"},
    }
    called: dict = {}
    repository.upsert_model_routes = lambda records: called.update(  # type: ignore[method-assign]
        {"records": records}
    ) or len(records)

    with pytest.raises(RepositoryError):
        repository.upsert_route_rules(
            [
                {
                    "model_name": "demo-model",
                    "primary_provider": "other-provider",
                    "is_enabled": True,
                }
            ]
        )

    result = repository.upsert_route_rules(
        [
            {
                "model_name": "demo-model",
                "primary_provider": "current-provider",
                "is_enabled": False,
                "description": "compat update",
            }
        ]
    )

    assert result == 1
    assert called["records"] == [
        {
            "model_key": "demo-model",
            "is_enabled": False,
            "priority": 0,
            "description": "compat update",
        }
    ]
