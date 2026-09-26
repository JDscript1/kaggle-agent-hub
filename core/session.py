from __future__ import annotations

from copy import deepcopy
from typing import Any


def new_session() -> dict[str, Any]:
    return {
        "provider_settings": {},
        "history": [],
        "system_prompt": "You are a helpful coding assistant. Be precise, concise, and safe with file operations.",
    }


def clone_session(state: dict[str, Any] | None) -> dict[str, Any]:
    return deepcopy(state or new_session())
