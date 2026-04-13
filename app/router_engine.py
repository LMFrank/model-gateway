from dataclasses import dataclass


class RouteNotFoundError(Exception):
    pass


@dataclass(slots=True)
class RouteDecision:
    model_name: str
    primary_provider: str
    fallback_provider: str | None

    @property
    def provider_chain(self) -> list[str]:
        return [self.primary_provider]


class RouterEngine:
    """按模型名精确匹配并返回路由决策。

    路由引擎只读取 primary_provider；fallback_provider
    在兼容输出结构中固定返回 None。
    """

    @staticmethod
    def decide(model_name: str, rule: dict | None) -> RouteDecision:
        if not rule:
            raise RouteNotFoundError(f"route rule not found for model: {model_name}")
        if not rule.get("is_enabled", True):
            raise RouteNotFoundError(f"route rule disabled for model: {model_name}")

        primary = (rule.get("primary_provider") or "").strip()
        if not primary:
            raise RouteNotFoundError(f"primary provider missing for model: {model_name}")

        return RouteDecision(
            model_name=model_name,
            primary_provider=primary,
            fallback_provider=None,
        )
