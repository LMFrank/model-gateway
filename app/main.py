from __future__ import annotations

import logging
import time
import uuid
from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse

from app.adapters import KimiCliAdapter, QwenApiAdapter
from app.adapters.base import AdapterError
from app.auth import require_admin_auth, require_client_auth
from app.config import get_settings
from app.repository import PostgresRepository
from app.router_engine import RouteNotFoundError, RouterEngine
from app.schemas import ProviderConfigsUpsertRequest, RouteRulesUpsertRequest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("model-gateway")


def _extract_usage(response_payload: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
    usage = response_payload.get("usage") if isinstance(response_payload, dict) else None
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

    app = FastAPI(title="Model Gateway", version="0.1.0")

    repository = PostgresRepository(settings)
    router_engine = RouterEngine()
    adapter_registry = {
        "kimi_cli": KimiCliAdapter(settings),
        "kimi_api": QwenApiAdapter(settings),
        "qwen_api": QwenApiAdapter(settings),
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
        request_id = request.headers.get("X-Request-Id") or f"req-{uuid.uuid4().hex[:20]}"
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        return response

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        db_ok = await run_in_threadpool(repository.healthcheck)
        if not db_ok:
            raise HTTPException(status_code=503, detail="database unavailable")
        return {"status": "ok"}

    @app.get("/admin/routes", dependencies=[Depends(require_admin_auth)])
    async def list_routes() -> dict[str, Any]:
        items = await run_in_threadpool(repository.list_route_rules)
        return {"items": items}

    @app.post("/admin/routes", dependencies=[Depends(require_admin_auth)])
    async def upsert_routes(body: RouteRulesUpsertRequest) -> dict[str, Any]:
        if not body.rules:
            raise HTTPException(status_code=400, detail="rules cannot be empty")
        await run_in_threadpool(repository.upsert_route_rules, [item.model_dump() for item in body.rules])
        items = await run_in_threadpool(repository.list_route_rules)
        return {"items": items}

    @app.get("/admin/providers", dependencies=[Depends(require_admin_auth)])
    async def list_providers() -> dict[str, Any]:
        items = await run_in_threadpool(repository.list_provider_configs)
        return {"items": items}

    @app.post("/admin/providers", dependencies=[Depends(require_admin_auth)])
    async def upsert_providers(body: ProviderConfigsUpsertRequest) -> dict[str, Any]:
        if not body.providers:
            raise HTTPException(status_code=400, detail="providers cannot be empty")
        await run_in_threadpool(repository.upsert_provider_configs, [item.model_dump() for item in body.providers])
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
        request_id = str(getattr(request.state, "request_id", f"req-{uuid.uuid4().hex[:20]}"))
        task_id, stock_code = _extract_task_fields(payload)

        started_at = time.perf_counter()
        attempted_chain: list[str] = []
        errors: list[str] = []

        try:
            route_rule = await run_in_threadpool(repository.get_route_rule, model_name)
        except Exception as exc:  # noqa: BLE001
            logger.exception("route_rule_fetch_failed model=%s", model_name)
            raise HTTPException(status_code=503, detail=f"route repository unavailable: {exc}") from exc

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
                provider_row = await run_in_threadpool(repository.get_provider_config, provider_name)
            except Exception as exc:  # noqa: BLE001
                logger.exception("provider_config_fetch_failed provider=%s", provider_name)
                errors.append(f"{provider_name}: provider config unavailable ({exc})")
                continue
            if not provider_row or not provider_row.get("is_enabled", True):
                errors.append(f"{provider_name}: provider config missing or disabled")
                continue

            provider_config = provider_row.get("config") or {}

            try:
                if is_stream:
                    stream_handle = await adapter.prepare_stream(payload, provider_config)

                    async def stream_wrapper(
                        selected_provider: str = provider_name,
                    ):
                        stream_error: str | None = None
                        try:
                            async for chunk in stream_handle.iterator:
                                yield chunk
                        except Exception as exc:  # noqa: BLE001
                            stream_error = str(exc)
                            logger.exception("stream provider failed: %s", selected_provider)
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

                    return StreamingResponse(stream_wrapper(), media_type="text/event-stream")

                response_payload = await adapter.chat(payload, provider_config)
                prompt_tokens, completion_tokens, total_tokens = _extract_usage(response_payload)
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
