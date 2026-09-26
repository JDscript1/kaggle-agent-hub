from __future__ import annotations

import os
import shutil
import zipfile
from pathlib import Path
from typing import Iterable

from core.config import CONFIG


class WorkspaceError(RuntimeError):
    pass


def root() -> Path:
    CONFIG.workspace.mkdir(parents=True, exist_ok=True)
    return CONFIG.workspace.resolve()


def safe_path(relative: str | Path) -> Path:
    base = root()
    candidate = (base / relative).resolve()
    try:
        candidate.relative_to(base)
    except ValueError as exc:
        raise WorkspaceError("Path escapes the workspace.") from exc
    return candidate


def list_tree(max_entries: int = 500) -> str:
    base = root()
    rows: list[str] = [f"Workspace: {base}"]
    count = 0
    for current, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in {".git", "__pycache__", ".venv"})
        rel_dir = Path(current).relative_to(base)
        depth = len(rel_dir.parts)
        prefix = "  " * depth
        if rel_dir != Path("."):
            rows.append(f"{prefix}📁 {rel_dir.name}/")
            count += 1
        for filename in sorted(files):
            rows.append(f"{'  ' * (depth + 1)}📄 {filename}")
            count += 1
            if count >= max_entries:
                rows.append("… truncated …")
                return "\n".join(rows)
    if count == 0:
        rows.append("(empty)")
    return "\n".join(rows)


def read_text(relative: str, max_bytes: int | None = None) -> str:
    path = safe_path(relative)
    if not path.exists() or not path.is_file():
        raise WorkspaceError("File does not exist.")
    limit = max_bytes or CONFIG.max_file_preview_bytes
    data = path.read_bytes()
    if len(data) > limit:
        data = data[:limit]
        suffix = "\n\n[preview truncated]"
    else:
        suffix = ""
    try:
        return data.decode("utf-8") + suffix
    except UnicodeDecodeError as exc:
        raise WorkspaceError("This file is not UTF-8 text.") from exc


def write_text(relative: str, content: str) -> Path:
    path = safe_path(relative)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def import_files(paths: Iterable[str]) -> list[Path]:
    imported: list[Path] = []
    for raw in paths:
        source = Path(raw)
        if not source.exists() or not source.is_file():
            continue
        dest = safe_path(source.name)
        if dest.exists():
            stem, suffix = dest.stem, dest.suffix
            i = 1
            while dest.exists():
                dest = safe_path(f"{stem}_{i}{suffix}")
                i += 1
        shutil.copy2(source, dest)
        imported.append(dest)
    return imported


def zip_workspace(destination: Path | None = None) -> Path:
    base = root()
    destination = destination or Path("/mnt/data/kaggle-agent-hub-workspace.zip")
    destination.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in base.rglob("*"):
            if path.is_file() and ".git" not in path.parts:
                zf.write(path, path.relative_to(base))
    return destination


def context_snapshot(max_bytes: int | None = None) -> str:
    """Produce a compact text snapshot of common source files for direct-API chat."""
    limit = max_bytes or CONFIG.max_workspace_context_bytes
    allowed = {".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".md", ".txt", ".toml", ".yaml", ".yml", ".html", ".css", ".kt", ".java", ".rs", ".go", ".sh"}
    chunks: list[str] = []
    total = 0
    base = root()
    sensitive_names = {"auth.json", "credentials.json", "secrets.json", ".env"}
    for path in sorted(base.rglob("*")):
        lower_name = path.name.lower()
        if (
            not path.is_file()
            or path.suffix.lower() not in allowed
            or ".git" in path.parts
            or lower_name in sensitive_names
            or lower_name.startswith(".env.")
            or "secret" in lower_name
            or "credential" in lower_name
        ):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        rel = path.relative_to(base)
        chunk = f"\n--- FILE: {rel} ---\n{text}\n"
        encoded = chunk.encode("utf-8")
        if total + len(encoded) > limit:
            remaining = max(0, limit - total)
            if remaining:
                chunks.append(encoded[:remaining].decode("utf-8", errors="ignore"))
            chunks.append("\n[workspace context truncated]\n")
            break
        chunks.append(chunk)
        total += len(encoded)
    return "".join(chunks)
