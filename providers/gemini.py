from __future__ import annotations

import httpx

from core.config import CONFIG
from providers.base import BaseProvider, ProviderConfig, ProviderError


class GeminiProvider(BaseProvider):
    def generate(self, messages: list[dict[str, str]], config: ProviderConfig) -> str:
        if not config.api_key:
            raise ProviderError("Missing Gemini API key.")
        base = (config.base_url or "https://generativelanguage.googleapis.com/v1beta").rstrip("/")
        url = f"{base}/models/{config.model}:generateContent"
        system = "\n\n".join(m["content"] for m in messages if m.get("role") in {"system", "developer"})
        contents = []
        for m in messages:
            if m.get("role") not in {"user", "assistant"}:
                continue
            contents.append({
                "role": "model" if m["role"] == "assistant" else "user",
                "parts": [{"text": m["content"]}],
            })
        payload: dict = {
            "contents": contents,
            "generationConfig": {
                "temperature": config.temperature,
                "maxOutputTokens": config.max_tokens,
            },
        }
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        try:
            with httpx.Client(timeout=CONFIG.request_timeout) as client:
                response = client.post(url, params={"key": config.api_key}, json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Gemini network error: {exc}") from exc
        if response.is_error:
            raise ProviderError(f"Gemini returned HTTP {response.status_code}: {response.text[:2000]}")
        data = response.json()
        try:
            parts = data["candidates"][0]["content"]["parts"]
            return "".join(p.get("text", "") for p in parts if isinstance(p, dict))
        except Exception as exc:
            raise ProviderError(f"Gemini returned no text output: {str(data)[:2000]}") from exc
