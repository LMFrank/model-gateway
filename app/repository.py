from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date, datetime, time, timedelta
from typing import Any

import pymysql
from pymysql.cursors import DictCursor

from app.config import Settings


class RepositoryError(Exception):
    pass


class MySQLRepository:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def _get_conn(self) -> pymysql.Connection:
        return pymysql.connect(
            host=self.settings.mysql_host,
            port=self.settings.mysql_port,
            user=self.settings.mysql_user,
            password=self.settings.mysql_password,
            database=self.settings.mysql_database,
            charset=self.settings.mysql_charset,
            connect_timeout=self.settings.mysql_connect_timeout,
            cursorclass=DictCursor,
            autocommit=True,
        )

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
    def _safe_json_dumps(value: Any, limit: int = 20000) -> str | None:
        if value is None:
            return None
        try:
            text = json.dumps(value, ensure_ascii=False)
        except TypeError:
            text = json.dumps(str(value), ensure_ascii=False)
        if len(text) > limit:
            # JSON 列必须保持合法，不能直接截断序列化字符串
            preview_limit = max(256, min(limit // 2, 8000))
            overflow = len(text) - preview_limit
            payload = {
                "_truncated": True,
                "_original_length": len(text),
                "_overflow_chars": overflow,
                "preview": text[:preview_limit],
            }
            return json.dumps(payload, ensure_ascii=False)
        return text

    @staticmethod
    def _p95(values: list[int]) -> int | None:
        cleaned = sorted([v for v in values if v is not None])
        if not cleaned:
            return None
        idx = max(0, math.ceil(len(cleaned) * 0.95) - 1)
        return cleaned[idx]

    def healthcheck(self) -> bool:
        try:
            with self._get_conn() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            return True
        except Exception:
            return False

    def get_route_rule(self, model_name: str) -> dict[str, Any] | None:
        sql = """
        SELECT model_name, primary_provider, fallback_provider, is_enabled, description, created_at, updated_at
        FROM route_rules
        WHERE model_name = %s
        LIMIT 1
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (model_name,))
                row = cursor.fetchone()
        if not row:
            return None
        row["is_enabled"] = bool(row.get("is_enabled", 1))
        return row

    def list_route_rules(self) -> list[dict[str, Any]]:
        sql = """
        SELECT model_name, primary_provider, fallback_provider, is_enabled, description, created_at, updated_at
        FROM route_rules
        ORDER BY model_name ASC
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()
        for row in rows:
            row["is_enabled"] = bool(row.get("is_enabled", 1))
        return rows

    def upsert_route_rules(self, rules: list[dict[str, Any]]) -> int:
        if not rules:
            return 0

        sql = """
        INSERT INTO route_rules (model_name, primary_provider, fallback_provider, is_enabled, description)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            primary_provider = VALUES(primary_provider),
            fallback_provider = VALUES(fallback_provider),
            is_enabled = VALUES(is_enabled),
            description = VALUES(description),
            updated_at = CURRENT_TIMESTAMP
        """

        values = [
            (
                item["model_name"],
                item["primary_provider"],
                item.get("fallback_provider"),
                1 if item.get("is_enabled", True) else 0,
                item.get("description"),
            )
            for item in rules
        ]

        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, values)
                return cursor.rowcount

    def get_provider_config(self, provider_name: str) -> dict[str, Any] | None:
        sql = """
        SELECT provider_name, config_json, is_enabled, created_at, updated_at
        FROM provider_configs
        WHERE provider_name = %s
        LIMIT 1
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, (provider_name,))
                row = cursor.fetchone()

        if not row:
            return None

        return {
            "provider_name": row["provider_name"],
            "config": self._json_load(row.get("config_json")) or {},
            "is_enabled": bool(row.get("is_enabled", 1)),
            "created_at": row.get("created_at"),
            "updated_at": row.get("updated_at"),
        }

    def list_provider_configs(self) -> list[dict[str, Any]]:
        sql = """
        SELECT provider_name, config_json, is_enabled, created_at, updated_at
        FROM provider_configs
        ORDER BY provider_name ASC
        """
        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql)
                rows = cursor.fetchall()

        out = []
        for row in rows:
            out.append(
                {
                    "provider_name": row["provider_name"],
                    "config": self._json_load(row.get("config_json")) or {},
                    "is_enabled": bool(row.get("is_enabled", 1)),
                    "created_at": row.get("created_at"),
                    "updated_at": row.get("updated_at"),
                }
            )
        return out

    def upsert_provider_configs(self, providers: list[dict[str, Any]]) -> int:
        if not providers:
            return 0

        sql = """
        INSERT INTO provider_configs (provider_name, config_json, is_enabled)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
            config_json = VALUES(config_json),
            is_enabled = VALUES(is_enabled),
            updated_at = CURRENT_TIMESTAMP
        """

        values = [
            (
                item["provider_name"],
                self._safe_json_dumps(item.get("config", {})),
                1 if item.get("is_enabled", True) else 0,
            )
            for item in providers
        ]

        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.executemany(sql, values)
                return cursor.rowcount

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
        """

        values = (
            log_data.get("request_id"),
            log_data.get("task_id"),
            log_data.get("stock_code"),
            log_data.get("model_name"),
            log_data.get("primary_provider"),
            log_data.get("fallback_provider"),
            self._safe_json_dumps(log_data.get("route_chain", [])),
            log_data.get("selected_provider"),
            log_data.get("status"),
            log_data.get("http_status"),
            (log_data.get("error_message") or "")[:2000] or None,
            log_data.get("prompt_tokens"),
            log_data.get("completion_tokens"),
            log_data.get("total_tokens"),
            log_data.get("latency_ms"),
            1 if log_data.get("is_stream", False) else 0,
            self._safe_json_dumps(log_data.get("request_body")),
            self._safe_json_dumps(log_data.get("response_body")),
        )

        with self._get_conn() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, values)
                return int(cursor.lastrowid)

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
            row["is_stream"] = bool(row.get("is_stream", 0))
            row["route_chain"] = self._json_load(row.get("route_chain")) or []

        return {"total": total, "items": items}

    def get_usage_summary(self, date_from: date | None = None, date_to: date | None = None) -> dict[str, Any]:
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
        all_latencies = [int(row["latency_ms"]) for row in rows if row.get("latency_ms") is not None]

        by_model: dict[str, list[dict[str, Any]]] = defaultdict(list)
        by_provider: dict[str, list[dict[str, Any]]] = defaultdict(list)

        for row in rows:
            by_model[str(row.get("model_name") or "unknown")].append(row)
            by_provider[str(row.get("selected_provider") or "unknown")].append(row)

        def _build_group(items: dict[str, list[dict[str, Any]]], key_name: str) -> list[dict[str, Any]]:
            output = []
            for key, group_rows in sorted(items.items(), key=lambda x: x[0]):
                calls = len(group_rows)
                failed = sum(1 for r in group_rows if r.get("status") != "success")
                tokens = sum(int(r.get("total_tokens") or 0) for r in group_rows)
                latencies = [int(r["latency_ms"]) for r in group_rows if r.get("latency_ms") is not None]
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
            "failure_rate": round((failed_calls / total_calls) if total_calls else 0.0, 4),
            "total_tokens": total_tokens,
            "p95_latency_ms": self._p95(all_latencies),
            "by_model": _build_group(by_model, "model_name"),
            "by_provider": _build_group(by_provider, "provider_name"),
        }
