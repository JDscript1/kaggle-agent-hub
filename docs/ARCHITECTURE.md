# Architecture

## Layers

- `app.py` — runtime entry point.
- `bootstrap.py` — installs Python dependencies and launches the app; intended for the second Kaggle cell.
- `core/` — workspace confinement, CLI execution, configuration, secrets resolution, logs and system detection.
- `providers/` — direct API adapters.
- `ui/` — Gradio callbacks and interface composition.

## Authentication model

Two modes are deliberately separated:

1. **Direct API providers** — API keys from UI, environment variables or Kaggle Secrets.
2. **CLI agents** — Codex CLI, Claude Code, Gemini CLI or a custom command authenticated with their own supported login mechanisms.

The app does not convert subscription-login tokens into API keys and does not copy CLI credential files into notebooks.

## Provider adapters

Native adapters are used for:

- OpenAI Responses API
- Anthropic Messages API
- Google Gemini `generateContent`

An OpenAI-compatible adapter covers DeepSeek, Moonshot/Kimi, OpenRouter, Mistral, Groq, Together, Fireworks, xAI and custom endpoints.

## Workspace model

The default workspace is `/kaggle/working/agent-workspace` on Kaggle and `./workspace` elsewhere. Files UI operations resolve paths against that root and reject traversal outside it.
