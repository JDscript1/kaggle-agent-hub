from __future__ import annotations

from copy import deepcopy
from typing import Any


def new_session() -> dict[str, Any]:
    return {
        "provider_settings": {},
        "history": [],
        "system_prompt": "You are a helpful coding assistant. Be precise, concise, and safe with file operations.",
    }


def clone_session(state: dict[str, Any] | None) -> dict[str, Any]:
    return deepcopy(state or new_session())


def provider_setting(state: dict[str, Any] | None, provider: str) -> dict[str, str]:
    """Return non-persistent in-memory settings for one API provider."""
    current = (state or {}).get("provider_settings", {}).get(provider, {})
    return {
        "api_key": str(current.get("api_key", "")),
        "model": str(current.get("model", "")),
        "base_url": str(current.get("base_url", "")),
    }


def save_provider_setting(
    state: dict[str, Any] | None,
    provider: str,
    *,
    api_key: str = "",
    model: str = "",
    base_url: str = "",
) -> dict[str, Any]:
    updated = clone_session(state)
    settings = updated.setdefault("provider_settings", {})
    existing = settings.setdefault(provider, {})
    if api_key.strip():
        existing["api_key"] = api_key.strip()
    if model.strip():
        existing["model"] = model.strip()
    if base_url.strip():
        existing["base_url"] = base_url.strip()
    return updated


def clear_provider_secret(state: dict[str, Any] | None, provider: str) -> dict[str, Any]:
    updated = clone_session(state)
    settings = updated.setdefault("provider_settings", {})
    existing = settings.get(provider)
    if existing:
        existing.pop("api_key", None)
        if not existing:
            settings.pop(provider, None)
    return updated
