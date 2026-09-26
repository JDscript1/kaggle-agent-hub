from providers.registry import adapter_for, make_config, names, preset


def test_core_providers_present():
    providers = set(names())
    assert {"OpenAI / Codex API", "Anthropic", "Google Gemini", "DeepSeek", "Kimi / Moonshot", "Qwen / DashScope"} <= providers


def test_presets_have_env_names():
    for name in names():
        assert preset(name).env_key


def test_openai_compatible_providers_expose_tool_calling():
    for name in ["DeepSeek", "Qwen / DashScope", "OpenRouter", "Kimi / Moonshot"]:
        assert adapter_for(name).supports_tools()


def test_openai_compatible_tool_call_translation(monkeypatch):
    captured = {}

    class Response:
        is_error = False
        text = ""

        def json(self):
            return {
                "choices": [{
                    "message": {
                        "content": "",
                        "tool_calls": [{
                            "id": "call-1",
                            "function": {"name": "read_file", "arguments": '{"path":"app.py"}'},
                        }],
                    }
                }]
            }

    class Client:
        def __init__(self, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def post(self, url, headers, json):
            captured.update({"url": url, "payload": json})
            return Response()

    monkeypatch.setattr("providers.openai_compatible.httpx.Client", Client)
    config = make_config("DeepSeek", "deepseek-chat", "test-key", "https://api.deepseek.com", 0.2, 100)
    result = adapter_for("DeepSeek").generate_turn(
        [{"role": "user", "content": "inspect"}],
        config,
        [{"name": "read_file", "description": "Read", "input_schema": {"type": "object"}}],
    )

    assert result.tool_calls[0].name == "read_file"
    assert result.tool_calls[0].arguments == {"path": "app.py"}
    assert captured["payload"]["tools"][0]["function"]["name"] == "read_file"
    assert captured["payload"]["tool_choice"] == "auto"
