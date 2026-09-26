from __future__ import annotations

from providers.registry import names, preset


def initial_provider() -> str:
    return names()[0]


def provider_defaults(name: str):
    p = preset(name)
    return p.default_model, p.default_base_url, p.env_key, p.note or f"Environment/Kaggle secret: {p.env_key}"
