# Prompt for Codex: publish this project to GitHub

Use this prompt from the directory that contains the extracted `kaggle-agent-hub` project:

```text
Inspect this repository completely before changing anything.

Goal: prepare and publish Kaggle Agent Hub to my existing GitHub repository:
https://github.com/Specter128/kaggle-agent-hub

Requirements:
1. Run the Python syntax checks and tests first.
2. Fix only real issues you find; do not remove working provider integrations.
3. Verify that no API keys, OAuth tokens, auth.json files, cookies, .env secrets, or credentials are tracked.
4. Keep the public two-cell Kaggle workflow exactly documented:
   !git clone https://github.com/Specter128/kaggle-agent-hub.git
   %run /kaggle/working/kaggle-agent-hub/bootstrap.py
5. Keep support for OpenAI/Codex API, Anthropic, Gemini, DeepSeek, Kimi/Moonshot, OpenRouter, Mistral, Groq, Together, Fireworks, xAI, generic OpenAI-compatible endpoints, plus the optional CLI Agents tab.
6. Keep direct API credentials separate from CLI subscription/login authentication.
7. If this directory is not already a git repository, initialize it with branch main.
8. Set the remote named origin to the GitHub repository above if needed.
9. Show me the final git status and the files that will be committed before pushing.
10. Commit with a clear initial-release message and push to main after the repository is clean and tests pass.

Do not print or commit any secret values.
```
