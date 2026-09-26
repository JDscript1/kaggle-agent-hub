# Providers

The UI includes configurable presets for:

- OpenAI / Codex API
- Anthropic
- Google Gemini
- DeepSeek
- Qwen / DashScope
- Kimi / Moonshot
- OpenRouter
- Mistral
- Groq
- Together
- Fireworks
- xAI
- Custom OpenAI-compatible endpoint

Model names and endpoints are editable because provider catalogs change over time.

## Direct APIs vs CLI logins

An API key and a consumer subscription login are different credentials. Kaggle Agent Hub keeps them separate.

For coding-agent behavior, use the `CLI Agents` tab after authenticating the corresponding CLI in the environment. For ordinary API chat, use the `Chat` tab or save a key in `Settings`. Settings keys are session-only and are never used as subscription credentials.
