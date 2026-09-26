from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from providers.anthropic import AnthropicProvider
from providers.base import BaseProvider, ProviderConfig
from providers.gemini import GeminiProvider
from providers.openai import OpenAIProvider
from providers.openai_compatible import OpenAICompatibleProvider


@dataclass(frozen=True)
class ProviderPreset:
    name: str
    env_key: str
    default_base_url: str
    default_model: str
    adapter: str = "compatible"
    note: str = ""


PRESETS: dict[str, ProviderPreset] = {
    "OpenAI / Codex API": ProviderPreset("OpenAI / Codex API", "OPENAI_API_KEY", "https://api.openai.com/v1", "gpt-5.6", "openai", "Uses the OpenAI Responses API."),
    "Anthropic": ProviderPreset("Anthropic", "ANTHROPIC_API_KEY", "https://api.anthropic.com", "claude-sonnet-4-5", "anthropic"),
    "Google Gemini": ProviderPreset("Google Gemini", "GEMINI_API_KEY", "https://generativelanguage.googleapis.com/v1beta", "gemini-2.5-pro", "gemini"),
    "DeepSeek": ProviderPreset("DeepSeek", "DEEPSEEK_API_KEY", "https://api.deepseek.com", "deepseek-chat"),
    "Kimi / Moonshot": ProviderPreset("Kimi / Moonshot", "MOONSHOT_API_KEY", "https://api.moonshot.ai/v1", "kimi-k2"),
    "Qwen / DashScope": ProviderPreset("Qwen / DashScope", "DASHSCOPE_API_KEY", "https://dashscope.aliyuncs.com/compatible-mode/v1", "qwen-plus", note="Uses DashScope's OpenAI-compatible API endpoint."),
    "OpenRouter": ProviderPreset("OpenRouter", "OPENROUTER_API_KEY", "https://openrouter.ai/api/v1", "openai/gpt-5.1"),
    "Mistral": ProviderPreset("Mistral", "MISTRAL_API_KEY", "https://api.mistral.ai/v1", "mistral-large-latest"),
    "Groq": ProviderPreset("Groq", "GROQ_API_KEY", "https://api.groq.com/openai/v1", "llama-3.3-70b-versatile"),
    "Together": ProviderPreset("Together", "TOGETHER_API_KEY", "https://api.together.xyz/v1", "meta-llama/Llama-3.3-70B-Instruct-Turbo"),
    "Fireworks": ProviderPreset("Fireworks", "FIREWORKS_API_KEY", "https://api.fireworks.ai/inference/v1", "accounts/fireworks/models/llama-v3p3-70b-instruct"),
    "xAI": ProviderPreset("xAI", "XAI_API_KEY", "https://api.x.ai/v1", "grok-4-fast-reasoning"),
    "Custom OpenAI-compatible": ProviderPreset("Custom OpenAI-compatible", "CUSTOM_API_KEY", "", "", "compatible"),
}


def names() -> list[str]:
    return list(PRESETS)


def preset(name: str) -> ProviderPreset:
    return PRESETS[name]


def adapter_for(name: str) -> BaseProvider:
    kind = PRESETS[name].adapter
    if kind == "openai":
        return OpenAIProvider()
    if kind == "anthropic":
        return AnthropicProvider()
    if kind == "gemini":
        return GeminiProvider()
    return OpenAICompatibleProvider()


def agent_model(name: str, config: ProviderConfig):
    """Return an agent-loop callback for providers with native tool calling."""
    adapter = adapter_for(name)
    if not adapter.supports_tools():
        raise ValueError(f"{name} does not support agent tool calling yet.")
    return lambda messages, tools: adapter.generate_turn(messages, config, tools)


def make_config(name: str, model: str, api_key: str, base_url: str, temperature: float, max_tokens: int) -> ProviderConfig:
    p = preset(name)
    return ProviderConfig(
        name=name,
        model=(model or p.default_model).strip(),
        api_key=api_key.strip(),
        base_url=(base_url or p.default_base_url).strip(),
        temperature=float(temperature),
        max_tokens=int(max_tokens),
        extra_headers={"HTTP-Referer": "https://github.com/Specter128/kaggle-agent-hub", "X-Title": "Kaggle Agent Hub"} if name == "OpenRouter" else {},
    )
