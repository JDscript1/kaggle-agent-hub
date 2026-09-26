"""One-command bootstrap used by Kaggle/Colab tutorial notebooks."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent


def run(command: list[str]) -> None:
    print("+", " ".join(command))
    subprocess.check_call(command, cwd=ROOT)


def main() -> None:
    print("Kaggle Agent Hub bootstrap")
    print("Repository:", ROOT)
    run([sys.executable, "-m", "pip", "install", "-q", "-r", str(ROOT / "requirements.txt")])

    workspace = Path(
        os.getenv(
            "KAGGLE_AGENT_HUB_WORKSPACE",
            "/kaggle/working/agent-workspace" if Path("/kaggle/working").exists() else ROOT / "workspace",
        )
    )
    workspace.mkdir(parents=True, exist_ok=True)
    print("Workspace:", workspace)
    print("Starting UI…")
    run([sys.executable, str(ROOT / "app.py")])


if __name__ == "__main__":
    main()
