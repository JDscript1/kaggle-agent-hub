from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_WORKSPACE = Path(
    os.getenv(
        "KAGGLE_AGENT_HUB_WORKSPACE",
        "/kaggle/working/agent-workspace" if Path("/kaggle/working").exists() else PROJECT_ROOT / "workspace",
    )
).expanduser()


@dataclass(frozen=True)
class AppConfig:
    workspace: Path = DEFAULT_WORKSPACE
    request_timeout: float = 120.0
    max_file_preview_bytes: int = 250_000
    max_workspace_context_bytes: int = 180_000
    host: str = "0.0.0.0"
    port: int = int(os.getenv("PORT", "7860"))
    share: bool = os.getenv("KAGGLE_AGENT_HUB_SHARE", "true").lower() in {"1", "true", "yes", "on"}


CONFIG = AppConfig()
CONFIG.workspace.mkdir(parents=True, exist_ok=True)
