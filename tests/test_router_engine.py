import pytest

from app.router_engine import RouteNotFoundError, RouterEngine


def test_router_engine_exact_match_success() -> None:
    decision = RouterEngine.decide(
        "kimi-for-coding",
        {
            "model_name": "kimi-for-coding",
            "primary_provider": "kimi_cli",
            "fallback_provider": "qwen_api",
            "fallback_model_key": "qwen3.6-plus",
            "is_enabled": True,
        },
    )
    assert decision.primary_provider == "kimi_cli"
    assert decision.fallback_provider == "qwen_api"
    assert getattr(decision, "fallback_model_key", None) == "qwen3.6-plus"
    assert decision.provider_chain == ["kimi_cli", "qwen_api"]


def test_router_engine_disabled_rule() -> None:
    with pytest.raises(RouteNotFoundError):
        RouterEngine.decide(
            "kimi-for-coding",
            {
                "model_name": "kimi-for-coding",
                "primary_provider": "kimi_cli",
                "fallback_provider": "qwen_api",
                "is_enabled": False,
            },
        )


def test_router_engine_missing_rule() -> None:
    with pytest.raises(RouteNotFoundError):
        RouterEngine.decide("unknown-model", None)
