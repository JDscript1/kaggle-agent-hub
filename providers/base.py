from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from core.agent import ModelTurn


@dataclass
class ProviderConfig:
    name: str
    model: str
    api_key: str = ""
    base_url: str = ""
    temperature: float = 0.2
    max_tokens: int = 4096
    extra_headers: dict[str, str] = field(default_factory=dict)


class ProviderError(RuntimeError):
    pass


class BaseProvider(ABC):
    @abstractmethod
    def generate(self, messages: list[dict[str, str]], config: ProviderConfig) -> str:
        raise NotImplementedError

    def supports_tools(self) -> bool:
        return False

    def generate_turn(
        self,
        messages: list[dict[str, Any]],
        config: ProviderConfig,
        tools: list[dict[str, Any]],
    ) -> ModelTurn:
        raise ProviderError(f"{config.name} does not support agent tool calling yet.")
