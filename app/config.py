from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    app_name: str = "model-gateway"
    app_env: str = "dev"
    log_level: str = "INFO"

    host: str = "0.0.0.0"
    port: int = 8080

    gateway_client_token: str = Field(default="", alias="GATEWAY_CLIENT_TOKEN")
    gateway_admin_token: str = Field(default="", alias="GATEWAY_ADMIN_TOKEN")

    pg_host: str = Field(
        default="pg", validation_alias=AliasChoices("PG_HOST", "MYSQL_HOST")
    )
    pg_port: int = Field(
        default=5432, validation_alias=AliasChoices("PG_PORT", "MYSQL_PORT")
    )
    pg_user: str = Field(
        default="model_gateway_user",
        validation_alias=AliasChoices("PG_USER", "MYSQL_USER"),
    )
    pg_password: str = Field(
        default="", validation_alias=AliasChoices("PG_PASSWORD", "MYSQL_PASSWORD")
    )
    pg_database: str = Field(
        default="model_gateway",
        validation_alias=AliasChoices("PG_DATABASE", "MYSQL_DATABASE"),
    )
    pg_connect_timeout: int = Field(
        default=5,
        validation_alias=AliasChoices("PG_CONNECT_TIMEOUT", "MYSQL_CONNECT_TIMEOUT"),
    )

    openai_compatible_timeout_sec: int = Field(
        default=120,
        validation_alias=AliasChoices(
            "OPENAI_COMPATIBLE_TIMEOUT_SEC", "QWEN_TIMEOUT_SEC"
        ),
    )
    kimi_timeout_sec: int = Field(default=120, alias="KIMI_TIMEOUT_SEC")
    kimi_cli_cmd: str = Field(default="kimi", alias="KIMI_CLI_CMD")

    default_page_limit: int = 100
    max_page_limit: int = 500

    api_key_encryption_key: str = Field(default="", alias="API_KEY_ENCRYPTION_KEY")
    encrypt_api_keys: bool = Field(default=False, alias="ENCRYPT_API_KEYS")


@lru_cache
def get_settings() -> Settings:
    return Settings()
