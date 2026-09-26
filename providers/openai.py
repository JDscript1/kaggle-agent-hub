from __future__ import annotations

import httpx

from core.config import CONFIG
from providers.base import BaseProvider, ProviderConfig, ProviderError


class OpenAIProvider(BaseProvider):
    """OpenAI Responses API adapter, suitable for current OpenAI text/reasoning models."""

    def generate(self, messages: list[dict[str, str]], config: ProviderConfig) -> str:
        if not config.api_key:
            raise ProviderError("Missing OpenAI API key.")
        base = (config.base_url or "https://api.openai.com/v1").rstrip("/")
        url = base + "/responses"
        headers = {"Authorization": f"Bearer {config.api_key}", "Content-Type": "application/json"}
        input_items = []
        for m in messages:
            role = m.get("role", "user")
            if role not in {"user", "assistant", "system", "developer"}:
                role = "user"
            input_items.append({"role": role, "content": m.get("content", "")})
        payload = {"model": config.model, "input": input_items, "max_output_tokens": config.max_tokens}
        try:
            with httpx.Client(timeout=CONFIG.request_timeout) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError(f"OpenAI network error: {exc}") from exc
        if response.is_error:
            raise ProviderError(f"OpenAI returned HTTP {response.status_code}: {response.text[:2000]}")
        data = response.json()
        if isinstance(data.get("output_text"), str) and data["output_text"]:
            return data["output_text"]
        texts: list[str] = []
        for item in data.get("output", []):
            for part in item.get("content", []) if isinstance(item, dict) else []:
                if isinstance(part, dict) and isinstance(part.get("text"), str):
                    texts.append(part["text"])
        if texts:
            return "".join(texts)
        raise ProviderError(f"OpenAI returned no text output: {str(data)[:2000]}")
