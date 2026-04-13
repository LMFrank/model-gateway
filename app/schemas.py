from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, Field


# ==========================================================================
# Provider Schemas
# ==========================================================================


class ProviderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64)
    display_name: str = Field(min_length=1, max_length=128)
    provider_type: str = Field(pattern="^(cli|api)$")
    base_url: str | None = Field(default=None, max_length=512)
    api_key: str | None = Field(default=None, max_length=512)
    config: dict[str, Any] = Field(default_factory=dict)
    description: str | None = Field(default=None)
    is_enabled: bool = True


class ProviderUpdate(BaseModel):
    display_name: str | None = Field(default=None, max_length=128)
    provider_type: str | None = Field(default=None, pattern="^(cli|api)$")
    base_url: str | None = Field(default=None, max_length=512)
    api_key: str | None = Field(default=None, max_length=512)
    config: dict[str, Any] | None = Field(default_factory=dict)
    description: str | None = Field(default=None)
    is_enabled: bool | None = None


class ProviderOut(BaseModel):
    id: int
    name: str
    display_name: str
    provider_type: str
    base_url: str | None
    api_key: str | None = None
    masked_api_key: str | None = None
    has_api_key: bool = False
    config: dict[str, Any]
    description: str | None
    is_enabled: bool
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ProvidersListResponse(BaseModel):
    items: list[ProviderOut]


# ==========================================================================
# Model Schemas
# ==========================================================================


class ModelCreate(BaseModel):
    provider_id: int
    model_key: str = Field(min_length=1, max_length=128)
    display_name: str = Field(min_length=1, max_length=128)
    upstream_model: str = Field(min_length=1, max_length=128)
    default_params: dict[str, Any] = Field(default_factory=dict)
    description: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    is_active: bool = True


class ModelUpdate(BaseModel):
    provider_id: int | None = None
    display_name: str | None = Field(default=None, max_length=128)
    upstream_model: str | None = Field(default=None, max_length=128)
    default_params: dict[str, Any] | None = Field(default_factory=dict)
    description: str | None = Field(default=None)
    notes: str | None = Field(default=None)
    is_active: bool | None = None
    health_status: str | None = Field(
        default=None, pattern="^(unknown|healthy|unhealthy)$"
    )


class ProviderInfo(BaseModel):
    id: int
    name: str
    display_name: str


class ModelOut(BaseModel):
    id: int
    model_key: str
    display_name: str
    upstream_model: str
    default_params: dict[str, Any]
    description: str | None
    notes: str | None
    is_active: bool
    health_status: str
    last_health_check: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    provider: ProviderInfo | None = None


class ModelsListResponse(BaseModel):
    items: list[dict[str, Any]]


# ==========================================================================
# Route Rules Schemas
# ==========================================================================


class ModelRouteUpsert(BaseModel):
    model_key: str = Field(min_length=1, max_length=128)
    is_enabled: bool = True
    priority: int = Field(default=0, ge=0)
    description: str | None = Field(default=None, max_length=255)


class ModelRoutesUpsertRequest(BaseModel):
    rules: list[ModelRouteUpsert]


class ModelInfo(BaseModel):
    id: int
    display_name: str
    upstream_model: str
    is_active: bool


class RouteProviderInfo(BaseModel):
    id: int
    name: str
    provider_type: str


class ModelRouteOut(BaseModel):
    model_key: str
    is_enabled: bool
    priority: int
    description: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    model: ModelInfo | None = None
    provider: RouteProviderInfo | None = None


class ModelRoutesListResponse(BaseModel):
    items: list[dict[str, Any]]


# ==========================================================================
# Compatibility Schemas
# ==========================================================================


class RouteRuleUpsert(BaseModel):
    model_name: str = Field(min_length=1, max_length=128)
    primary_provider: str = Field(min_length=1, max_length=64)
    fallback_provider: str | None = Field(
        default=None,
        max_length=64,
        description="兼容字段；提交时保持为空，路由引擎只使用 primary_provider。",
    )
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


# ==========================================================================
# Query Schemas
# ==========================================================================


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
