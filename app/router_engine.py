from dataclasses import dataclass


class RouteNotFoundError(Exception):
    pass


@dataclass(slots=True)
class RouteDecision:
    model_name: str
    primary_provider: str
    fallback_provider: str | None
    fallback_model_key: str | None

    @property
    def provider_chain(self) -> list[str]:
        chain = [self.primary_provider]
        fallback = (self.fallback_provider or "").strip()
        if fallback and fallback != self.primary_provider:
            chain.append(fallback)
        return chain


class RouterEngine:
    """按模型名精确匹配并返回有序 provider 路由决策。"""

    @staticmethod
    def decide(model_name: str, rule: dict | None) -> RouteDecision:
        if not rule:
            raise RouteNotFoundError(f"route rule not found for model: {model_name}")
        if not rule.get("is_enabled", True):
            raise RouteNotFoundError(f"route rule disabled for model: {model_name}")

        primary = (rule.get("primary_provider") or "").strip()
        if not primary:
            raise RouteNotFoundError(f"primary provider missing for model: {model_name}")

        fallback = str(rule.get("fallback_provider") or "").strip() or None
        if fallback == primary:
            fallback = None
        fallback_model_key = (
            str(rule.get("fallback_model_key") or "").strip() or None
        )
        if fallback and not fallback_model_key:
            raise RouteNotFoundError(
                f"fallback model missing for model: {model_name}"
            )

        return RouteDecision(
            model_name=model_name,
            primary_provider=primary,
            fallback_provider=fallback,
            fallback_model_key=fallback_model_key if fallback else None,
        )
