from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from core.config import CONFIG
from core.logging_store import LOGS


@dataclass(frozen=True)
class CliAgent:
    name: str
    executable: str
    argv_prefix: tuple[str, ...]


CLI_AGENTS: dict[str, CliAgent] = {
    "Codex CLI": CliAgent("Codex CLI", "codex", ("exec", "--skip-git-repo-check")),
    "Claude Code": CliAgent("Claude Code", "claude", ("-p",)),
    "Gemini CLI": CliAgent("Gemini CLI", "gemini", ("-p",)),
    # Kimi CLI flags differ between distributions; the UI exposes a custom command for it.
}


def availability() -> dict[str, bool]:
    return {name: bool(shutil.which(agent.executable)) for name, agent in CLI_AGENTS.items()}


def run_agent(name: str, prompt: str, timeout: int = 900, custom_command: str = "") -> str:
    if not prompt.strip():
        return "Prompt is empty."
    cwd = CONFIG.workspace.resolve()
    cwd.mkdir(parents=True, exist_ok=True)

    if name == "Custom CLI":
        if not custom_command.strip():
            return "Custom command is empty."
        argv = shlex.split(custom_command) + [prompt]
    else:
        agent = CLI_AGENTS.get(name)
        if not agent:
            return f"Unknown CLI agent: {name}"
        exe = shutil.which(agent.executable)
        if not exe:
            return f"{agent.name} is not installed or not on PATH."
        argv = [exe, *agent.argv_prefix, prompt]

    LOGS.add(f"Launching {name} in {cwd}")
    try:
        proc = subprocess.run(
            argv,
            cwd=cwd,
            env=os.environ.copy(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
            check=False,
        )
        output = proc.stdout or ""
        LOGS.add(f"{name} finished with exit code {proc.returncode}")
        return output[-120_000:]
    except subprocess.TimeoutExpired as exc:
        LOGS.add(f"{name} timed out after {timeout}s", "ERROR")
        partial = exc.stdout or ""
        return f"Timed out after {timeout}s.\n\n{partial}"
    except Exception as exc:
        LOGS.add(f"CLI error: {exc}", "ERROR")
        return f"CLI error: {exc}"
