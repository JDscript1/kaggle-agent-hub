from __future__ import annotations

import httpx

from core.config import CONFIG
from providers.base import BaseProvider, ProviderConfig, ProviderError


class AnthropicProvider(BaseProvider):
    def generate(self, messages: list[dict[str, str]], config: ProviderConfig) -> str:
        if not config.api_key:
            raise ProviderError("Missing Anthropic API key.")
        base = (config.base_url or "https://api.anthropic.com").rstrip("/")
        system_parts = [m["content"] for m in messages if m.get("role") in {"system", "developer"}]
        conversation = [m for m in messages if m.get("role") in {"user", "assistant"}]
        payload = {
            "model": config.model,
            "max_tokens": config.max_tokens,
            "temperature": config.temperature,
            "messages": [{"role": m["role"], "content": m["content"]} for m in conversation],
        }
        if system_parts:
            payload["system"] = "\n\n".join(system_parts)
        headers = {
            "x-api-key": config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        try:
            with httpx.Client(timeout=CONFIG.request_timeout) as client:
                response = client.post(base + "/v1/messages", headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Anthropic network error: {exc}") from exc
        if response.is_error:
            raise ProviderError(f"Anthropic returned HTTP {response.status_code}: {response.text[:2000]}")
        data = response.json()
        texts = [p.get("text", "") for p in data.get("content", []) if isinstance(p, dict) and p.get("type") == "text"]
        return "".join(texts) or "[Anthropic returned no text output]"
