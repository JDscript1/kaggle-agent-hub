from core.config import CONFIG


def summary() -> str:
    return f"Workspace: {CONFIG.workspace}\\nPublic share default: {CONFIG.share}"
