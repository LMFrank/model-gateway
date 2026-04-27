from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

import psycopg
from psycopg.rows import dict_row
from psycopg.types.json import Json

from app.config import Settings
from app.crypto import ApiKeyCrypto


class RepositoryError(Exception):
    pass


class PostgresRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.api_key_crypto = ApiKeyCrypto(
            settings.api_key_encryption_key,
            enabled=settings.encrypt_api_keys,
        )

    def _get_conn(self) -> psycopg.Connection:
        last_error: psycopg.Error | None = None
        for host in self._candidate_hosts():
            try:
                return psycopg.connect(
                    host=host,
                    port=self.settings.pg_port,
                    user=self.settings.pg_user,
                    password=self.settings.pg_password,
                    dbname=self.settings.pg_database,
                    connect_timeout=self.settings.pg_connect_timeout,
                    row_factory=dict_row,
                    autocommit=True,
                )
            except psycopg.OperationalError as exc:
                last_error = exc
                continue
        if last_error is not None:
            raise last_error
        raise RuntimeError("postgres connection candidates exhausted")

    def _candidate_hosts(self) -> list[str]:
        host = str(self.settings.pg_host or "").strip() or "127.0.0.1"
        if host != "pg":
            return [host]
        return ["pg", "127.0.0.1"]

    @staticmethod
    def _json_load(value: Any) -> Any:
        if value is None:
            return None
        if isinstance(value, (dict, list)):
            return value
        if isinstance(value, (bytes, bytearray)):
            value = value.decode("utf-8", errors="ignore")
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                return value
        return value

    @staticmethod
    def _safe_json_value(value: Any, limit: int = 20000) -> Any:
        if value is None:
            return None

        normalized = value
        try:
            text = json.dumps(normalized, ensure_ascii=False)
        except TypeError:
            normalized = str(value)
            text = json.dumps(normalized, ensure_ascii=False)

        if len(text) > limit:
            preview_limit = max(256, min(limit // 2, 8000))
            overflow = len(text) - preview_limit
            return {
                "_truncated": True,
                "_original_length": len(text),
                "_overflow_chars": overflow,
                "preview": text[:preview_limit],
            }

        return normalized

    @staticmethod
    def _p95(values: list[int]) -> int | None:
        cleaned = sorted([v for v in values if v is not None])
        if not cleaned:
            return None
        idx = max(0, math.ceil(len(cleaned) * 0.95) - 1)
        return cleaned[idx]

    @staticmethod
    def _to_json_param(value: Any) -> Json | None:
        if value is None:
            return None
        return Json(value)

    @staticmethod
    def _normalize_optional_text(value: Any) -> str | None:
        if value is None:
            return None
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return str(value)

    @staticmethod
    def _mask_api_key(value: str | None) -> str | None:
        if not value:
            return None
        if len(value) <= 6:
            return "*" * len(value)
        return f"{value[:3]}***{value[-4:]}"

    def _decrypt_api_key(self, value: Any) -> str | None:
        normalized = self._normalize_optional_text(value)
        if not normalized:
            return None
        return self.api_key_crypto.decrypt(normalized)

    def _encrypt_api_key(self, value: Any) -> str | None:
        normalized = self._normalize_optional_text(value)
        if not normalized:
            return None
        return self.api_key_crypto.encrypt(normalized)

    def _provider_row_to_dict(
        self, row: dict[str, Any], *, include_secret: bool = False
    ) -> dict[str, Any]:
        api_key = self._decrypt_api_key(row.get("api_key"))
        return {
            "id": row["id"],
            "name": row["name"],
            "display_name": row["display_name"],
            "provider_type": row["provider_type"],
            "base_url": row["base_url"],
            "api_key": api_key if include_secret else None,
            "masked_api_key": self._mask_api_key(api_key),
            "has_api_key": bool(api_key),
            "config": self._json_load(row.get("config_json")) or {},
            "description": row["description"],
            "is_enabled": bool(row.get("is_enabled", True)),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    @staticmethod
    def _provider_to_compat_config(provider: dict[str, Any]) -> dict[str, Any]:
        config = (provider.get("config") or {}).copy()
        config["base_url"] = provider.get("base_url")
        config["api_key"] = provider.get("api_key")
        return {
            "provider_name": provider["name"],
            "config": config,
            "is_enabled": provider["is_enabled"],
            "created_at": provider["created_at"],
            "updated_at": provider["updated_at"],
        }

    def healthcheck(self) -> bool:
        required_tables = (
            "providers",
            "models",
            "model_routes",
            "health_checks",
            "route_rules",
            "call_logs",
            "daily_usage_agg",
        )
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT tablename
                        FROM pg_tables
                        WHERE schemaname = 'public'
                          AND tablename = ANY(%s)
                        """,
                        (list(required_tables),),
                    )
                    existing = {row["tablename"] for row in cursor.fetchall()}
            return all(table in existing for table in required_tables)
        except Exception:
            return False

    # ==========================================================================
    # Provider CRUD
    # ==========================================================================

    def get_provider(
        self, provider_id: int, *, include_secret: bool = False
    ) -> dict[str, Any] | None:
        """根据 ID 获取 Provider"""
        sql = """
        SELECT id, name, display_name, provider_type, base_url, api_key, 
               config_json, description, is_enabled, created_at, updated_at
        FROM providers
        WHERE id = %s
        LIMIT 1
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (provider_id,))
                row = cursor.fetchone()
        if not row:
            return None
        return self._provider_row_to_dict(row, include_secret=include_secret)

    def get_provider_by_name(
        self, name: str, *, include_secret: bool = True
    ) -> dict[str, Any] | None:
        """根据名称获取 Provider"""
        sql = """
        SELECT id, name, display_name, provider_type, base_url, api_key, 
               config_json, description, is_enabled, created_at, updated_at
        FROM providers
        WHERE name = %s
        LIMIT 1
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (name,))
                row = cursor.fetchone()
        if not row:
            return None
        return self._provider_row_to_dict(row, include_secret=include_secret)

    def list_providers(self) -> list[dict[str, Any]]:
        """列出所有 Providers"""
        sql = """
        SELECT id, name, display_name, provider_type, base_url, api_key, 
               config_json, description, is_enabled, created_at, updated_at
        FROM providers
        ORDER BY name ASC
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()

        out = []
        for row in rows:
            out.append(self._provider_row_to_dict(row))
        return out

    def create_provider(self, data: dict[str, Any]) -> int:
        """创建 Provider"""
        sql = """
        INSERT INTO providers (name, display_name, provider_type, base_url, api_key, 
                               config_json, description, is_enabled)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        values = (
            data["name"],
            data["display_name"],
            data["provider_type"],
            data.get("base_url"),
            self._encrypt_api_key(data.get("api_key")),
            self._to_json_param(self._safe_json_value(data.get("config", {}))),
            data.get("description"),
            bool(data.get("is_enabled", True)),
        )
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, values)
                row = cursor.fetchone()
                return int(row["id"])

    def update_provider(self, provider_id: int, data: dict[str, Any]) -> bool:
        """更新 Provider"""
        fields = []
        values = []

        if "display_name" in data:
            fields.append("display_name = %s")
            values.append(data["display_name"])
        if "provider_type" in data:
            fields.append("provider_type = %s")
            values.append(data["provider_type"])
        if "base_url" in data:
            fields.append("base_url = %s")
            values.append(data["base_url"])
        if "api_key" in data and self._normalize_optional_text(data.get("api_key")):
            fields.append("api_key = %s")
            values.append(self._encrypt_api_key(data["api_key"]))
        if "config" in data:
            fields.append("config_json = %s")
            values.append(self._to_json_param(self._safe_json_value(data["config"])))
        if "description" in data:
            fields.append("description = %s")
            values.append(data["description"])
        if "is_enabled" in data:
            fields.append("is_enabled = %s")
            values.append(bool(data["is_enabled"]))

        if not fields:
            return False

        fields.append("updated_at = NOW()")
        values.append(provider_id)

        sql = f"UPDATE providers SET {', '.join(fields)} WHERE id = %s"
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, tuple(values))
                return cursor.rowcount > 0

    def delete_provider(self, provider_id: int) -> bool:
        """删除 Provider"""
        sql = "DELETE FROM providers WHERE id = %s"
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (provider_id,))
                return cursor.rowcount > 0

    # ==========================================================================
    # Model CRUD
    # ==========================================================================

    def get_model(self, model_id: int) -> dict[str, Any] | None:
        """根据 ID 获取 Model"""
        sql = """
        SELECT m.id, m.model_key, m.display_name, m.upstream_model, m.default_params,
               m.description, m.notes, m.is_active, m.health_status, m.last_health_check,
               m.created_at, m.updated_at,
               p.id as provider_id, p.name as provider_name, p.display_name as provider_display_name
        FROM models m
        JOIN providers p ON m.provider_id = p.id
        WHERE m.id = %s
        LIMIT 1
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (model_id,))
                row = cursor.fetchone()
        if not row:
            return None
        return self._model_row_to_dict(row)

    def get_model_by_key(self, model_key: str) -> dict[str, Any] | None:
        """根据 model_key 获取 Model"""
        sql = """
        SELECT m.id, m.model_key, m.display_name, m.upstream_model, m.default_params,
               m.description, m.notes, m.is_active, m.health_status, m.last_health_check,
               m.created_at, m.updated_at,
               p.id as provider_id, p.name as provider_name, p.display_name as provider_display_name
        FROM models m
        JOIN providers p ON m.provider_id = p.id
        WHERE m.model_key = %s
        LIMIT 1
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (model_key,))
                row = cursor.fetchone()
        if not row:
            return None
        return self._model_row_to_dict(row)

    def list_models(self, provider_id: int | None = None) -> list[dict[str, Any]]:
        """列出所有 Models，可按 Provider 筛选"""
        sql = """
        SELECT m.id, m.model_key, m.display_name, m.upstream_model, m.default_params,
               m.description, m.notes, m.is_active, m.health_status, m.last_health_check,
               m.created_at, m.updated_at,
               p.id as provider_id, p.name as provider_name, p.display_name as provider_display_name
        FROM models m
        JOIN providers p ON m.provider_id = p.id
        """
        params = []
        if provider_id:
            sql += " WHERE m.provider_id = %s"
            params.append(provider_id)
        sql += " ORDER BY m.model_key ASC"

        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, tuple(params))
                rows = cursor.fetchall()

        return [self._model_row_to_dict(row) for row in rows]

    def create_model(self, data: dict[str, Any]) -> int:
        """创建 Model"""
        sql = """
        INSERT INTO models (provider_id, model_key, display_name, upstream_model, 
                            default_params, description, notes, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        values = (
            data["provider_id"],
            data["model_key"],
            data["display_name"],
            data["upstream_model"],
            self._to_json_param(self._safe_json_value(data.get("default_params", {}))),
            data.get("description"),
            data.get("notes"),
            bool(data.get("is_active", True)),
        )
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, values)
                row = cursor.fetchone()
                return int(row["id"])

    def update_model(self, model_id: int, data: dict[str, Any]) -> bool:
        """更新 Model"""
        fields = []
        values = []

        if "provider_id" in data:
            fields.append("provider_id = %s")
            values.append(data["provider_id"])
        if "display_name" in data:
            fields.append("display_name = %s")
            values.append(data["display_name"])
        if "upstream_model" in data:
            fields.append("upstream_model = %s")
            values.append(data["upstream_model"])
        if "default_params" in data:
            fields.append("default_params = %s")
            values.append(
                self._to_json_param(self._safe_json_value(data["default_params"]))
            )
        if "description" in data:
            fields.append("description = %s")
            values.append(data["description"])
        if "notes" in data:
            fields.append("notes = %s")
            values.append(data["notes"])
        if "is_active" in data:
            fields.append("is_active = %s")
            values.append(bool(data["is_active"]))
        if "health_status" in data:
            fields.append("health_status = %s")
            values.append(data["health_status"])
            fields.append("last_health_check = NOW()")

        if not fields:
            return False

        fields.append("updated_at = NOW()")
        values.append(model_id)

        sql = f"UPDATE models SET {', '.join(fields)} WHERE id = %s"
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, tuple(values))
                return cursor.rowcount > 0

    def delete_model(self, model_id: int) -> bool:
        """删除 Model"""
        sql = "DELETE FROM models WHERE id = %s"
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (model_id,))
                return cursor.rowcount > 0

    def _model_row_to_dict(self, row: dict[str, Any]) -> dict[str, Any]:
        """将 Model 查询结果转换为字典"""
        return {
            "id": row["id"],
            "model_key": row["model_key"],
            "display_name": row["display_name"],
            "upstream_model": row["upstream_model"],
            "default_params": self._json_load(row.get("default_params")) or {},
            "description": row["description"],
            "notes": row["notes"],
            "is_active": bool(row.get("is_active", True)),
            "health_status": row.get("health_status", "unknown"),
            "last_health_check": row.get("last_health_check"),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "provider": {
                "id": row["provider_id"],
                "name": row["provider_name"],
                "display_name": row["provider_display_name"],
            }
            if row.get("provider_id")
            else None,
        }

    # ==========================================================================
    # Route Rules
    # ==========================================================================

    def get_model_route(self, model_key: str) -> dict[str, Any] | None:
        """根据 model_key 获取路由规则"""
        sql = """
        SELECT r.model_key, r.is_enabled, r.priority, r.description, 
               r.created_at, r.updated_at,
               m.id as model_id, m.display_name as model_display_name, 
               m.upstream_model, m.is_active as model_is_active,
               p.id as provider_id, p.name as provider_name, p.provider_type
        FROM model_routes r
        JOIN models m ON r.model_key = m.model_key
        JOIN providers p ON m.provider_id = p.id
        WHERE r.model_key = %s
        LIMIT 1
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (model_key,))
                row = cursor.fetchone()
        if not row:
            return None
        return self._model_route_row_to_dict(row)

    def list_model_routes(self) -> list[dict[str, Any]]:
        """列出所有路由规则"""
        sql = """
        SELECT r.model_key, r.is_enabled, r.priority, r.description, 
               r.created_at, r.updated_at,
               m.id as model_id, m.display_name as model_display_name, 
               m.upstream_model, m.is_active as model_is_active,
               p.id as provider_id, p.name as provider_name, p.provider_type
        FROM model_routes r
        JOIN models m ON r.model_key = m.model_key
        JOIN providers p ON m.provider_id = p.id
        ORDER BY r.priority DESC, r.model_key ASC
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
        return [self._model_route_row_to_dict(row) for row in rows]

    def upsert_model_routes(self, rules: list[dict[str, Any]]) -> int:
        """批量增改路由规则"""
        if not rules:
            return 0

        sql = """
        INSERT INTO model_routes (model_key, is_enabled, priority, description)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (model_key) DO UPDATE SET
            is_enabled = EXCLUDED.is_enabled,
            priority = EXCLUDED.priority,
            description = EXCLUDED.description,
            updated_at = NOW()
        """

        values = [
            (
                item["model_key"],
                bool(item.get("is_enabled", True)),
                int(item.get("priority", 0)),
                item.get("description"),
            )
            for item in rules
        ]

        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, values)
        return len(values)

    def delete_model_route(self, model_key: str) -> bool:
        """删除路由规则"""
        sql = "DELETE FROM model_routes WHERE model_key = %s"
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (model_key,))
                return cursor.rowcount > 0

    def _model_route_row_to_dict(self, row: dict[str, Any]) -> dict[str, Any]:
        """将路由规则查询结果转换为字典"""
        return {
            "model_key": row["model_key"],
            "is_enabled": bool(row.get("is_enabled", True)),
            "priority": int(row.get("priority", 0)),
            "description": row["description"],
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
            "model": {
                "id": row["model_id"],
                "display_name": row["model_display_name"],
                "upstream_model": row["upstream_model"],
                "is_active": bool(row.get("model_is_active", True)),
            },
            "provider": {
                "id": row["provider_id"],
                "name": row["provider_name"],
                "provider_type": row["provider_type"],
            },
        }

    # ==========================================================================
    # Compatibility Adapters
    # ==========================================================================

    def get_route_rule(self, model_name: str) -> dict[str, Any] | None:
        """根据模型名获取兼容格式的路由规则"""
        rule = self.get_model_route(model_name)
        if not rule:
            return None
        # 转换为兼容格式
        return {
            "model_name": rule["model_key"],
            "primary_provider": rule["provider"]["name"]
            if rule.get("provider")
            else None,
            "fallback_provider": None,  # 核心路由结构不支持 fallback
            "is_enabled": rule["is_enabled"] and rule["model"]["is_active"],
            "description": rule["description"],
            "created_at": rule["created_at"],
            "updated_at": rule["updated_at"],
        }

    def list_route_rules(self) -> list[dict[str, Any]]:
        """列出兼容格式的路由规则"""
        rules = self.list_model_routes()
        return [
            {
                "model_name": rule["model_key"],
                "primary_provider": rule["provider"]["name"]
                if rule.get("provider")
                else None,
                "fallback_provider": None,
                "is_enabled": rule["is_enabled"] and rule["model"]["is_active"],
                "description": rule["description"],
                "created_at": rule["created_at"],
                "updated_at": rule["updated_at"],
            }
            for rule in rules
        ]

    def upsert_route_rules(self, rules: list[dict[str, Any]]) -> int:
        """批量增改兼容格式的路由规则"""
        model_route_records = []
        for rule in rules:
            model_name = str(rule.get("model_name") or "").strip()
            primary_provider = str(rule.get("primary_provider") or "").strip()
            model = self.get_model_by_key(model_name)
            if not model:
                raise RepositoryError(
                    f"compat route rule requires existing model: {model_name}"
                )

            current_provider = (model.get("provider") or {}).get("name")
            if current_provider != primary_provider:
                raise RepositoryError(
                    "compat route rule cannot change model provider binding; "
                    f"model {model_name} is bound to {current_provider or 'none'}, "
                    f"not {primary_provider or 'none'}"
                )

            model_route_records.append(
                {
                    "model_key": model_name,
                    "is_enabled": bool(rule.get("is_enabled", True)),
                    "priority": 0,
                    "description": rule.get("description"),
                }
            )
        return self.upsert_model_routes(model_route_records)

    def get_provider_config(self, provider_name: str) -> dict[str, Any] | None:
        """获取兼容格式的 Provider 配置"""
        provider = self.get_provider_by_name(provider_name, include_secret=True)
        if not provider:
            return None
        return self._provider_to_compat_config(provider)

    def list_provider_configs(self) -> list[dict[str, Any]]:
        """列出兼容格式的 Provider 配置"""
        providers = [
            self.get_provider_by_name(item["name"], include_secret=True)
            for item in self.list_providers()
        ]
        out = []
        for provider in providers:
            if not provider:
                continue
            out.append(self._provider_to_compat_config(provider))
        return out

    def upsert_provider_configs(self, providers: list[dict[str, Any]]) -> int:
        """批量更新兼容格式的 Provider 配置（不负责创建 Provider）"""
        for item in providers:
            name = item["provider_name"]
            existing = self.get_provider_by_name(name)
            config = item.get("config", {})
            if not isinstance(config, dict):
                raise RepositoryError(
                    f"compat provider config for {name} must be an object"
                )
            if not existing:
                raise RepositoryError(
                    "compat provider config can only update existing providers; "
                    f"create provider via /api/providers first: {name}"
                )
            inferred_provider_type = (
                existing.get("provider_type")
                if existing.get("provider_type") in {"api", "cli"}
                else "api"
                if self._normalize_optional_text(config.get("base_url"))
                else "cli"
            )
            has_base_url = bool(self._normalize_optional_text(config.get("base_url")))
            if inferred_provider_type == "api" and not (has_base_url or existing):
                raise RepositoryError(
                    f"compat provider config missing base_url for api provider: {name}"
                )
            data = {
                "name": name,
                "display_name": name,
                "provider_type": inferred_provider_type,
                "base_url": config.get("base_url"),
                "api_key": config.get("api_key"),
                "config": config,
                "is_enabled": bool(item.get("is_enabled", True)),
            }
            self.update_provider(existing["id"], data)
        return len(providers)

    # ==========================================================================
    # Call Logs
    # ==========================================================================

    def insert_call_log(self, log_data: dict[str, Any]) -> int:
        sql = """
        INSERT INTO call_logs (
            request_id,
            task_id,
            stock_code,
            model_name,
            primary_provider,
            fallback_provider,
            route_chain,
            selected_provider,
            status,
            http_status,
            error_message,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            latency_ms,
            is_stream,
            request_body,
            response_body
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id
        """

        values = (
            log_data.get("request_id"),
            log_data.get("task_id"),
            log_data.get("stock_code"),
            log_data.get("model_name"),
            log_data.get("primary_provider"),
            log_data.get("fallback_provider"),
            self._to_json_param(self._safe_json_value(log_data.get("route_chain", []))),
            log_data.get("selected_provider"),
            log_data.get("status"),
            log_data.get("http_status"),
            (log_data.get("error_message") or "")[:2000] or None,
            log_data.get("prompt_tokens"),
            log_data.get("completion_tokens"),
            log_data.get("total_tokens"),
            log_data.get("latency_ms"),
            bool(log_data.get("is_stream", False)),
            self._to_json_param(self._safe_json_value(log_data.get("request_body"))),
            self._to_json_param(self._safe_json_value(log_data.get("response_body"))),
        )

        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, values)
                row = cursor.fetchone() or {}
                return int(row.get("id", 0))

    def list_calls(self, filters: dict[str, Any]) -> dict[str, Any]:
        where_clauses = ["1=1"]
        params: list[Any] = []

        if filters.get("task_id"):
            where_clauses.append("task_id = %s")
            params.append(filters["task_id"])
        if filters.get("stock_code"):
            where_clauses.append("stock_code = %s")
            params.append(filters["stock_code"])
        if filters.get("model"):
            where_clauses.append("model_name = %s")
            params.append(filters["model"])
        if filters.get("status"):
            where_clauses.append("status = %s")
            params.append(filters["status"])

        where_sql = " AND ".join(where_clauses)

        limit = int(filters.get("limit", 100))
        offset = int(filters.get("offset", 0))

        count_sql = f"SELECT COUNT(*) AS total FROM call_logs WHERE {where_sql}"
        data_sql = f"""
        SELECT
            id,
            request_id,
            task_id,
            stock_code,
            model_name,
            primary_provider,
            fallback_provider,
            route_chain,
            selected_provider,
            status,
            http_status,
            error_message,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            latency_ms,
            is_stream,
            created_at
        FROM call_logs
        WHERE {where_sql}
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """

        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(count_sql, tuple(params))
                total = int((cursor.fetchone() or {}).get("total", 0))

                cursor.execute(data_sql, tuple([*params, limit, offset]))
                items = cursor.fetchall()

        for row in items:
            row["is_stream"] = bool(row.get("is_stream", False))
            row["route_chain"] = self._json_load(row.get("route_chain")) or []

        return {"total": total, "items": items}

    def get_usage_summary(
        self, date_from: date | None = None, date_to: date | None = None
    ) -> dict[str, Any]:
        if date_to is None:
            date_to = date.today()
        if date_from is None:
            date_from = date_to - timedelta(days=6)

        start_dt = datetime.combine(date_from, time.min)
        end_dt = datetime.combine(date_to + timedelta(days=1), time.min)

        sql = """
        SELECT model_name, selected_provider, status, total_tokens, latency_ms
        FROM call_logs
        WHERE created_at >= %s AND created_at < %s
        """

        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (start_dt, end_dt))
                rows = cursor.fetchall()

        total_calls = len(rows)
        failed_calls = sum(1 for row in rows if row.get("status") != "success")
        total_tokens = sum(int(row.get("total_tokens") or 0) for row in rows)
        all_latencies = [
            int(row["latency_ms"]) for row in rows if row.get("latency_ms") is not None
        ]

        by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for row in rows:
            by_model[str(row.get("model_name") or "unknown")].append(row)
            by_provider[str(row.get("selected_provider") or "unknown")].append(row)

        def _build_group(
            items: dict[str, list[dict[str, Any]]], key_name: str
        ) -> list[dict[str, Any]]:
            output = []
            for key, group_rows in sorted(items.items(), key=lambda x: x[0]):
                calls = len(group_rows)
                failed = sum(1 for r in group_rows if r.get("status") != "success")
                tokens = sum(int(r.get("total_tokens") or 0) for r in group_rows)
                latencies = [
                    int(r["latency_ms"])
                    for r in group_rows
                    if r.get("latency_ms") is not None
                ]
                output.append(
                    {
                        key_name: key,
                        "call_count": calls,
                        "failed_calls": failed,
                        "failure_rate": round((failed / calls) if calls else 0.0, 4),
                        "total_tokens": tokens,
                        "p95_latency_ms": self._p95(latencies),
                    }
                )
            return output

        return {
            "date_from": str(date_from),
            "date_to": str(date_to),
            "total_calls": total_calls,
            "failed_calls": failed_calls,
            "failure_rate": round(
                (failed_calls / total_calls) if total_calls else 0.0, 4
            ),
            "total_tokens": total_tokens,
            "p95_latency_ms": self._p95(all_latencies),
            "by_model": _build_group(by_model, "model_name"),
            "by_provider": _build_group(by_provider, "provider_name"),
        }

    # ==========================================================================
    # Health Checks
    # ==========================================================================

    def insert_health_check(self, data: dict[str, Any]) -> int:
        """插入健康检查记录"""
        sql = """
        INSERT INTO health_checks (check_type, target_id, target_name, status, 
                                   check_result, latency_ms, error_message)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id
        """
        values = (
            data["check_type"],
            data["target_id"],
            data["target_name"],
            data["status"],
            self._to_json_param(self._safe_json_value(data.get("check_result", {}))),
            data.get("latency_ms"),
            (data.get("error_message") or "")[:1000] or None,
        )
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, values)
                row = cursor.fetchone()
                return int(row["id"])

    def get_latest_health_check(
        self, check_type: str, target_id: int
    ) -> dict[str, Any] | None:
        """获取最新的健康检查记录"""
        sql = """
        SELECT id, check_type, target_id, target_name, status, check_result,
               latency_ms, error_message, checked_at
        FROM health_checks
        WHERE check_type = %s AND target_id = %s
        ORDER BY checked_at DESC
        LIMIT 1
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (check_type, target_id))
                row = cursor.fetchone()
        if not row:
            return None
        return {
            "id": row["id"],
            "check_type": row["check_type"],
            "target_id": row["target_id"],
            "target_name": row["target_name"],
            "status": row["status"],
            "check_result": self._json_load(row.get("check_result")) or {},
            "latency_ms": row.get("latency_ms"),
            "error_message": row.get("error_message"),
            "checked_at": row.get("checked_at"),
        }

    def list_health_checks(self, filters: dict[str, Any]) -> list[dict[str, Any]]:
        """列出健康检查记录"""
        where_clauses = ["1=1"]
        params: list[Any] = []

        if filters.get("check_type"):
            where_clauses.append("check_type = %s")
            params.append(filters["check_type"])
        if filters.get("target_id"):
            where_clauses.append("target_id = %s")
            params.append(filters["target_id"])
        if filters.get("status"):
            where_clauses.append("status = %s")
            params.append(filters["status"])

        limit = int(filters.get("limit", 50))
        where_sql = " AND ".join(where_clauses)

        sql = f"""
        SELECT id, check_type, target_id, target_name, status, check_result,
               latency_ms, error_message, checked_at
        FROM health_checks
        WHERE {where_sql}
        ORDER BY checked_at DESC
        LIMIT %s
        """

        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, tuple(params + [limit]))
                rows = cursor.fetchall()

        return [
            {
                "id": row["id"],
                "check_type": row["check_type"],
                "target_id": row["target_id"],
                "target_name": row["target_name"],
                "status": row["status"],
                "check_result": self._json_load(row.get("check_result")) or {},
                "latency_ms": row.get("latency_ms"),
                "error_message": row.get("error_message"),
                "checked_at": row.get("checked_at"),
            }
            for row in rows
        ]

    def get_health_summary(self) -> dict[str, Any]:
        """获取健康检查汇总统计"""
        sql = """
        SELECT 
            check_type,
            status,
            COUNT(*) as count
        FROM health_checks
        WHERE checked_at > NOW() - INTERVAL '24 hours'
        GROUP BY check_type, status
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()

        summary: dict[str, Any] = {
            "providers": {"healthy": 0, "unhealthy": 0, "unknown": 0},
            "models": {"healthy": 0, "unhealthy": 0, "unknown": 0},
        }
        for row in rows:
            check_type = row["check_type"]
            status = row["status"]
            count = int(row["count"])
            if check_type in summary and status in summary[check_type]:
                summary[check_type][status] = count

        return summary
