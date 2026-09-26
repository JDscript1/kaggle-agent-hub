from core.session import clear_provider_secret, new_session, provider_setting, save_provider_setting


def test_provider_api_settings_are_session_only():
    state = save_provider_setting(
        new_session(),
        "Qwen / DashScope",
        api_key="qwen-secret",
        model="qwen-max",
        base_url="https://example.test/v1",
    )
    assert provider_setting(state, "Qwen / DashScope") == {
        "api_key": "qwen-secret",
        "model": "qwen-max",
        "base_url": "https://example.test/v1",
    }
    cleared = clear_provider_secret(state, "Qwen / DashScope")
    assert provider_setting(cleared, "Qwen / DashScope")["api_key"] == ""
    assert provider_setting(state, "Qwen / DashScope")["api_key"] == "qwen-secret"
