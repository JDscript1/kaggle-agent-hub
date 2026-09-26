from core.environment import runtime_context


def test_runtime_context_identifies_workspace_and_capabilities(monkeypatch, tmp_path):
    monkeypatch.setenv("TERMUX_VERSION", "test")
    from core import environment, workspace
    from core.config import CONFIG
    from dataclasses import replace

    monkeypatch.setattr(workspace, "CONFIG", replace(CONFIG, workspace=tmp_path))
    (tmp_path / "analysis.ipynb").write_text("{}", encoding="utf-8")
    context = runtime_context()

    assert "Termux on Android" in context
    assert f"active workspace: {tmp_path}" in context
    assert "available agent capabilities" in context
    assert "notebook files in workspace: analysis.ipynb" in context
    assert "live Kaggle UI cell insertion is not exposed" in context
    assert "API_KEY=" not in context


def test_agent_injects_runtime_context_before_user_messages(monkeypatch, tmp_path):
    from dataclasses import replace
    from core import tools, workspace
    from core.agent import ModelTurn, run_agent
    from core.config import CONFIG

    monkeypatch.setattr(workspace, "CONFIG", replace(CONFIG, workspace=tmp_path))
    captured = {}

    def model(messages, schemas):
        captured["messages"] = messages
        return ModelTurn(content="ready")

    result = run_agent([{"role": "user", "content": "What environment is this?"}], model, tools.default_tool_registry())

    assert result.completed
    assert captured["messages"][0]["role"] == "system"
    assert "Automatic runtime context" in captured["messages"][0]["content"]
    assert captured["messages"][1]["content"] == "What environment is this?"
