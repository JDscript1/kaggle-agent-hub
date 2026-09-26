from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

import psutil

from core.config import CONFIG


def _cmd(command: list[str]) -> str:
    try:
        return subprocess.check_output(command, text=True, stderr=subprocess.STDOUT, timeout=6).strip()
    except Exception:
        return "not available"


def collect() -> str:
    vm = psutil.virtual_memory()
    disk = shutil.disk_usage(CONFIG.workspace)
    gpu = _cmd(["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader"])
    rows = [
        f"Python: {sys.version.split()[0]}",
        f"OS: {platform.platform()}",
        f"CPU: {platform.processor() or platform.machine()}",
        f"RAM: {vm.total / 2**30:.1f} GiB total / {vm.available / 2**30:.1f} GiB available",
        f"Disk: {disk.total / 2**30:.1f} GiB total / {disk.free / 2**30:.1f} GiB free",
        f"Workspace: {CONFIG.workspace}",
        f"Kaggle detected: {Path('/kaggle/working').exists()}",
        f"GPU: {gpu}",
        f"codex: {shutil.which('codex') or 'not installed'}",
        f"claude: {shutil.which('claude') or 'not installed'}",
        f"gemini: {shutil.which('gemini') or 'not installed'}",
        f"kimi: {shutil.which('kimi') or 'not installed'}",
        f"Node: {_cmd(['node', '--version'])}",
    ]
    return "\n".join(rows)
