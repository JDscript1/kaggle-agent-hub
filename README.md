# Kaggle Agent Hub

A public, notebook-friendly multi-provider AI workspace built for **Kaggle first**, while remaining usable on Colab/Linux/local Python.

It combines two workflows in one UI:

1. **Direct API chat** with OpenAI/Codex API, Anthropic, Gemini, DeepSeek, Qwen/DashScope, Kimi/Moonshot, OpenRouter, Mistral, Groq, Together, Fireworks, xAI and generic OpenAI-compatible endpoints.
2. **Authenticated CLI coding agents** such as Codex CLI, Claude Code and Gemini CLI, running directly against a confined workspace.

The project is intentionally designed for a YouTube tutorial: the Kaggle notebook itself can stay extremely small.

## Two-cell Kaggle install

### Cell 1

```python
!git clone https://github.com/Specter128/kaggle-agent-hub.git
```

### Cell 2

```python
%run /kaggle/working/kaggle-agent-hub/bootstrap.py
```

That is the whole notebook setup. `bootstrap.py` installs the Python requirements and launches the Gradio interface.

> Kaggle Internet must be enabled when you need external provider APIs, package downloads or a public Gradio tunnel.

## UI

- **Chat** — direct API conversation with provider/model switching.
- **CLI Agents** — run coding agents inside the workspace.
- **Files** — inspect, edit, import and export project files.
- **Logs** — runtime diagnostics without intentionally logging raw API keys.
- **System** — GPU/RAM/disk and CLI detection.
- **Settings** — workspace/security guidance.

## Authentication and secrets

Kaggle Agent Hub does **not** treat a ChatGPT/Claude/Gemini subscription login as an API key.

For direct API mode, use an API key from the provider. Values can come from:

1. the password field in the UI,
2. environment variables,
3. Kaggle Secrets.

You can also save a provider key, model and endpoint from the **Settings** tab. These values are held only in the active UI session and are not written to project files. The Settings key is used only for direct API chat; it is never injected into CLI-agent subscription logins.

The standard secret names are documented in [`docs/PROVIDERS.md`](docs/PROVIDERS.md).

For CLI mode, authenticate the CLI with its own supported login mechanism. The project does not copy or publish CLI auth files.

## Workspace

On Kaggle, the default workspace is:

```text
/kaggle/working/agent-workspace
```

On other systems it defaults to `./workspace`.

The Files tab rejects paths that escape this workspace.

## Local run

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py --no-share
```

## Test

```bash
pip install pytest
pytest -q
```

## Project structure

```text
kaggle-agent-hub/
├── app.py
├── bootstrap.py
├── requirements.txt
├── core/
│   ├── config.py
│   ├── logging_store.py
│   ├── runner.py
│   ├── secrets.py
│   ├── session.py
│   ├── system_info.py
│   └── workspace.py
├── providers/
│   ├── base.py
│   ├── openai.py
│   ├── anthropic.py
│   ├── gemini.py
│   ├── openai_compatible.py
│   └── registry.py
├── ui/
│   ├── app.py
│   ├── chat.py
│   ├── files.py
│   └── providers.py
├── docs/
└── tests/
```

## Security

Read [`SECURITY.md`](SECURITY.md) before publishing a notebook or repository. In particular, never commit API keys, OAuth/session tokens or CLI `auth.json` files.

## License

MIT.
