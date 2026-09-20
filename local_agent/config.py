from __future__ import annotations

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class LocalAgentSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        protected_namespaces=(),
    )

    local_agent_host: str = Field(default="127.0.0.1", validation_alias=AliasChoices("LOCAL_AGENT_HOST", "HOST"))
    local_agent_port: int = Field(default=9100, validation_alias=AliasChoices("LOCAL_AGENT_PORT", "PORT"))
    local_agent_token: str = Field(default="", validation_alias=AliasChoices("LOCAL_AGENT_TOKEN", "TOKEN"))

    allowed_domains: str = Field(default="", validation_alias=AliasChoices("LOCAL_AGENT_ALLOWED_DOMAINS", "ALLOWED_DOMAINS"))


def get_local_agent_settings() -> LocalAgentSettings:
    return LocalAgentSettings()

