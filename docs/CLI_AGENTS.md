# CLI Agents

The CLI tab runs tools inside the configured workspace.

Built-in command prefixes:

- Codex CLI: `codex exec --skip-git-repo-check <prompt>`
- Claude Code: `claude -p <prompt>`
- Gemini CLI: `gemini -p <prompt>`
- Custom CLI: user-supplied command prefix + prompt

CLI package names, login methods and flags may change independently of this project. The UI detects executables on `PATH` and reports missing tools instead of silently installing them.

For public tutorials, authenticate interactively or with each tool's officially supported mechanism. Never put auth files in the repository.
