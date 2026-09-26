# Contributing

1. Fork the repository and create a focused branch.
2. Never add real credentials or session tokens.
3. Keep provider adapters small and isolated.
4. Add tests for provider-registry or workspace behavior when relevant.
5. Run `python -m pytest -q` before opening a pull request.

Provider APIs evolve. Prefer configurable model names and base URLs instead of hard-coding assumptions into the UI.
