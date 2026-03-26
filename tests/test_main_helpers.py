from app.main import _extract_task_fields, _extract_usage


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
