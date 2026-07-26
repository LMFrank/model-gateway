from app.config import Settings
from app.repository import PostgresRepository


class _FakeCursor:
    def __init__(self, rows=None, rowcount: int = 0) -> None:
        self.rows = rows or []
        self.rowcount = rowcount
        self.queries: list[str] = []
        self.params: list[object] = []

    def execute(self, sql, params=None) -> None:
        self.queries.append(str(sql))
        self.params.append(params)

    def fetchall(self):
        return self.rows

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConn:
    def __init__(self, cursor: _FakeCursor) -> None:
        self._cursor = cursor

    def cursor(self):
        return self._cursor

    def transaction(self):
        return self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_health_summary_counts_only_latest_check_per_target() -> None:
    cursor = _FakeCursor(
        rows=[
            {"check_type": "provider", "status": "healthy", "count": 2},
            {"check_type": "model", "status": "unhealthy", "count": 1},
        ]
    )
    repository = PostgresRepository(Settings())
    repository._get_conn = lambda: _FakeConn(cursor)  # type: ignore[method-assign]

    summary = repository.get_health_summary()

    assert "DISTINCT ON (check_type, target_id)" in cursor.queries[0]
    assert summary["providers"]["healthy"] == 2
    assert summary["models"]["unhealthy"] == 1


def test_delete_expired_call_logs_uses_configured_retention_days() -> None:
    cursor = _FakeCursor(rowcount=7)
    repository = PostgresRepository(Settings())
    repository._get_conn = lambda: _FakeConn(cursor)  # type: ignore[method-assign]

    cleanup = getattr(repository, "delete_expired_call_logs", None)
    assert callable(cleanup)
    assert cleanup(30) == 7
    assert "DELETE FROM call_logs" in cursor.queries[0]
    assert cursor.params[0] == (30,)


def test_delete_provider_removes_dependent_routes_before_provider() -> None:
    cursor = _FakeCursor(rowcount=1)
    repository = PostgresRepository(Settings())
    repository._get_conn = lambda: _FakeConn(cursor)  # type: ignore[method-assign]

    assert repository.delete_provider(7) is True

    assert len(cursor.queries) == 4
    assert "DELETE FROM route_rules" in cursor.queries[0]
    assert "DELETE FROM model_routes" in cursor.queries[1]
    assert "DELETE FROM provider_configs" in cursor.queries[2]
    assert "DELETE FROM providers" in cursor.queries[3]
    assert cursor.params == [(7,), (7,), (7,), (7,)]


def test_delete_model_removes_primary_and_fallback_routes_before_model() -> None:
    cursor = _FakeCursor(rowcount=1)
    repository = PostgresRepository(Settings())
    repository._get_conn = lambda: _FakeConn(cursor)  # type: ignore[method-assign]

    assert repository.delete_model(34) is True

    assert len(cursor.queries) == 3
    assert "DELETE FROM route_rules" in cursor.queries[0]
    assert "fallback_model_key" in cursor.queries[0]
    assert "DELETE FROM model_routes" in cursor.queries[1]
    assert "DELETE FROM models" in cursor.queries[2]
    assert cursor.params == [(34,), (34,), (34,)]
