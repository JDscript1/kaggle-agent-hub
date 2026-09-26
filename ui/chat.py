from __future__ import annotations

from core.logging_store import LOGS
from core.secrets import resolve_secret
from core.session import clone_session, provider_setting
from core.workspace import context_snapshot
from providers.base import ProviderError
from providers.registry import adapter_for, make_config, preset


def _normalize_history(history) -> list[dict[str, str]]:
    out: list[dict[str, str]] = []
    for item in history or []:
        if isinstance(item, dict) and "role" in item and "content" in item:
            out.append({"role": str(item["role"]), "content": str(item["content"])})
        elif isinstance(item, (list, tuple)) and len(item) == 2:
            if item[0]:
                out.append({"role": "user", "content": str(item[0])})
            if item[1]:
                out.append({"role": "assistant", "content": str(item[1])})
    return out


def respond(
    message: str,
    history,
    session_state,
    provider_name: str,
    model: str,
    api_key: str,
    base_url: str,
    temperature: float,
    max_tokens: int,
    system_prompt: str,
    include_workspace: bool,
):
    state = clone_session(session_state)
    if not message.strip():
        return history, state, ""

    p = preset(provider_name)
    saved = provider_setting(state, provider_name)
    effective_model = model or saved["model"]
    effective_base_url = base_url or saved["base_url"]
    secret = resolve_secret(api_key or saved["api_key"], p.env_key)
    cfg = make_config(provider_name, effective_model, secret, effective_base_url, temperature, max_tokens)
    messages: list[dict[str, str]] = []
    if system_prompt.strip():
        messages.append({"role": "system", "content": system_prompt.strip()})
    if include_workspace:
        snapshot = context_snapshot()
        if snapshot:
            messages.append({
                "role": "system",
                "content": "Current workspace snapshot follows. Treat it as context only; do not assume a file was changed unless a CLI agent or the Files tab actually changes it.\n" + snapshot,
            })
    messages.extend(_normalize_history(history))
    messages.append({"role": "user", "content": message})

    try:
        LOGS.add(f"Chat request -> {provider_name} / {cfg.model}")
        answer = adapter_for(provider_name).generate(messages, cfg)
        LOGS.add(f"Chat response <- {provider_name} / {cfg.model}")
    except ProviderError as exc:
        detail = str(exc).replace(secret, "[REDACTED]") if secret else str(exc)
        answer = f"Provider error: {detail}"
        LOGS.add(detail, "ERROR")
    except Exception as exc:
        detail = str(exc).replace(secret, "[REDACTED]") if secret else str(exc)
        answer = f"Unexpected error: {detail}"
        LOGS.add(f"Unexpected chat error: {detail}", "ERROR")

    normalized = _normalize_history(history)
    normalized.append({"role": "user", "content": message})
    normalized.append({"role": "assistant", "content": answer})
    state["history"] = normalized
    return normalized, state, ""
