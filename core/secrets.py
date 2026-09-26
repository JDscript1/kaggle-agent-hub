from __future__ import annotations

import os
from typing import Optional


def mask_secret(value: str | None) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "••••••••"
    return f"{value[:4]}…{value[-4:]}"


def from_environment(name: str) -> str:
    return os.getenv(name, "").strip()


def from_kaggle(name: str) -> str:
    """Read a Kaggle Secret if running inside Kaggle; otherwise return empty string."""
    try:
        from kaggle_secrets import UserSecretsClient  # type: ignore

        return (UserSecretsClient().get_secret(name) or "").strip()
    except Exception:
        return ""


def resolve_secret(explicit: str, env_name: str, kaggle_name: Optional[str] = None) -> str:
    """Resolve a secret without persisting it: UI value -> env -> Kaggle Secret."""
    if explicit and explicit.strip():
        return explicit.strip()
    env_value = from_environment(env_name)
    if env_value:
        return env_value
    return from_kaggle(kaggle_name or env_name)
