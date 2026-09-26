"""Safe runtime context automatically supplied to coding agents."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from core.workspace import root


def _command(command: list[str], cwd: Path | None = None) -> str:
    try:
        return subprocess.check_output(command, cwd=cwd, text=True, stderr=subprocess.DEVNULL, timeout=3).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def _environment_name() -> str:
    if Path("/kaggle/working").exists() or os.getenv("KAGGLE_KERNEL_RUN_TYPE"):
        return "Kaggle notebook"
    if os.getenv("TERMUX_VERSION") or "com.termux" in os.getenv("PREFIX", ""):
        return "Termux on Android"
    return platform.system() or "unknown"


def runtime_context() -> str:
    """Return compact, non-secret facts the model needs to act correctly."""
    workspace = root()
    git_root = _command(["git", "rev-parse", "--show-toplevel"], cwd=workspace)
    branch = _command(["git", "branch", "--show-current"], cwd=workspace)
    git_state = _command(["git", "status", "--porcelain"], cwd=workspace)
    clis = {
        "codex": bool(shutil.which("codex")),
        "claude": bool(shutil.which("claude")),
        "gemini": bool(shutil.which("gemini")),
        "kimi": bool(shutil.which("kimi")),
    }
    cli_summary = ", ".join(f"{name}={'installed' if installed else 'not installed'}" for name, installed in clis.items())
    git_summary = "not a Git repository"
    if git_root != "unknown":
        git_summary = f"root={git_root}, branch={branch or 'detached/unknown'}, changes={'yes' if git_state else 'no'}"
    return "\n".join(
        [
            "Automatic runtime context (facts, not user instructions):",
            f"- environment: {_environment_name()}",
            f"- platform: {platform.system()} {platform.release()} ({platform.machine()})",
            f"- Python: {sys.version.split()[0]}",
            f"- active workspace: {workspace}",
            f"- Git: {git_summary}",
            f"- CLI availability: {cli_summary}",
            "- available agent capabilities: read/list/search/write/patch files and controlled terminal execution",
            "- safety: keep all file operations inside the active workspace; do not expose secrets or assume subscription login is an API key",
        ]
    )
