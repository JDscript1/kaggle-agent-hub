from __future__ import annotations

import argparse

from core.config import CONFIG
from core.logging_store import LOGS
from ui.app import build_app


def main() -> None:
    parser = argparse.ArgumentParser(description="Kaggle Agent Hub")
    parser.add_argument("--no-share", action="store_true", help="Disable the Gradio public share tunnel")
    parser.add_argument("--port", type=int, default=CONFIG.port)
    args = parser.parse_args()

    share = False if args.no_share else CONFIG.share
    LOGS.add(f"Starting Kaggle Agent Hub on port {args.port}; share={share}")
    demo = build_app()
    demo.launch(server_name=CONFIG.host, server_port=args.port, share=share, show_error=True)


if __name__ == "__main__":
    main()
