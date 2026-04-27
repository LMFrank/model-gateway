from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

ProviderType = Literal["api", "cli"]


class ProviderRuntimeConfigError(ValueError):
    pass


class ApiProviderRuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timeout_sec: int | None = Field(default=None, ge=1, le=3600)
    connect_retries: int | None = Field(default=None, ge=0, le=10)
    retry_backoff_sec: float | None = Field(default=None, ge=0, le=60)
    chat_endpoint: str | None = Field(default=None, min_length=1, max_length=128)
    upstream_model: str | None = Field(default=None, min_length=1, max_length=128)

    @field_validator("chat_endpoint")
    @classmethod
    def _validate_chat_endpoint(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.startswith("/"):
            raise ValueError("chat_endpoint must start with '/'")
        return value


class CliProviderRuntimeConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timeout_sec: int | None = Field(default=None, ge=1, le=3600)
    command: str | None = Field(default=None, min_length=1, max_length=255)
    args: list[str] | None = None
    extra_args: list[str] | None = None
    model_arg: str | None = Field(default=None, min_length=1, max_length=64)
    prompt_arg: str | None = Field(default=None, min_length=1, max_length=64)
    stream_arg: str | None = Field(default=None, min_length=1, max_length=64)
    stdin_prompt_arg: str | None = Field(default=None, min_length=1, max_length=64)
    response_file: str | None = Field(default=None, min_length=1, max_length=512)
    upstream_model: str | None = Field(default=None, min_length=1, max_length=128)
    use_stdin_prompt: bool | None = None
    force_stdin_prompt: bool | None = None


RUNTIME_CONFIG_MODELS: dict[ProviderType, type[BaseModel]] = {
    "api": ApiProviderRuntimeConfig,
    "cli": CliProviderRuntimeConfig,
}

RUNTIME_CONFIG_FIELDS: dict[ProviderType, set[str]] = {
    provider_type: set(model.model_fields.keys())
    for provider_type, model in RUNTIME_CONFIG_MODELS.items()
}


def _normalize_config_object(value: Any) -> dict[str, Any]:
    if not value:
        return {}
    if not isinstance(value, dict):
        raise ProviderRuntimeConfigError("provider runtime config must be an object")
    return value.copy()


def validate_runtime_config(
    provider_type: ProviderType, runtime_config: dict[str, Any] | None
) -> dict[str, Any]:
    model = RUNTIME_CONFIG_MODELS[provider_type]
    normalized = _normalize_config_object(runtime_config)
    try:
        parsed = model.model_validate(normalized)
    except ValidationError as exc:
        raise ProviderRuntimeConfigError(str(exc)) from exc
    return parsed.model_dump(exclude_none=True)


def split_runtime_config(
    provider_type: ProviderType, config: dict[str, Any] | None
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized = _normalize_config_object(config)
    supported_fields = RUNTIME_CONFIG_FIELDS[provider_type]
    runtime_config = {
        key: value for key, value in normalized.items() if key in supported_fields
    }
    runtime_config_extras = {
        key: value for key, value in normalized.items() if key not in supported_fields
    }
    return validate_runtime_config(provider_type, runtime_config), runtime_config_extras


def merge_runtime_config(
    provider_type: ProviderType,
    *,
    config: dict[str, Any] | None = None,
    runtime_config: dict[str, Any] | None = None,
    runtime_config_extras: dict[str, Any] | None = None,
) -> dict[str, Any]:
    base_runtime_config, base_extras = split_runtime_config(provider_type, config)
    runtime_override = _normalize_config_object(runtime_config)
    extras_override = _normalize_config_object(runtime_config_extras)
    supported_fields = RUNTIME_CONFIG_FIELDS[provider_type]

    merged_runtime_config = {
        **base_runtime_config,
        **{key: value for key, value in runtime_override.items() if key in supported_fields},
    }
    merged_extras = {
        **base_extras,
        **{key: value for key, value in extras_override.items() if key not in supported_fields},
    }
    validated_runtime_config = validate_runtime_config(
        provider_type, merged_runtime_config
    )
    return {**merged_extras, **validated_runtime_config}
