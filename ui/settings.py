from __future__ import annotations

from core.config import CONFIG
from core.session import clear_provider_secret, provider_setting, save_provider_setting
from providers.registry import preset


def summary() -> str:
    return f"Workspace: {CONFIG.workspace}\\nPublic share default: {CONFIG.share}"


def load_provider_setting(provider: str, state: dict) -> tuple[str, str, str]:
    current = provider_setting(state, provider)
    p = preset(provider)
    hint = "API key stored in this session." if current["api_key"] else f"No session key. Environment/Kaggle Secret: `{p.env_key}`"
    return current["model"] or p.default_model, current["base_url"] or p.default_base_url, hint


def save_api_settings(state: dict, provider: str, model: str, base_url: str, api_key: str) -> tuple[dict, str, str]:
    updated = save_provider_setting(state, provider, model=model, base_url=base_url, api_key=api_key)
    return updated, "Provider settings saved in memory for this session.", ""


def clear_api_settings(state: dict, provider: str) -> tuple[dict, str, str]:
    updated = clear_provider_secret(state, provider)
    return updated, "Session API key cleared. Environment/Kaggle Secret fallback remains available.", ""
