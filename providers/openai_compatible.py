from __future__ import annotations

import json
from typing import Any

import httpx

from core.config import CONFIG
from core.agent import ModelTurn, ToolCall
from providers.base import BaseProvider, ProviderConfig, ProviderError


class OpenAICompatibleProvider(BaseProvider):
    """Generic /v1/chat/completions adapter used by many providers."""

    def supports_tools(self) -> bool:
        return True

    def _request(self, messages: list[dict], config: ProviderConfig, tools: list[dict] | None = None) -> dict:
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
        if tools:
            payload["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": tool["name"],
                        "description": tool.get("description", ""),
                        "parameters": tool.get("input_schema", {"type": "object"}),
                    },
                }
                for tool in tools
            ]
            payload["tool_choice"] = "auto"
        try:
            with httpx.Client(timeout=CONFIG.request_timeout) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.HTTPError as exc:
            raise ProviderError(f"Network error calling {config.name}: {exc}") from exc

        if response.is_error:
            raise ProviderError(f"{config.name} returned HTTP {response.status_code}: {response.text[:2000]}")
        try:
            return response.json()
        except ValueError as exc:
            raise ProviderError(f"Unexpected non-JSON response from {config.name}.") from exc

    def generate(self, messages: list[dict[str, str]], config: ProviderConfig) -> str:
        data = self._request(messages, config)
        try:
            content = data["choices"][0]["message"]["content"]
            if isinstance(content, str):
                return content
            # Some compatible APIs return structured content arrays.
            if isinstance(content, list):
                parts = [p.get("text", "") for p in content if isinstance(p, dict)]
                return "".join(parts)
            return json.dumps(content, ensure_ascii=False)
        except Exception as exc:
            raise ProviderError(f"Unexpected response from {config.name}: {str(data)[:2000]}") from exc

    def generate_turn(
        self,
        messages: list[dict[str, Any]],
        config: ProviderConfig,
        tools: list[dict[str, Any]],
    ) -> ModelTurn:
        api_messages = []
        for message in messages:
            converted = dict(message)
            if message.get("role") == "assistant" and message.get("tool_calls"):
                converted["tool_calls"] = [
                    {
                        "id": call["id"],
                        "type": "function",
                        "function": {
                            "name": call["name"],
                            "arguments": json.dumps(call.get("arguments", {}), ensure_ascii=False),
                        },
                    }
                    for call in message["tool_calls"]
                ]
            api_messages.append(converted)
        data = self._request(api_messages, config, tools)
        try:
            message = data["choices"][0]["message"]
            calls = []
            for index, raw_call in enumerate(message.get("tool_calls", []) or []):
                function = raw_call.get("function", {})
                arguments = function.get("arguments", "{}")
                if isinstance(arguments, str):
                    arguments = json.loads(arguments)
                calls.append(ToolCall(str(raw_call.get("id", f"call-{index + 1}")), function["name"], arguments))
            content = message.get("content") or ""
            return ModelTurn(content=content, tool_calls=tuple(calls))
        except (KeyError, TypeError, ValueError) as exc:
            raise ProviderError(f"Unexpected tool-call response from {config.name}: {str(data)[:2000]}") from exc
