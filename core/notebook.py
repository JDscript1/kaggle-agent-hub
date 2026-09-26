"""Structured editing for saved Jupyter notebook files inside the workspace."""
from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from copy import deepcopy
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


def _cell_output_text(cell: dict[str, Any]) -> str:
    chunks: list[str] = []
    for output in cell.get("outputs", []):
        if output.get("output_type") == "stream":
            chunks.append(_source(output.get("text", "")))
        elif output.get("output_type") in {"execute_result", "display_data"}:
            data = output.get("data", {})
            if isinstance(data, dict):
                chunks.append(_source(data.get("text/plain", "")))
        elif output.get("output_type") == "error":
            chunks.append("\n".join(str(line) for line in output.get("traceback", [])))
    return "".join(chunks)


def _execute_python_fallback(relative: str, path: Path, document: dict[str, Any], index: int, timeout: int) -> dict[str, Any]:
    source = "\n\n".join(
        _source(cell.get("source", ""))
        for cell in document["cells"][: index + 1]
        if cell.get("cell_type") == "code"
    )
    try:
        process = subprocess.run(
            [sys.executable, "-c", source],
            cwd=root(),
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise NotebookError(f"Notebook execution timed out after {timeout}s.") from exc
    output = (process.stdout or "") + (process.stderr or "")
    target = document["cells"][index]
    target["outputs"] = [{"output_type": "stream", "name": "stdout", "text": output}] if output else []
    target["execution_count"] = 1
    _write(path, document)
    if process.returncode != 0:
        raise NotebookError(f"Notebook execution failed with exit code {process.returncode}: {output[-4000:]}")
    return {"path": relative, "index": index, "execution_count": 1, "output": output[-120_000:], "kernel": "python-subprocess"}


def execute_cell(arguments: dict[str, Any]) -> dict[str, Any]:
    """Execute cells from the start of a notebook through one code cell.

    This uses a temporary kernel. It is not the live Kaggle frontend kernel,
    but running the prefix preserves ordinary notebook variable dependencies.
    """
    relative, path, document = _load(arguments.get("path"))
    index = arguments.get("index")
    if not isinstance(index, int) or isinstance(index, bool) or not 0 <= index < len(document["cells"]):
        raise NotebookError("index is outside the notebook cell range.")
    if document["cells"][index].get("cell_type") != "code":
        raise NotebookError("Only code cells can be executed.")
    timeout = arguments.get("timeout", 120)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or not 1 <= timeout <= 3600:
        raise NotebookError("timeout must be an integer between 1 and 3600 seconds.")
    kernel_name = arguments.get("kernel_name", "python3")
    if not isinstance(kernel_name, str) or not kernel_name.strip():
        raise NotebookError("kernel_name must be a non-empty string.")
    try:
        import nbformat
        from nbclient import NotebookClient
    except ImportError:
        if kernel_name not in {"python", "python3"}:
            raise NotebookError("nbclient is required for non-Python notebook kernels.")
        return _execute_python_fallback(relative, path, document, index, timeout)

    execution_document = nbformat.from_dict(deepcopy(document))
    execution_document.cells = execution_document.cells[: index + 1]
    for cell in execution_document.cells:
        if cell.get("cell_type") == "code":
            cell["outputs"] = []
            cell["execution_count"] = None
    client = NotebookClient(execution_document, timeout=timeout, kernel_name=kernel_name, resources={"metadata": {"path": str(root())}})
    try:
        client.execute()
    except Exception as exc:
        if "No such kernel" in str(exc) and kernel_name in {"python", "python3"}:
            return _execute_python_fallback(relative, path, document, index, timeout)
        # nbclient still leaves executed outputs in the in-memory document.
        for original, executed in zip(document["cells"], execution_document.cells):
            if executed.get("cell_type") == "code":
                original["outputs"] = executed.get("outputs", [])
                original["execution_count"] = executed.get("execution_count")
        _write(path, document)
        raise NotebookError(f"Notebook execution failed: {exc}") from exc

    for original, executed in zip(document["cells"], execution_document.cells):
        if executed.get("cell_type") == "code":
            original["outputs"] = executed.get("outputs", [])
            original["execution_count"] = executed.get("execution_count")
    _write(path, document)
    target = execution_document.cells[index]
    output = _cell_output_text(target)
    return {"path": relative, "index": index, "execution_count": target.get("execution_count"), "output": output[-120_000:]}
