from dataclasses import replace
from pathlib import Path

import pytest

from core import tools, workspace
from core.config import CONFIG


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "CONFIG", replace(CONFIG, workspace=tmp_path))
    return tools.default_tool_registry()


def test_registry_exposes_schemas_and_structured_results(registry):
    assert registry.names() == ["read_file", "list_files", "search_files", "write_file", "patch_file", "terminal_exec", "list_cells", "read_cell", "insert_cell", "update_cell", "delete_cell"]
    result = registry.execute("write_file", {"path": "src/app.py", "content": "print('ok')\n"})
    assert result.success
    assert result.to_dict()["data"]["path"] == "src/app.py"


@pytest.mark.parametrize("path", ["../../outside.txt", "/etc/passwd", "~/.ssh/id_rsa"])
def test_all_filesystem_tools_block_workspace_escape(registry, path):
    assert not registry.execute("read_file", {"path": path}).success
    assert not registry.execute("write_file", {"path": path, "content": "no"}).success
    assert not registry.execute("patch_file", {"path": path, "old_text": "a", "new_text": "b"}).success
    assert not registry.execute("list_files", {"path": path}).success
    assert not registry.execute("search_files", {"query": "x", "path": path}).success


def test_read_search_and_list_hide_sensitive_files(registry, tmp_path):
    (tmp_path / "visible.txt").write_text("needle here\n", encoding="utf-8")
    (tmp_path / ".env").write_text("API_KEY=secret\n", encoding="utf-8")
    (tmp_path / "auth.json").write_text("secret", encoding="utf-8")

    listed = registry.execute("list_files", {}).data["entries"]
    assert {entry["path"] for entry in listed} == {"visible.txt"}
    found = registry.execute("search_files", {"query": "needle"}).data["matches"]
    assert found[0]["path"] == "visible.txt"
    assert not registry.execute("read_file", {"path": ".env"}).success


def test_list_and_search_reject_symlink_outside_workspace(registry, tmp_path):
    outside = tmp_path.parent / "outside-secret.txt"
    outside.write_text("outside-secret", encoding="utf-8")
    (tmp_path / "linked.txt").symlink_to(outside)

    listed = registry.execute("list_files", {}).data["entries"]
    assert all(entry["path"] != "linked.txt" for entry in listed)
    found = registry.execute("search_files", {"query": "outside-secret"}).data["matches"]
    assert found == []


def test_patch_file_requires_unique_match_and_returns_diff(registry):
    registry.execute("write_file", {"path": "main.py", "content": "old\n"})
    result = registry.execute("patch_file", {"path": "main.py", "old_text": "old", "new_text": "new"})
    assert result.success
    assert "-old" in result.data["diff"]
    assert registry.execute("read_file", {"path": "main.py"}).data["content"] == "new\n"

    registry.execute("write_file", {"path": "duplicate.txt", "content": "x x"})
    duplicate = registry.execute("patch_file", {"path": "duplicate.txt", "old_text": "x", "new_text": "y"})
    assert not duplicate.success
    assert "Expected 1" in duplicate.error


def test_tool_registry_handles_unknown_tool_without_exception(registry):
    result = registry.execute("missing", {})
    assert not result.success
    assert result.error == "Unknown tool: missing"


def test_terminal_exec_uses_workspace_and_returns_process_result(registry, tmp_path):
    result = registry.execute("terminal_exec", {"command": "printf 'hello' > terminal.txt && pwd"})
    assert result.success
    assert result.data["exit_code"] == 0
    assert result.data["cwd"] == "."
    assert "hello" not in result.data["output"]
    assert (tmp_path / "terminal.txt").read_text(encoding="utf-8") == "hello"


def test_terminal_exec_reports_workspace_cwd_and_blocks_dangerous_commands(registry, tmp_path):
    location = registry.execute("terminal_exec", {"command": "pwd"})
    assert location.success
    assert Path(location.data["output"].strip()).resolve() == tmp_path.resolve()
    blocked = registry.execute("terminal_exec", {"command": "rm -rf /"})
    assert not blocked.success
    assert "safety policy" in blocked.error


def test_terminal_exec_masks_environment_values(registry, monkeypatch):
    monkeypatch.setenv("TEST_AGENT_SECRET", "super-secret-value")
    result = registry.execute("terminal_exec", {"command": "printf '%s' \"$TEST_AGENT_SECRET\""})
    assert result.success
    assert "super-secret-value" not in result.data["output"]
    assert "supe…alue" in result.data["output"]


def test_notebook_tools_list_insert_update_and_delete_cells(registry, tmp_path):
    notebook = tmp_path / "analysis.ipynb"
    notebook.write_text('{"cells": [{"cell_type": "code", "metadata": {}, "source": ["print(1)\\n"], "outputs": [], "execution_count": 1}], "metadata": {}, "nbformat": 4, "nbformat_minor": 5}', encoding="utf-8")

    listed = registry.execute("list_cells", {"path": "analysis.ipynb"})
    assert listed.success and listed.data["count"] == 1
    inserted = registry.execute("insert_cell", {"path": "analysis.ipynb", "index": 0, "cell_type": "markdown", "source": "# Title"})
    assert inserted.success
    updated = registry.execute("update_cell", {"path": "analysis.ipynb", "index": 1, "source": "print(2)"})
    assert updated.success and updated.data["before"] == "print(1)\n"
    read = registry.execute("read_cell", {"path": "analysis.ipynb", "index": 1})
    assert read.data["source"] == "print(2)"
    deleted = registry.execute("delete_cell", {"path": "analysis.ipynb", "index": 0})
    assert deleted.success
