from pathlib import Path

import pytest

from core import workspace


def test_safe_path_stays_inside_workspace():
    p = workspace.safe_path("hello.txt")
    assert p.parent == workspace.root()


def test_safe_path_blocks_escape():
    with pytest.raises(workspace.WorkspaceError):
        workspace.safe_path("../../outside.txt")
