# Security

## Secrets

Kaggle Agent Hub is designed for public notebooks and repositories.

- Never commit API keys, OAuth tokens, cookies, `auth.json`, `.env`, or browser session data.
- Prefer Kaggle Secrets or environment variables for API keys.
- Keys entered in the UI are used only for the request and are not deliberately persisted by the project.
- CLI authentication is kept separate from direct API-provider settings.
- Do not upload `~/.codex/auth.json`, Claude Code credentials, Gemini CLI credentials, or similar login files to GitHub.

## Workspace

The Files UI confines reads and writes to the configured workspace root and rejects path traversal outside it.

## Reporting

For a security issue, open a private security advisory on GitHub rather than posting a secret in a public issue.
