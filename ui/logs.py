from core.logging_store import LOGS


def refresh_logs() -> str:
    return LOGS.text()


def clear_logs() -> str:
    LOGS.clear()
    return ""
