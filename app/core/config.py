from functools import lru_cache

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    supabase_url: str = Field(validation_alias=AliasChoices("SUPABASE_URL"))
    supabase_key: str = Field(validation_alias=AliasChoices("SUPABASE_KEY", "SUPABASE_SERVICE_ROLE_KEY"))
    hf_api_key: str = Field(validation_alias=AliasChoices("HF_API_KEY", "EMBEDDING_API_KEY"))
    llm_api_key: str = Field(validation_alias=AliasChoices("GROK_API_KEY", "LLM_API_KEY"))
    llm_base_url: str = Field(default="https://api.x.ai/v1", validation_alias=AliasChoices("LLM_BASE_URL", "GROK_BASE_URL"))
    llama_cloud_api_key: str = Field(default="", validation_alias=AliasChoices("LLAMA_CLOUD_API_KEY"))
    llama_parse_result_type: str = Field(default="markdown", validation_alias=AliasChoices("LLAMA_PARSE_RESULT_TYPE"))

    imap_host: str = Field(default="", validation_alias=AliasChoices("IMAP_HOST"))
    imap_port: int = Field(default=993, validation_alias=AliasChoices("IMAP_PORT"))
    imap_user: str = Field(default="", validation_alias=AliasChoices("IMAP_USER", "IMAP_USERNAME"))
    imap_password: str = Field(default="", validation_alias=AliasChoices("IMAP_PASSWORD"))

    smtp_host: str = Field(default="", validation_alias=AliasChoices("SMTP_HOST"))
    smtp_port: int = Field(default=587, validation_alias=AliasChoices("SMTP_PORT"))
    smtp_user: str = Field(default="", validation_alias=AliasChoices("SMTP_USER"))
    smtp_password: str = Field(default="", validation_alias=AliasChoices("SMTP_PASSWORD"))
    smtp_from: str = Field(default="", validation_alias=AliasChoices("SMTP_FROM", "RESEND_FROM_EMAIL"))

    app_env: str = Field(default="development", validation_alias=AliasChoices("APP_ENV"))
    log_level: str = Field(default="INFO", validation_alias=AliasChoices("LOG_LEVEL"))
    api_timeout_seconds: int = Field(default=30, validation_alias=AliasChoices("API_TIMEOUT_SECONDS"))
    embedding_model_name: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        validation_alias=AliasChoices("EMBEDDING_MODEL_NAME", "EMBEDDING_MODEL"),
    )
    llm_model_name: str = Field(default="grok-2-latest", validation_alias=AliasChoices("GROK_MODEL_NAME", "LLM_MODEL"))
    max_upload_mb: int = Field(default=25, validation_alias=AliasChoices("MAX_UPLOAD_MB", "MAX_UPLOAD_SIZE_MB"))
    email_poll_batch_size: int = Field(default=25, validation_alias=AliasChoices("EMAIL_POLL_BATCH_SIZE"))
    email_poll_interval_seconds: int = Field(default=60, validation_alias=AliasChoices("EMAIL_POLL_INTERVAL_SECONDS"))
    email_automation_enabled: bool = Field(default=False, validation_alias=AliasChoices("EMAIL_AUTOMATION_ENABLED"))
    api_key: str = Field(default="", validation_alias=AliasChoices("API_KEY"))
    rate_limit_per_minute: int = Field(default=120, validation_alias=AliasChoices("RATE_LIMIT_PER_MINUTE"))
    grok_max_retries: int = Field(default=3, validation_alias=AliasChoices("GROK_MAX_RETRIES"))
    external_call_timeout_seconds: int = Field(default=30, validation_alias=AliasChoices("EXTERNAL_CALL_TIMEOUT_SECONDS"))
    cors_allowed_origins: str = Field(default="*", validation_alias=AliasChoices("CORS_ALLOWED_ORIGINS", "CORS_ORIGINS"))
    trusted_hosts: str = Field(default="*", validation_alias=AliasChoices("TRUSTED_HOSTS"))
    max_request_mb: int = Field(default=30, validation_alias=AliasChoices("MAX_REQUEST_MB"))
    api_keys: str = Field(default="", validation_alias=AliasChoices("API_KEYS"))
    circuit_failure_threshold: int = Field(default=5, validation_alias=AliasChoices("CIRCUIT_FAILURE_THRESHOLD"))
    circuit_recovery_seconds: int = Field(default=30, validation_alias=AliasChoices("CIRCUIT_RECOVERY_SECONDS"))
    llm_parser_enabled: bool = Field(default=True, validation_alias=AliasChoices("LLM_PARSER_ENABLED"))

    @property
    def cors_origins_list(self) -> list[str]:
        values = [item.strip() for item in self.cors_allowed_origins.split(",") if item.strip()]
        return values or ["*"]

    @property
    def trusted_hosts_list(self) -> list[str]:
        values = [item.strip() for item in self.trusted_hosts.split(",") if item.strip()]
        return values or ["*"]

    @property
    def api_key_scope_map(self) -> dict[str, set[str]]:
        parsed: dict[str, set[str]] = {}
        if self.api_key:
            parsed[self.api_key] = {"*"}

        for item in [part.strip() for part in self.api_keys.split(",") if part.strip()]:
            if ":" not in item:
                continue
            key, scopes_raw = item.split(":", maxsplit=1)
            scopes = {scope.strip() for scope in scopes_raw.split("|") if scope.strip()}
            if key.strip() and scopes:
                parsed[key.strip()] = scopes

        return parsed


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
