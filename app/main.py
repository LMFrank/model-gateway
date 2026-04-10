from __future__ import annotations

import logging
import time
import uuid
from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, Response, StreamingResponse
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest

from app.adapters import KimiCliAdapter, QwenApiAdapter
from app.adapters.base import AdapterError
from app.auth import require_admin_auth, require_client_auth
from app.config import get_settings
from app.repository import PostgresRepository
from app.router_engine import RouteNotFoundError, RouterEngine
from app.schemas import (
    ModelCreate,
    ModelUpdate,
    ModelsListResponse,
    ProviderCreate,
    ProviderUpdate,
    ProvidersListResponse,
    ProviderConfigsUpsertRequest,
    RouteRulesUpsertRequest,
    RouteRulesV2ListResponse,
    RouteRulesV2UpsertRequest,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model-gateway")

APP_VERSION = "0.1.6"
SERVICE_NAME = "model-gateway-api"
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total HTTP requests handled by the service.",
    ["service", "method", "path", "status"],
)
HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["service", "method", "path"],
)


def _extract_usage(
    response_payload: dict[str, Any],
) -> tuple[int | None, int | None, int | None]:
    usage = (
        response_payload.get("usage") if isinstance(response_payload, dict) else None
    )
    if not isinstance(usage, dict):
        return None, None, None

    prompt_tokens = usage.get("prompt_tokens")
    completion_tokens = usage.get("completion_tokens")
    total_tokens = usage.get("total_tokens")
    return (
        int(prompt_tokens) if prompt_tokens is not None else None,
        int(completion_tokens) if completion_tokens is not None else None,
        int(total_tokens) if total_tokens is not None else None,
    )


def _extract_task_fields(payload: dict[str, Any]) -> tuple[str | None, str | None]:
    task_id = payload.get("task_id")
    stock_code = payload.get("stock_code")

    metadata = payload.get("metadata")
    if isinstance(metadata, dict):
        task_id = task_id or metadata.get("task_id")
        stock_code = stock_code or metadata.get("stock_code")

    return (
        str(task_id) if task_id is not None else None,
        str(stock_code) if stock_code is not None else None,
    )


def create_app() -> FastAPI:
    settings = get_settings()

    app = FastAPI(title="Model Gateway", version=APP_VERSION)

    repository = PostgresRepository(settings)
    router_engine = RouterEngine()
    adapter_registry = {
        "kimi_cli": KimiCliAdapter(settings),
        "codex_cli": KimiCliAdapter(settings),
        "openai_api": QwenApiAdapter(settings),
        "bailian_coding_api": QwenApiAdapter(settings),
        "bailian_api": QwenApiAdapter(settings),
        "deepseek_api": QwenApiAdapter(settings),
    }

    app.state.settings = settings
    app.state.repository = repository
    app.state.adapter_registry = adapter_registry
    app.state.router_engine = router_engine

    async def safe_insert_call_log(log_payload: dict[str, Any]) -> None:
        try:
            await run_in_threadpool(repository.insert_call_log, log_payload)
        except Exception:  # noqa: BLE001
            logger.exception(
                "call_log_insert_failed request_id=%s model=%s status=%s",
                log_payload.get("request_id"),
                log_payload.get("model_name"),
                log_payload.get("status"),
            )

    @app.middleware("http")
    async def request_id_middleware(request: Request, call_next):
        request_id = (
            request.headers.get("X-Request-Id") or f"req-{uuid.uuid4().hex[:20]}"
        )
        request.state.request_id = request_id

        start_time = time.perf_counter()
        path = request.url.path
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            HTTP_REQUEST_DURATION_SECONDS.labels(
                service=SERVICE_NAME,
                method=request.method,
                path=path,
            ).observe(time.perf_counter() - start_time)
            HTTP_REQUESTS_TOTAL.labels(
                service=SERVICE_NAME,
                method=request.method,
                path=path,
                status=str(status_code),
            ).inc()
            raise
        else:
            duration = time.perf_counter() - start_time
            HTTP_REQUEST_DURATION_SECONDS.labels(
                service=SERVICE_NAME,
                method=request.method,
                path=path,
            ).observe(duration)
            HTTP_REQUESTS_TOTAL.labels(
                service=SERVICE_NAME,
                method=request.method,
                path=path,
                status=str(status_code),
            ).inc()

        response.headers["X-Request-Id"] = request_id
        return response

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        db_ok = await run_in_threadpool(repository.healthcheck)
        if not db_ok:
            raise HTTPException(status_code=503, detail="database unavailable")
        return {"status": "ok"}

    @app.get("/metrics")
    async def metrics() -> Response:
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    @app.get("/v1/models", dependencies=[Depends(require_client_auth)])
    async def list_client_models() -> dict[str, Any]:
        items = await run_in_threadpool(repository.list_route_rules_v2)
        active_items = [
            item
            for item in items
            if item.get("is_enabled")
            and item.get("model", {}).get("is_active")
            and item.get("provider")
        ]
        return {
            "object": "list",
            "data": [
                {
                    "id": item["model_key"],
                    "object": "model",
                    "owned_by": item["provider"]["name"],
                    "display_name": item["model"]["display_name"],
                }
                for item in active_items
            ],
        }

    @app.get("/admin/routes", dependencies=[Depends(require_admin_auth)])
    async def list_routes() -> dict[str, Any]:
        items = await run_in_threadpool(repository.list_route_rules)
        return {"items": items}

    @app.post("/admin/routes", dependencies=[Depends(require_admin_auth)])
    async def upsert_routes(body: RouteRulesUpsertRequest) -> dict[str, Any]:
        if not body.rules:
            raise HTTPException(status_code=400, detail="rules cannot be empty")
        if any(item.fallback_provider for item in body.rules):
            raise HTTPException(
                status_code=400,
                detail="fallback_provider is deprecated and no longer supported",
            )
        await run_in_threadpool(
            repository.upsert_route_rules, [item.model_dump() for item in body.rules]
        )
        items = await run_in_threadpool(repository.list_route_rules)
        return {"items": items}

    # ==========================================================================
    # New Admin APIs (v2 Schema)
    # ==========================================================================

    # Provider CRUD
    @app.get("/api/providers", dependencies=[Depends(require_admin_auth)])
    async def list_providers_v2() -> ProvidersListResponse:
        items = await run_in_threadpool(repository.list_providers)
        return ProvidersListResponse(items=items)

    @app.get("/api/providers/{provider_id}", dependencies=[Depends(require_admin_auth)])
    async def get_provider_v2(provider_id: int) -> dict[str, Any]:
        item = await run_in_threadpool(repository.get_provider, provider_id)
        if not item:
            raise HTTPException(status_code=404, detail="provider not found")
        return item

    @app.post("/api/providers", dependencies=[Depends(require_admin_auth)])
    async def create_provider_v2(body: ProviderCreate) -> dict[str, Any]:
        provider_id = await run_in_threadpool(
            repository.create_provider, body.model_dump()
        )
        item = await run_in_threadpool(repository.get_provider, provider_id)
        return {"id": provider_id, "item": item}

    @app.put("/api/providers/{provider_id}", dependencies=[Depends(require_admin_auth)])
    async def update_provider_v2(
        provider_id: int, body: ProviderUpdate
    ) -> dict[str, Any]:
        success = await run_in_threadpool(
            repository.update_provider, provider_id, body.model_dump(exclude_unset=True)
        )
        if not success:
            raise HTTPException(status_code=404, detail="provider not found")
        item = await run_in_threadpool(repository.get_provider, provider_id)
        return {"item": item}

    @app.delete(
        "/api/providers/{provider_id}", dependencies=[Depends(require_admin_auth)]
    )
    async def delete_provider_v2(provider_id: int) -> dict[str, str]:
        success = await run_in_threadpool(repository.delete_provider, provider_id)
        if not success:
            raise HTTPException(status_code=404, detail="provider not found")
        return {"message": "provider deleted"}

    # Model CRUD
    @app.get("/api/models", dependencies=[Depends(require_admin_auth)])
    async def list_models_v2(
        provider_id: int | None = Query(default=None),
    ) -> ModelsListResponse:
        items = await run_in_threadpool(repository.list_models, provider_id)
        return ModelsListResponse(items=items)

    @app.get("/api/models/{model_id}", dependencies=[Depends(require_admin_auth)])
    async def get_model_v2(model_id: int) -> dict[str, Any]:
        item = await run_in_threadpool(repository.get_model, model_id)
        if not item:
            raise HTTPException(status_code=404, detail="model not found")
        return item

    @app.post("/api/models", dependencies=[Depends(require_admin_auth)])
    async def create_model_v2(body: ModelCreate) -> dict[str, Any]:
        # Validate provider exists
        provider = await run_in_threadpool(repository.get_provider, body.provider_id)
        if not provider:
            raise HTTPException(status_code=400, detail="provider not found")

        model_id = await run_in_threadpool(repository.create_model, body.model_dump())
        item = await run_in_threadpool(repository.get_model, model_id)
        return {"id": model_id, "item": item}

    @app.put("/api/models/{model_id}", dependencies=[Depends(require_admin_auth)])
    async def update_model_v2(model_id: int, body: ModelUpdate) -> dict[str, Any]:
        # Validate provider if provided
        if body.provider_id:
            provider = await run_in_threadpool(
                repository.get_provider, body.provider_id
            )
            if not provider:
                raise HTTPException(status_code=400, detail="provider not found")

        success = await run_in_threadpool(
            repository.update_model, model_id, body.model_dump(exclude_unset=True)
        )
        if not success:
            raise HTTPException(status_code=404, detail="model not found")
        item = await run_in_threadpool(repository.get_model, model_id)
        return {"item": item}

    @app.delete("/api/models/{model_id}", dependencies=[Depends(require_admin_auth)])
    async def delete_model_v2(model_id: int) -> dict[str, str]:
        success = await run_in_threadpool(repository.delete_model, model_id)
        if not success:
            raise HTTPException(status_code=404, detail="model not found")
        return {"message": "model deleted"}

    # Route Rules v2
    @app.get("/api/routes", dependencies=[Depends(require_admin_auth)])
    async def list_routes_v2() -> RouteRulesV2ListResponse:
        items = await run_in_threadpool(repository.list_route_rules_v2)
        return RouteRulesV2ListResponse(items=items)

    @app.post("/api/routes", dependencies=[Depends(require_admin_auth)])
    async def upsert_routes_v2(
        body: RouteRulesV2UpsertRequest,
    ) -> RouteRulesV2ListResponse:
        if not body.rules:
            raise HTTPException(status_code=400, detail="rules cannot be empty")
        await run_in_threadpool(
            repository.upsert_route_rules_v2, [item.model_dump() for item in body.rules]
        )
        items = await run_in_threadpool(repository.list_route_rules_v2)
        return RouteRulesV2ListResponse(items=items)

    @app.delete("/api/routes/{model_key}", dependencies=[Depends(require_admin_auth)])
    async def delete_route_v2(model_key: str) -> dict[str, str]:
        success = await run_in_threadpool(repository.delete_route_rule_v2, model_key)
        if not success:
            raise HTTPException(status_code=404, detail="route not found")
        return {"message": "route deleted"}

    @app.get("/admin/providers", dependencies=[Depends(require_admin_auth)])
    async def list_providers() -> dict[str, Any]:
        items = await run_in_threadpool(repository.list_provider_configs)
        return {"items": items}

    @app.post("/admin/providers", dependencies=[Depends(require_admin_auth)])
    async def upsert_providers(body: ProviderConfigsUpsertRequest) -> dict[str, Any]:
        if not body.providers:
            raise HTTPException(status_code=400, detail="providers cannot be empty")
        await run_in_threadpool(
            repository.upsert_provider_configs,
            [item.model_dump() for item in body.providers],
        )
        items = await run_in_threadpool(repository.list_provider_configs)
        return {"items": items}

    @app.get("/admin/calls", dependencies=[Depends(require_admin_auth)])
    async def list_calls(
        task_id: str | None = None,
        stock_code: str | None = None,
        model: str | None = None,
        status: str | None = None,
        limit: int = Query(100, ge=1, le=500),
        offset: int = Query(0, ge=0),
    ) -> dict[str, Any]:
        result = await run_in_threadpool(
            repository.list_calls,
            {
                "task_id": task_id,
                "stock_code": stock_code,
                "model": model,
                "status": status,
                "limit": limit,
                "offset": offset,
            },
        )
        return result

    @app.get("/admin/usage/summary", dependencies=[Depends(require_admin_auth)])
    async def usage_summary(
        date_from: date | None = Query(default=None),
        date_to: date | None = Query(default=None),
    ) -> dict[str, Any]:
        return await run_in_threadpool(repository.get_usage_summary, date_from, date_to)

    @app.get("/api/health/checks", dependencies=[Depends(require_admin_auth)])
    async def list_health_checks(
        check_type: str | None = Query(None, description="provider or model"),
        target_id: int | None = Query(None),
        status: str | None = Query(None),
        limit: int = Query(50, ge=1, le=200),
    ) -> dict[str, Any]:
        items = await run_in_threadpool(
            repository.list_health_checks,
            {
                "check_type": check_type,
                "target_id": target_id,
                "status": status,
                "limit": limit,
            },
        )
        return {"items": items}

    @app.get("/api/health/summary", dependencies=[Depends(require_admin_auth)])
    async def health_summary() -> dict[str, Any]:
        return await run_in_threadpool(repository.get_health_summary)

    @app.post(
        "/api/health/check/provider/{provider_id}",
        dependencies=[Depends(require_admin_auth)],
    )
    async def check_provider_health(provider_id: int) -> dict[str, Any]:
        provider = await run_in_threadpool(repository.get_provider, provider_id)
        if not provider:
            raise HTTPException(status_code=404, detail="provider not found")

        import asyncio

        started_at = time.perf_counter()
        status = "unknown"
        check_result: dict[str, Any] = {}
        error_message = None

        if provider["provider_type"] == "api":
            base_url = provider.get("base_url")
            if base_url:
                try:
                    async with asyncio.timeout(10):
                        resp = await httpx_async_client().get(
                            f"{base_url.rstrip('/')}/models", timeout=10.0
                        )
                        if resp.status_code == 200:
                            status = "healthy"
                            check_result["endpoint_reachable"] = True
                            check_result["http_status"] = resp.status_code
                        else:
                            status = "unhealthy"
                            check_result["endpoint_reachable"] = False
                            check_result["http_status"] = resp.status_code
                            error_message = f"HTTP {resp.status_code}"
                except asyncio.TimeoutError:
                    status = "unhealthy"
                    check_result["endpoint_reachable"] = False
                    error_message = "timeout after 10s"
                except Exception as e:
                    status = "unhealthy"
                    check_result["endpoint_reachable"] = False
                    error_message = str(e)[:200]
            else:
                status = "unknown"
                error_message = "no base_url configured"
        else:
            adapter = adapter_registry.get(provider["name"])
            if not adapter:
                status = "unknown"
                error_message = f"no adapter for provider {provider['name']}"
            else:
                provider_models = await run_in_threadpool(
                    repository.list_models, provider["id"]
                )
                active_models = [
                    item for item in provider_models if bool(item.get("is_active"))
                ]
                probe_model = active_models[0] if active_models else None
                if not probe_model:
                    status = "unknown"
                    error_message = "no active model bound to provider"
                else:
                    runtime_config = provider.get("config", {}) or {}
                    if not isinstance(runtime_config, dict):
                        runtime_config = {}
                    raw_timeout = runtime_config.get("timeout_sec", 20)
                    try:
                        probe_timeout_sec = int(raw_timeout)
                    except (TypeError, ValueError):
                        probe_timeout_sec = 20
                    probe_timeout_sec = max(5, min(probe_timeout_sec, 30))
                    runtime_config = {
                        **runtime_config,
                        "base_url": provider.get("base_url"),
                        "api_key": provider.get("api_key"),
                        "timeout_sec": probe_timeout_sec,
                    }
                    probe_payload = {
                        "model": probe_model.get("upstream_model")
                        or probe_model["model_key"],
                        "messages": [{"role": "user", "content": "ping"}],
                        "max_tokens": 1,
                    }
                    check_result["probe_model"] = probe_model["model_key"]
                    check_result["probe_upstream_model"] = probe_payload["model"]
                    check_result["timeout_sec"] = probe_timeout_sec

                    try:
                        async with asyncio.timeout(probe_timeout_sec):
                            await adapter.chat(probe_payload, runtime_config)
                        status = "healthy"
                        check_result["request_successful"] = True
                        check_result["response_type"] = "chat"
                    except asyncio.TimeoutError:
                        status = "unhealthy"
                        check_result["request_successful"] = False
                        error_message = f"timeout after {probe_timeout_sec}s"
                    except AdapterError as e:
                        status = "unhealthy"
                        check_result["request_successful"] = False
                        error_message = str(e)[:200]
                    except Exception as e:
                        status = "unhealthy"
                        check_result["request_successful"] = False
                        error_message = str(e)[:200]

        latency_ms = int((time.perf_counter() - started_at) * 1000)

        log_id = await run_in_threadpool(
            repository.insert_health_check,
            {
                "check_type": "provider",
                "target_id": provider_id,
                "target_name": provider["name"],
                "status": status,
                "check_result": check_result,
                "latency_ms": latency_ms,
                "error_message": error_message,
            },
        )

        return {
            "id": log_id,
            "provider_id": provider_id,
            "provider_name": provider["name"],
            "status": status,
            "latency_ms": latency_ms,
            "check_result": check_result,
            "error_message": error_message,
            "checked_at": time.time(),
        }

    @app.post(
        "/api/health/check/model/{model_id}", dependencies=[Depends(require_admin_auth)]
    )
    async def check_model_health(model_id: int) -> dict[str, Any]:
        model = await run_in_threadpool(repository.get_model, model_id)
        if not model:
            raise HTTPException(status_code=404, detail="model not found")

        provider = model.get("provider")
        if not provider:
            raise HTTPException(status_code=400, detail="model has no provider")

        import asyncio

        started_at = time.perf_counter()
        status = "unknown"
        check_result: dict[str, Any] = {}
        error_message = None

        test_payload = {
            "model": model["upstream_model"],
            "messages": [{"role": "user", "content": "ping"}],
            "max_tokens": 5,
        }

        provider_config = await run_in_threadpool(
            repository.get_provider, provider["id"]
        )
        if not provider_config:
            raise HTTPException(status_code=400, detail="provider config not found")

        adapter = adapter_registry.get(provider["name"])
        if adapter:
            try:
                async with asyncio.timeout(30):
                    resp = await adapter.chat(
                        test_payload,
                        {
                            "base_url": provider_config.get("base_url"),
                            "api_key": provider_config.get("api_key"),
                            "config": provider_config.get("config", {}),
                        },
                    )
                    status = "healthy"
                    check_result["request_successful"] = True
                    check_result["response_type"] = "chat"
            except asyncio.TimeoutError:
                status = "unhealthy"
                check_result["request_successful"] = False
                error_message = "timeout after 30s"
            except AdapterError as e:
                status = "unhealthy"
                check_result["request_successful"] = False
                error_message = str(e)[:200]
            except Exception as e:
                status = "unhealthy"
                check_result["request_successful"] = False
                error_message = str(e)[:200]
        else:
            status = "unknown"
            error_message = f"no adapter for provider {provider['name']}"

        latency_ms = int((time.perf_counter() - started_at) * 1000)

        log_id = await run_in_threadpool(
            repository.insert_health_check,
            {
                "check_type": "model",
                "target_id": model_id,
                "target_name": model["model_key"],
                "status": status,
                "check_result": check_result,
                "latency_ms": latency_ms,
                "error_message": error_message,
            },
        )

        await run_in_threadpool(
            repository.update_model,
            model_id,
            {"health_status": status},
        )

        return {
            "id": log_id,
            "model_id": model_id,
            "model_key": model["model_key"],
            "provider_name": provider["name"],
            "status": status,
            "latency_ms": latency_ms,
            "check_result": check_result,
            "error_message": error_message,
            "checked_at": time.time(),
        }

    def httpx_async_client():
        import httpx

        return httpx.AsyncClient()

    @app.post("/v1/chat/completions", dependencies=[Depends(require_client_auth)])
    async def chat_completions(request: Request):
        try:
            payload = await request.json()
        except Exception as exc:
            raise HTTPException(status_code=400, detail="invalid json payload") from exc

        if not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="payload must be a json object")

        model_name = payload.get("model")
        if not isinstance(model_name, str) or not model_name.strip():
            raise HTTPException(status_code=400, detail="model is required")

        is_stream = bool(payload.get("stream", False))
        request_id = str(
            getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:20]}")
        )
        task_id, stock_code = _extract_task_fields(payload)

        started_at = time.perf_counter()
        attempted_chain: list[str] = []
        errors: list[str] = []

        # Get model info to retrieve upstream_model
        model_info = await run_in_threadpool(repository.get_model_by_key, model_name)
        upstream_model = model_info.get("upstream_model") if model_info else None

        # Replace model in payload with upstream_model if available
        if upstream_model:
            payload = {**payload, "model": upstream_model}

        try:
            route_rule = await run_in_threadpool(repository.get_route_rule, model_name)
        except Exception as exc:  # noqa: BLE001
            logger.exception("route_rule_fetch_failed model=%s", model_name)
            raise HTTPException(
                status_code=503, detail=f"route repository unavailable: {exc}"
            ) from exc

        try:
            decision = router_engine.decide(model_name, route_rule)
        except RouteNotFoundError as exc:
            latency_ms = int((time.perf_counter() - started_at) * 1000)
            await safe_insert_call_log(
                {
                    "request_id": request_id,
                    "task_id": task_id,
                    "stock_code": stock_code,
                    "model_name": model_name,
                    "primary_provider": None,
                    "fallback_provider": None,
                    "route_chain": [],
                    "selected_provider": None,
                    "status": "failed",
                    "http_status": 400,
                    "error_message": str(exc),
                    "prompt_tokens": None,
                    "completion_tokens": None,
                    "total_tokens": None,
                    "latency_ms": latency_ms,
                    "is_stream": is_stream,
                    "request_body": payload,
                    "response_body": None,
                }
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        for provider_name in decision.provider_chain:
            attempted_chain.append(provider_name)

            adapter = adapter_registry.get(provider_name)
            if adapter is None:
                errors.append(f"{provider_name}: adapter is not supported")
                continue

            try:
                provider_row = await run_in_threadpool(
                    repository.get_provider_config, provider_name
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception(
                    "provider_config_fetch_failed provider=%s", provider_name
                )
                errors.append(f"{provider_name}: provider config unavailable ({exc})")
                continue
            if not provider_row or not provider_row.get("is_enabled", True):
                errors.append(f"{provider_name}: provider config missing or disabled")
                continue

            provider_config = provider_row.get("config") or {}

            try:
                if is_stream:
                    stream_handle = await adapter.prepare_stream(
                        payload, provider_config
                    )

                    async def stream_wrapper(
                        selected_provider: str = provider_name,
                    ):
                        stream_error: str | None = None
                        try:
                            async for chunk in stream_handle.iterator:
                                yield chunk
                        except Exception as exc:  # noqa: BLE001
                            stream_error = str(exc)
                            logger.exception(
                                "stream provider failed: %s", selected_provider
                            )
                            raise
                        finally:
                            await stream_handle.close()
                            latency_ms = int((time.perf_counter() - started_at) * 1000)
                            await safe_insert_call_log(
                                {
                                    "request_id": request_id,
                                    "task_id": task_id,
                                    "stock_code": stock_code,
                                    "model_name": model_name,
                                    "primary_provider": decision.primary_provider,
                                    "fallback_provider": decision.fallback_provider,
                                    "route_chain": attempted_chain,
                                    "selected_provider": selected_provider,
                                    "status": "failed" if stream_error else "success",
                                    "http_status": 502 if stream_error else 200,
                                    "error_message": stream_error,
                                    "prompt_tokens": None,
                                    "completion_tokens": None,
                                    "total_tokens": None,
                                    "latency_ms": latency_ms,
                                    "is_stream": True,
                                    "request_body": payload,
                                    "response_body": None,
                                }
                            )

                    return StreamingResponse(
                        stream_wrapper(), media_type="text/event-stream"
                    )

                response_payload = await adapter.chat(payload, provider_config)
                prompt_tokens, completion_tokens, total_tokens = _extract_usage(
                    response_payload
                )
                latency_ms = int((time.perf_counter() - started_at) * 1000)

                await safe_insert_call_log(
                    {
                        "request_id": request_id,
                        "task_id": task_id,
                        "stock_code": stock_code,
                        "model_name": model_name,
                        "primary_provider": decision.primary_provider,
                        "fallback_provider": decision.fallback_provider,
                        "route_chain": attempted_chain,
                        "selected_provider": provider_name,
                        "status": "success",
                        "http_status": 200,
                        "error_message": None,
                        "prompt_tokens": prompt_tokens,
                        "completion_tokens": completion_tokens,
                        "total_tokens": total_tokens,
                        "latency_ms": latency_ms,
                        "is_stream": False,
                        "request_body": payload,
                        "response_body": response_payload,
                    }
                )

                return JSONResponse(response_payload)
            except AdapterError as exc:
                errors.append(f"{provider_name}: {exc}")
            except Exception as exc:  # noqa: BLE001
                logger.exception("provider request failed: %s", provider_name)
                errors.append(f"{provider_name}: {exc}")

        latency_ms = int((time.perf_counter() - started_at) * 1000)
        error_text = " | ".join(errors) if errors else "all providers failed"

        await safe_insert_call_log(
            {
                "request_id": request_id,
                "task_id": task_id,
                "stock_code": stock_code,
                "model_name": model_name,
                "primary_provider": decision.primary_provider,
                "fallback_provider": decision.fallback_provider,
                "route_chain": attempted_chain,
                "selected_provider": None,
                "status": "failed",
                "http_status": 502,
                "error_message": error_text,
                "prompt_tokens": None,
                "completion_tokens": None,
                "total_tokens": None,
                "latency_ms": latency_ms,
                "is_stream": is_stream,
                "request_body": payload,
                "response_body": None,
            }
        )

        raise HTTPException(
            status_code=502,
            detail={
                "message": f"all providers failed for model: {model_name}",
                "errors": errors,
            },
        )

    return app


app = create_app()
