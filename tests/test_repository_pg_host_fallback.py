from __future__ import annotations

from unittest.mock import MagicMock, patch

import psycopg

from app.config import Settings
from app.repository import PostgresRepository


def test_candidate_hosts_prefers_localhost_when_pg_alias_used() -> None:
    repo = PostgresRepository(Settings(PG_HOST="pg"))
    assert repo._candidate_hosts() == ["pg", "127.0.0.1"]


def test_candidate_hosts_keeps_explicit_host_without_fallback() -> None:
    repo = PostgresRepository(Settings(PG_HOST="db.internal"))
    assert repo._candidate_hosts() == ["db.internal"]


def test_get_conn_retries_localhost_after_pg_resolution_failure() -> None:
    repo = PostgresRepository(Settings(PG_HOST="pg"))
    fake_conn = MagicMock()

    with patch(
        "app.repository.psycopg.connect",
        side_effect=[
            psycopg.OperationalError("failed to resolve host 'pg'"),
            fake_conn,
        ],
    ) as connect_mock:
        conn = repo._get_conn()

    assert conn is fake_conn
    assert connect_mock.call_args_list[0].kwargs["host"] == "pg"
    assert connect_mock.call_args_list[1].kwargs["host"] == "127.0.0.1"
