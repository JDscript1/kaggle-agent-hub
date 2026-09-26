from __future__ import annotations

import json

import httpx

from core.config import CONFIG
from providers.base import BaseProvider, ProviderConfig, ProviderError


class OpenAICompatibleProvider(BaseProvider):
    """Generic /v1/chat/completions adapter used by many providers."""

    def generate(self, messages: list[dict[str, str]], config: ProviderConfig) -> str:
        if not config.api_key:
            raise ProviderError(f"Missing API key for {config.name}.")
        if not config.base_url:
            raise ProviderError(f"Missing base URL for {config.name}.")

        url = config.base_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
            **config.extra_headers,
        }
        payload = {
            "model": config.model,
            "messages": messages,
            "temperature": config.temperature,
            "max_tokens": config.max_tokens,
        }
        try:
            with httpx.Client(timeout=CONFIG.request_timeout) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Network error calling {config.name}: {exc}") from exc

        if response.is_error:
            text = response.text[:2000]
            raise ProviderError(f"{config.name} returned HTTP {response.status_code}: {text}")

        try:
            data = response.json()
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, str):
                return content
            # Some compatible APIs return structured content arrays.
            if isinstance(content, list):
                parts = [p.get("text", "") for p in content if isinstance(p, dict)]
                return "".join(parts)
            return json.dumps(content, ensure_ascii=False)
        except Exception as exc:
            raise ProviderError(f"Unexpected response from {config.name}: {response.text[:2000]}") from exc
