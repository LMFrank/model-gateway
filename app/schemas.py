from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


class RouteRuleUpsert(BaseModel):
    model_name: str = Field(min_length=1, max_length=128)
    primary_provider: str = Field(min_length=1, max_length=64)
    fallback_provider: str | None = Field(default=None, max_length=64)
    is_enabled: bool = True
    description: str | None = Field(default=None, max_length=255)


class RouteRulesUpsertRequest(BaseModel):
    rules: list[RouteRuleUpsert]


class RouteRuleOut(RouteRuleUpsert):
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProviderConfigUpsert(BaseModel):
    provider_name: str = Field(min_length=1, max_length=64)
    config: dict[str, Any] = Field(default_factory=dict)
    is_enabled: bool = True


class ProviderConfigsUpsertRequest(BaseModel):
    providers: list[ProviderConfigUpsert]


class ProviderConfigOut(ProviderConfigUpsert):
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CallLogQuery(BaseModel):
    task_id: str | None = None
    stock_code: str | None = None
    model: str | None = None
    status: str | None = None
    limit: int = 100
    offset: int = 0


class UsageSummaryQuery(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
