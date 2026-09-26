"""Controlled terminal execution for coding-agent tool calls."""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

from core.secrets import mask_secret
from core.workspace import WorkspaceError, root, safe_path


class TerminalError(RuntimeError):
    pass


# These checks are intentionally conservative.  A terminal is still powerful,
# so the UI/agent must make destructive operations explicit in a later phase.
_BLOCKED_COMMANDS = (
    re.compile(r"\brm\s+(?:-[^\s]*r[^\s]*\s+)?(?:-[^\s]*f[^\s]*\s+)?/(?:\s|$)", re.I),
    re.compile(r"\b(?:mkfs(?:\.[\w-]+)?|fdisk|parted)\b", re.I),
    re.compile(r"\bdd\s+[^\n]*\bif=", re.I),
    re.compile(r"\b(?:shutdown|reboot|poweroff|halt)\b", re.I),
    re.compile(r":\(\)\s*\{", re.I),
    re.compile(r"\bgit\s+reset\s+--hard\b", re.I),
    re.compile(r"\bgit\s+clean\s+-[^\n]*f", re.I),
)


def _workspace_cwd(raw: Any) -> tuple[str, Path]:
    if raw is None:
        return ".", root()
    if not isinstance(raw, str) or not raw.strip():
        raise TerminalError("cwd must be a non-empty workspace-relative path.")
    try:
        path = safe_path(raw.strip())
    except WorkspaceError as exc:
        raise TerminalError(str(exc)) from exc
    if not path.is_dir():
        raise TerminalError("cwd must be an existing directory inside the workspace.")
    return raw.strip(), path


def _mask_output(text: str, environment: dict[str, str]) -> str:
    masked = text
    secret_markers = ("KEY", "TOKEN", "SECRET", "PASSWORD", "CREDENTIAL")
    for name, value in environment.items():
        if any(marker in name.upper() for marker in secret_markers) and len(value) >= 8:
            masked = masked.replace(value, mask_secret(value))
    return masked


def execute_terminal(
    command: str,
    *,
    cwd: str | None = None,
    timeout: int = 120,
    max_output: int = 120_000,
) -> dict[str, Any]:
    if not isinstance(command, str) or not command.strip():
        raise TerminalError("command must be a non-empty string.")
    if len(command) > 4_000:
        raise TerminalError("command exceeds the 4,000 character limit.")
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 3_600:
        raise TerminalError("timeout must be an integer between 1 and 3600 seconds.")
    if not isinstance(max_output, int) or isinstance(max_output, bool) or not 1 <= max_output <= 500_000:
        raise TerminalError("max_output must be an integer between 1 and 500000 bytes.")
    for pattern in _BLOCKED_COMMANDS:
        if pattern.search(command):
            raise TerminalError("Command blocked by the safety policy.")

    cwd_label, workdir = _workspace_cwd(cwd)
    environment = dict(os.environ)
    try:
        process = subprocess.run(
            command,
            cwd=workdir,
            env=environment,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        stdout = _mask_output(exc.stdout or "", environment)
        stderr = _mask_output(exc.stderr or "", environment)
        combined = (stdout + ("\n" if stdout and stderr else "") + stderr)[-max_output:]
        return {"command": command, "cwd": cwd_label, "stdout": stdout[-max_output:], "stderr": stderr[-max_output:], "output": combined, "exit_code": None, "timed_out": True}

    stdout = _mask_output(process.stdout or "", environment)
    stderr = _mask_output(process.stderr or "", environment)
    combined = (stdout + ("\n" if stdout and stderr else "") + stderr)[-max_output:]
    return {
        "command": command,
        "cwd": cwd_label,
        "stdout": stdout[-max_output:],
        "stderr": stderr[-max_output:],
        "output": combined,
        "exit_code": process.returncode,
        "timed_out": False,
    }
