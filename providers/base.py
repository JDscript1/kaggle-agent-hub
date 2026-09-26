from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


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
