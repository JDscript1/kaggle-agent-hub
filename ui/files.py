from __future__ import annotations

from pathlib import Path

from core.logging_store import LOGS
from core.workspace import WorkspaceError, import_files, list_tree, read_text, write_text, zip_workspace


def refresh_tree() -> str:
    return list_tree()


def open_file(path: str) -> str:
    try:
        return read_text(path.strip())
    except Exception as exc:
        return f"Error: {exc}"


def save_file(path: str, content: str) -> tuple[str, str]:
    try:
        saved = write_text(path.strip(), content)
        LOGS.add(f"Saved workspace file: {saved.name}")
        return f"Saved: {saved}", list_tree()
    except Exception as exc:
        LOGS.add(f"File save error: {exc}", "ERROR")
        return f"Error: {exc}", list_tree()


def upload_files(files) -> tuple[str, str]:
    if not files:
        return "No files selected.", list_tree()
    raw_paths = []
    for f in files:
        if isinstance(f, str):
            raw_paths.append(f)
        elif hasattr(f, "name"):
            raw_paths.append(f.name)
    imported = import_files(raw_paths)
    LOGS.add(f"Imported {len(imported)} file(s) into workspace")
    return "Imported: " + ", ".join(p.name for p in imported), list_tree()


def export_zip() -> str:
    path = zip_workspace()
    LOGS.add(f"Workspace archive created: {path}")
    return str(path)
