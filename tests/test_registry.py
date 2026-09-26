from providers.registry import names, preset


def test_core_providers_present():
    providers = set(names())
    assert {"OpenAI / Codex API", "Anthropic", "Google Gemini", "DeepSeek", "Kimi / Moonshot"} <= providers


def test_presets_have_env_names():
    for name in names():
        assert preset(name).env_key
