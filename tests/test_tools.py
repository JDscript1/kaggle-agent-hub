from dataclasses import replace

import pytest

from core import tools, workspace
from core.config import CONFIG


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "CONFIG", replace(CONFIG, workspace=tmp_path))
    return tools.default_tool_registry()


def test_registry_exposes_schemas_and_structured_results(registry):
    assert registry.names() == ["read_file", "list_files", "search_files", "write_file", "patch_file"]
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
