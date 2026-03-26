from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "model-gateway"
    app_env: str = "dev"
    log_level: str = "INFO"

    host: str = "0.0.0.0"
    port: int = 8080

    gateway_client_token: str = Field(default="", alias="GATEWAY_CLIENT_TOKEN")
    gateway_admin_token: str = Field(default="", alias="GATEWAY_ADMIN_TOKEN")

    mysql_host: str = Field(default="mysql", alias="MYSQL_HOST")
    mysql_port: int = Field(default=3306, alias="MYSQL_PORT")
    mysql_user: str = Field(default="model_gateway_user", alias="MYSQL_USER")
    mysql_password: str = Field(default="", alias="MYSQL_PASSWORD")
    mysql_database: str = Field(default="model_gateway", alias="MYSQL_DATABASE")
    mysql_charset: str = Field(default="utf8mb4", alias="MYSQL_CHARSET")
    mysql_connect_timeout: int = Field(default=5, alias="MYSQL_CONNECT_TIMEOUT")

    qwen_timeout_sec: int = Field(default=120, alias="QWEN_TIMEOUT_SEC")
    kimi_timeout_sec: int = Field(default=120, alias="KIMI_TIMEOUT_SEC")
    kimi_cli_cmd: str = Field(default="kimi", alias="KIMI_CLI_CMD")

    default_page_limit: int = 100
    max_page_limit: int = 500


@lru_cache
def get_settings() -> Settings:
    return Settings()
