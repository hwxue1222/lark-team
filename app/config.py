from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL", "APP_LOG_LEVEL"))

    lark_app_id: str = Field(validation_alias=AliasChoices("LARK_APP_ID", "APP_ID"))
    lark_app_secret: str = Field(validation_alias=AliasChoices("LARK_APP_SECRET", "APP_SECRET"))
    lark_domain: str = Field(default="https://open.larksuite.com", validation_alias=AliasChoices("LARK_DOMAIN", "LARK_OPEN_DOMAIN"))

    kimi_api_key: str = Field(validation_alias=AliasChoices("KIMI_API_KEY", "MOONSHOT_API_KEY"))
    kimi_model: str = Field(validation_alias=AliasChoices("KIMI_MODEL", "MODEL_NAME"))
    kimi_base_url: str = Field(default="https://api.kimi.ai/coding/v1", validation_alias=AliasChoices("KIMI_BASE_URL", "MOONSHOT_BASE_URL"))

    bot_title: str = Field(default="BBY中控", validation_alias=AliasChoices("BOT_TITLE", "LARK_BOT_TITLE"))

    http_host: str = Field(default="0.0.0.0", validation_alias=AliasChoices("HTTP_HOST", "HOST"))
    http_port: int = Field(default=8000, validation_alias=AliasChoices("HTTP_PORT", "PORT"))

    local_agent_enabled: bool = Field(default=False, validation_alias=AliasChoices("LOCAL_AGENT_ENABLED", "BBY_LOCAL_AGENT_ENABLED"))
    local_agent_url: str = Field(default="http://127.0.0.1:9100", validation_alias=AliasChoices("LOCAL_AGENT_URL", "BBY_LOCAL_AGENT_URL"))
    local_agent_token: str = Field(default="", validation_alias=AliasChoices("LOCAL_AGENT_TOKEN", "BBY_LOCAL_AGENT_TOKEN"))
    local_agent_operator_ids: str = Field(default="", validation_alias=AliasChoices("LOCAL_AGENT_OPERATOR_IDS", "BBY_LOCAL_AGENT_OPERATOR_IDS"))

    accountant_enabled: bool = Field(default=False, validation_alias=AliasChoices("ACCOUNTANT_ENABLED", "BBY_ACCOUNTANT_ENABLED"))
    bby_accounting_base_url: str = Field(default="https://bbyaccounting.com", validation_alias=AliasChoices("BBY_ACCOUNTING_BASE_URL", "BBYACCOUNTING_BASE_URL"))
    bby_accounting_email: str = Field(default="", validation_alias=AliasChoices("BBY_ACCOUNTING_EMAIL", "BBYACCOUNTING_EMAIL"))
    bby_accounting_password: str = Field(default="", validation_alias=AliasChoices("BBY_ACCOUNTING_PASSWORD", "BBYACCOUNTING_PASSWORD"))
    bby_accounting_org_id: str = Field(default="", validation_alias=AliasChoices("BBY_ACCOUNTING_ORG_ID", "BBYACCOUNTING_ORG_ID"))
    accountant_operator_ids: str = Field(default="", validation_alias=AliasChoices("ACCOUNTANT_OPERATOR_IDS", "BBY_ACCOUNTANT_OPERATOR_IDS"))
    accountant_default_currency: str = Field(default="SGD", validation_alias=AliasChoices("ACCOUNTANT_DEFAULT_CURRENCY", "BBY_ACCOUNTANT_DEFAULT_CURRENCY"))
    accountant_default_fx_rate: float = Field(default=1.0, validation_alias=AliasChoices("ACCOUNTANT_DEFAULT_FX_RATE", "BBY_ACCOUNTANT_DEFAULT_FX_RATE"))


def get_settings() -> Settings:
    return Settings()
