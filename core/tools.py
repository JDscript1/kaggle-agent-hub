"""Safe, provider-independent tools for coding-agent integrations.

The registry in this module is deliberately small.  It gives future agent
loops one stable interface while keeping filesystem policy in one place.
"""
from __future__ import annotations

import difflib
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

from core.logging_store import LOGS
from core.notebook import NotebookError, delete_cell, insert_cell, list_cells, read_cell, update_cell
from core.terminal import TerminalError, execute_terminal
from core.workspace import WorkspaceError, root, safe_path


ToolHandler = Callable[[dict[str, Any]], "ToolResult"]


class ToolError(RuntimeError):
    """A safe, user-facing tool validation or execution error."""


@dataclass(frozen=True)
class ToolResult:
    """Serializable result returned by every registered tool."""

    success: bool
    data: Any = None
    error: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def ok(cls, data: Any = None, **metadata: Any) -> "ToolResult":
        return cls(success=True, data=data, metadata=metadata)

    @classmethod
    def failure(cls, error: str, **metadata: Any) -> "ToolResult":
        return cls(success=False, error=error, metadata=metadata)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"success": self.success, "data": self.data}
        if self.error is not None:
            result["error"] = self.error
        if self.metadata:
            result["metadata"] = self.metadata
        return result


@dataclass(frozen=True)
class AgentTool:
    """Definition and implementation of one agent-callable tool."""

    name: str
    description: str
    input_schema: dict[str, Any]
    handler: ToolHandler

    def schema(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ToolRegistry:
    """Named tool registry with uniform validation and error boundaries."""

    def __init__(self, tools: Iterable[AgentTool] | None = None) -> None:
        self._tools: dict[str, AgentTool] = {}
        for tool in tools or ():
            self.register(tool)

    def register(self, tool: AgentTool) -> None:
        if not tool.name or not tool.name.strip():
            raise ValueError("Tool name cannot be empty.")
        if tool.name in self._tools:
            raise ValueError(f"Tool already registered: {tool.name}")
        self._tools[tool.name] = tool

    def get(self, name: str) -> AgentTool:
        try:
            return self._tools[name]
        except KeyError as exc:
            raise ToolError(f"Unknown tool: {name}") from exc

    def names(self) -> list[str]:
        return list(self._tools)

    def schemas(self) -> list[dict[str, Any]]:
        return [self._tools[name].schema() for name in self._tools]

    def execute(self, name: str, arguments: dict[str, Any] | None = None) -> ToolResult:
        if arguments is not None and not isinstance(arguments, dict):
            return ToolResult.failure("Tool arguments must be an object.")
        LOGS.add(f"Tool call: {name}")
        try:
            result = self.get(name).handler(arguments or {})
        except ToolError as exc:
            result = ToolResult.failure(str(exc))
        except (OSError, UnicodeError) as exc:
            result = ToolResult.failure(f"Tool failed: {exc}")
        except Exception as exc:  # Keep provider/model loops from crashing on a tool bug.
            result = ToolResult.failure(f"Tool failed unexpectedly: {exc}")
        LOGS.add(f"Tool result: {name} ({'success' if result.success else 'error'})")
        return result


_SENSITIVE_BASENAMES = {
    ".env",
    "auth.json",
    "credentials.json",
    "secrets.json",
    "token.json",
}
_SENSITIVE_DIRS = {".codex", ".ssh"}
_SENSITIVE_SUFFIXES = {".key", ".pem"}
_IGNORED_DIRS = {".git", "__pycache__", ".venv", "venv", ".kaggle-agent-hub"}


def _is_sensitive(path: Path) -> bool:
    lowered_parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    return (
        name in _SENSITIVE_BASENAMES
        or name.startswith(".env.")
        or path.suffix.lower() in _SENSITIVE_SUFFIXES
        or bool(lowered_parts & _SENSITIVE_DIRS)
    )


def _relative_path(raw: Any, *, allow_empty: bool = False) -> tuple[str, Path]:
    if not isinstance(raw, str):
        raise ToolError("path must be a string.")
    relative = raw.strip()
    if not relative and not allow_empty:
        raise ToolError("path cannot be empty.")
    try:
        path = safe_path(relative or ".")
    except WorkspaceError as exc:
        raise ToolError(str(exc)) from exc
    return relative or ".", path


def _ensure_visible(relative: str, path: Path) -> None:
    if _is_sensitive(path.relative_to(root())):
        raise ToolError(f"Access to sensitive workspace path is blocked: {relative}")


def _visible_candidate(candidate: Path) -> bool:
    """Reject symlinks that resolve outside the active workspace."""
    try:
        candidate.resolve().relative_to(root())
    except ValueError:
        return False
    return True


def _read_file(arguments: dict[str, Any]) -> ToolResult:
    relative, path = _relative_path(arguments.get("path"))
    _ensure_visible(relative, path)
    if not path.is_file():
        raise ToolError("File does not exist.")
    max_bytes = arguments.get("max_bytes", 512 * 1024)
    if not isinstance(max_bytes, int) or max_bytes <= 0:
        raise ToolError("max_bytes must be a positive integer.")
    data = path.read_bytes()
    truncated = len(data) > max_bytes
    if truncated:
        data = data[:max_bytes]
    try:
        content = data.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ToolError("This file is not UTF-8 text.") from exc
    return ToolResult.ok({"path": relative, "content": content, "truncated": truncated})


def _list_files(arguments: dict[str, Any]) -> ToolResult:
    relative, path = _relative_path(arguments.get("path", "."), allow_empty=True)
    _ensure_visible(relative, path)
    if not path.is_dir():
        raise ToolError("Directory does not exist.")
    recursive = arguments.get("recursive", True)
    if not isinstance(recursive, bool):
        raise ToolError("recursive must be a boolean.")
    max_entries = arguments.get("max_entries", 500)
    if not isinstance(max_entries, int) or max_entries <= 0:
        raise ToolError("max_entries must be a positive integer.")

    entries: list[dict[str, Any]] = []
    iterator = path.rglob("*") if recursive else path.glob("*")
    for candidate in sorted(iterator, key=lambda item: str(item).lower()):
        rel = candidate.relative_to(root())
        if (
            not _visible_candidate(candidate)
            or any(part.lower() in _IGNORED_DIRS for part in rel.parts)
            or _is_sensitive(rel)
        ):
            continue
        entries.append({"path": str(rel), "type": "directory" if candidate.is_dir() else "file"})
        if len(entries) >= max_entries:
            break
    return ToolResult.ok({"path": relative, "entries": entries, "truncated": len(entries) >= max_entries})


def _search_files(arguments: dict[str, Any]) -> ToolResult:
    query = arguments.get("query")
    if not isinstance(query, str) or not query:
        raise ToolError("query must be a non-empty string.")
    relative, path = _relative_path(arguments.get("path", "."), allow_empty=True)
    _ensure_visible(relative, path)
    if not path.is_dir():
        raise ToolError("Search path must be a directory.")
    case_sensitive = arguments.get("case_sensitive", False)
    if not isinstance(case_sensitive, bool):
        raise ToolError("case_sensitive must be a boolean.")
    max_results = arguments.get("max_results", 100)
    if not isinstance(max_results, int) or max_results <= 0:
        raise ToolError("max_results must be a positive integer.")
    needle = query if case_sensitive else query.lower()
    matches: list[dict[str, Any]] = []
    for candidate in sorted(path.rglob("*"), key=lambda item: str(item).lower()):
        rel = candidate.relative_to(root())
        if (
            not candidate.is_file()
            or not _visible_candidate(candidate)
            or any(part.lower() in _IGNORED_DIRS for part in rel.parts)
            or _is_sensitive(rel)
        ):
            continue
        try:
            text = candidate.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(text.splitlines(), 1):
            haystack = line if case_sensitive else line.lower()
            if needle in haystack:
                matches.append({"path": str(rel), "line": line_number, "text": line})
                if len(matches) >= max_results:
                    return ToolResult.ok({"query": query, "matches": matches, "truncated": True})
    return ToolResult.ok({"query": query, "matches": matches, "truncated": False})


def _write_file(arguments: dict[str, Any]) -> ToolResult:
    relative, path = _relative_path(arguments.get("path"))
    _ensure_visible(relative, path)
    content = arguments.get("content")
    if not isinstance(content, str):
        raise ToolError("content must be a string.")
    if len(content.encode("utf-8")) > 2 * 1024 * 1024:
        raise ToolError("File content exceeds the 2 MiB tool limit.")
    overwrite = arguments.get("overwrite", True)
    if not isinstance(overwrite, bool):
        raise ToolError("overwrite must be a boolean.")
    if path.exists() and not overwrite:
        raise ToolError("File already exists; set overwrite=true to replace it.")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return ToolResult.ok({"path": relative, "bytes": len(content.encode("utf-8"))})


def _patch_file(arguments: dict[str, Any]) -> ToolResult:
    relative, path = _relative_path(arguments.get("path"))
    _ensure_visible(relative, path)
    old_text = arguments.get("old_text")
    new_text = arguments.get("new_text")
    if not isinstance(old_text, str) or not isinstance(new_text, str):
        raise ToolError("old_text and new_text must be strings.")
    if old_text == new_text:
        raise ToolError("Patch makes no changes.")
    if not path.is_file():
        raise ToolError("File does not exist.")
    try:
        original = path.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ToolError("This file is not UTF-8 text.") from exc
    occurrences = original.count(old_text)
    expected = arguments.get("expected_replacements", 1)
    if not isinstance(expected, int) or expected <= 0:
        raise ToolError("expected_replacements must be a positive integer.")
    if occurrences != expected:
        raise ToolError(f"Expected {expected} exact match(es), found {occurrences}.")
    updated = original.replace(old_text, new_text)
    path.write_text(updated, encoding="utf-8")
    diff = "".join(
        difflib.unified_diff(
            original.splitlines(keepends=True),
            updated.splitlines(keepends=True),
            fromfile=relative,
            tofile=relative,
        )
    )
    return ToolResult.ok({"path": relative, "diff": diff, "replacements": occurrences})


def _terminal_exec(arguments: dict[str, Any]) -> ToolResult:
    try:
        result = execute_terminal(
            arguments.get("command"),
            cwd=arguments.get("cwd"),
            timeout=arguments.get("timeout", 120),
            max_output=arguments.get("max_output", 120_000),
        )
    except TerminalError as exc:
        raise ToolError(str(exc)) from exc
    return ToolResult.ok(result)


def _notebook_call(function, arguments: dict[str, Any]) -> ToolResult:
    try:
        return ToolResult.ok(function(arguments))
    except NotebookError as exc:
        raise ToolError(str(exc)) from exc


def default_tool_registry() -> ToolRegistry:
    """Build the filesystem tools used by the first coding-agent milestone."""
    return ToolRegistry(
        [
            AgentTool(
                "read_file",
                "Read a UTF-8 text file inside the active workspace.",
                {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}, "max_bytes": {"type": "integer"}}},
                _read_file,
            ),
            AgentTool(
                "list_files",
                "List visible files and directories inside the active workspace.",
                {"type": "object", "properties": {"path": {"type": "string", "default": "."}, "recursive": {"type": "boolean"}, "max_entries": {"type": "integer"}}},
                _list_files,
            ),
            AgentTool(
                "search_files",
                "Search visible UTF-8 text files in the active workspace.",
                {"type": "object", "required": ["query"], "properties": {"query": {"type": "string"}, "path": {"type": "string"}, "case_sensitive": {"type": "boolean"}, "max_results": {"type": "integer"}}},
                _search_files,
            ),
            AgentTool(
                "write_file",
                "Create or replace a UTF-8 text file inside the active workspace.",
                {"type": "object", "required": ["path", "content"], "properties": {"path": {"type": "string"}, "content": {"type": "string"}, "overwrite": {"type": "boolean"}}},
                _write_file,
            ),
            AgentTool(
                "patch_file",
                "Apply one or more exact text replacements to a UTF-8 file and return a unified diff.",
                {"type": "object", "required": ["path", "old_text", "new_text"], "properties": {"path": {"type": "string"}, "old_text": {"type": "string"}, "new_text": {"type": "string"}, "expected_replacements": {"type": "integer"}}},
                _patch_file,
            ),
            AgentTool(
                "terminal_exec",
                "Run a controlled shell command in the active workspace.",
                {"type": "object", "required": ["command"], "properties": {"command": {"type": "string"}, "cwd": {"type": "string"}, "timeout": {"type": "integer", "default": 120}, "max_output": {"type": "integer", "default": 120000}}},
                _terminal_exec,
            ),
            AgentTool("list_cells", "List cells in a saved .ipynb file.", {"type": "object", "required": ["path"], "properties": {"path": {"type": "string"}}}, lambda args: _notebook_call(list_cells, args)),
            AgentTool("read_cell", "Read one cell from a saved .ipynb file.", {"type": "object", "required": ["path", "index"], "properties": {"path": {"type": "string"}, "index": {"type": "integer"}}}, lambda args: _notebook_call(read_cell, args)),
            AgentTool("insert_cell", "Insert a code, markdown, or raw cell into a saved .ipynb file.", {"type": "object", "required": ["path", "source"], "properties": {"path": {"type": "string"}, "index": {"type": "integer"}, "cell_type": {"type": "string"}, "source": {"type": "string"}}}, lambda args: _notebook_call(insert_cell, args)),
            AgentTool("update_cell", "Update one cell in a saved .ipynb file and clear stale code outputs by default.", {"type": "object", "required": ["path", "index", "source"], "properties": {"path": {"type": "string"}, "index": {"type": "integer"}, "source": {"type": "string"}, "clear_outputs": {"type": "boolean"}}}, lambda args: _notebook_call(update_cell, args)),
            AgentTool("delete_cell", "Delete one cell from a saved .ipynb file with an explicit empty-notebook safeguard.", {"type": "object", "required": ["path", "index"], "properties": {"path": {"type": "string"}, "index": {"type": "integer"}, "allow_empty": {"type": "boolean"}}}, lambda args: _notebook_call(delete_cell, args)),
        ]
    )


TOOLS = default_tool_registry()
