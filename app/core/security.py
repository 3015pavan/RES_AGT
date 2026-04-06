from __future__ import annotations

from email.utils import parseaddr
from typing import Callable

from fastapi import Depends, Header

from app.core.config import Settings, get_settings
from app.core.errors import AppError


def validate_email_value(candidate: str, field_name: str) -> None:
    _, parsed = parseaddr(candidate)
    if not parsed or "@" not in parsed:
        raise AppError(code="INVALID_EMAIL", message=f"Invalid email for {field_name}", status_code=422)


def require_api_key(
    x_api_key: str | None = Header(default=None),
    settings: Settings = Depends(get_settings),
) -> str:
    key_map = settings.api_key_scope_map
    if not key_map:
        raise AppError(code="AUTH_CONFIG_ERROR", message="Server API key is not configured", status_code=500)
    if not x_api_key or x_api_key not in key_map:
        raise AppError(code="UNAUTHORIZED", message="Invalid API key", status_code=401)
    return x_api_key


def require_scopes(required_scopes: list[str]) -> Callable[[str, Settings], str]:
    def _dependency(
        api_key: str = Depends(require_api_key),
        settings: Settings = Depends(get_settings),
    ) -> str:
        key_scopes = settings.api_key_scope_map.get(api_key, set())
        if "*" in key_scopes:
            return api_key
        if not set(required_scopes).issubset(key_scopes):
            raise AppError(code="FORBIDDEN", message="Insufficient scope", status_code=403)
        return api_key

    return _dependency
