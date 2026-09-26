"""Structured editing for saved Jupyter notebook files inside the workspace."""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from core.workspace import WorkspaceError, root, safe_path


class NotebookError(RuntimeError):
    pass


def _notebook_path(raw: Any) -> tuple[str, Path]:
    if not isinstance(raw, str) or not raw.strip():
        raise NotebookError("path must be a non-empty string.")
    relative = raw.strip()
    try:
        path = safe_path(relative)
    except WorkspaceError as exc:
        raise NotebookError(str(exc)) from exc
    if path.suffix.lower() != ".ipynb":
        raise NotebookError("Notebook tools require a .ipynb file.")
    if path.name.lower() in {".env", "auth.json", "credentials.json", "secrets.json", "token.json"}:
        raise NotebookError("Access to sensitive workspace files is blocked.")
    return relative, path


def _load(raw: Any) -> tuple[str, Path, dict[str, Any]]:
    relative, path = _notebook_path(raw)
    if not path.is_file():
        raise NotebookError("Notebook file does not exist.")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise NotebookError("Notebook is not valid UTF-8 JSON.") from exc
    if not isinstance(document, dict) or not isinstance(document.get("cells"), list):
        raise NotebookError("Notebook JSON must contain a cells list.")
    return relative, path, document


def _source(value: Any) -> str:
    if isinstance(value, list):
        return "".join(str(part) for part in value)
    return str(value or "")


def _cell_type(value: Any) -> str:
    if value not in {"code", "markdown", "raw"}:
        raise NotebookError("cell_type must be code, markdown, or raw.")
    return value


def _write(path: Path, document: dict[str, Any]) -> None:
    payload = json.dumps(document, ensure_ascii=False, indent=1) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(payload)
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def list_cells(arguments: dict[str, Any]) -> dict[str, Any]:
    relative, _, document = _load(arguments.get("path"))
    cells = [
        {"index": index, "cell_type": cell.get("cell_type", "unknown"), "source": _source(cell.get("source", ""))[:500]}
        for index, cell in enumerate(document["cells"])
    ]
    return {"path": relative, "count": len(cells), "cells": cells}


def read_cell(arguments: dict[str, Any]) -> dict[str, Any]:
    relative, _, document = _load(arguments.get("path"))
    index = arguments.get("index")
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(document["cells"]):
        raise NotebookError("index is outside the notebook cell range.")
    cell = document["cells"][index]
    return {"path": relative, "index": index, "cell_type": cell.get("cell_type", "unknown"), "source": _source(cell.get("source", ""))}


def insert_cell(arguments: dict[str, Any]) -> dict[str, Any]:
    relative, path, document = _load(arguments.get("path"))
    cell_type = _cell_type(arguments.get("cell_type", "code"))
    source = arguments.get("source")
    if not isinstance(source, str):
        raise NotebookError("source must be a string.")
    index = arguments.get("index", len(document["cells"]))
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index <= len(document["cells"]):
        raise NotebookError("index is outside the insertion range.")
    cell: dict[str, Any] = {"cell_type": cell_type, "metadata": {}, "source": source.splitlines(keepends=True)}
    if cell_type == "code":
        cell.update({"execution_count": None, "outputs": []})
    document["cells"].insert(index, cell)
    _write(path, document)
    return {"path": relative, "index": index, "cell_type": cell_type}


def update_cell(arguments: dict[str, Any]) -> dict[str, Any]:
    relative, path, document = _load(arguments.get("path"))
    index = arguments.get("index")
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(document["cells"]):
        raise NotebookError("index is outside the notebook cell range.")
    source = arguments.get("source")
    if not isinstance(source, str):
        raise NotebookError("source must be a string.")
    cell = document["cells"][index]
    before = _source(cell.get("source", ""))
    cell["source"] = source.splitlines(keepends=True)
    if cell.get("cell_type") == "code" and arguments.get("clear_outputs", True):
        cell["execution_count"] = None
        cell["outputs"] = []
    _write(path, document)
    return {"path": relative, "index": index, "before": before, "after": source}


def delete_cell(arguments: dict[str, Any]) -> dict[str, Any]:
    relative, path, document = _load(arguments.get("path"))
    index = arguments.get("index")
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(document["cells"]):
        raise NotebookError("index is outside the notebook cell range.")
    if len(document["cells"]) == 1 and not arguments.get("allow_empty", False):
        raise NotebookError("Refusing to delete the only cell without allow_empty=true.")
    deleted = document["cells"].pop(index)
    _write(path, document)
    return {"path": relative, "index": index, "deleted": {"cell_type": deleted.get("cell_type"), "source": _source(deleted.get("source", ""))}}
