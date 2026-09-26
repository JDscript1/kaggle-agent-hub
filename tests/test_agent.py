from dataclasses import replace

import pytest

from core import tools, workspace
from core.agent import ModelTurn, ToolCall, run_agent
from core.config import CONFIG


@pytest.fixture()
def registry(tmp_path, monkeypatch):
    monkeypatch.setattr(workspace, "CONFIG", replace(CONFIG, workspace=tmp_path))
    return tools.default_tool_registry()


def test_agent_loop_executes_tool_then_returns_final_response(registry, tmp_path):
    (tmp_path / "app.py").write_text("print('fixed')\n", encoding="utf-8")
    turns = iter([
        ModelTurn(tool_calls=(ToolCall("call-1", "read_file", {"path": "app.py"}),)),
        ModelTurn(content="I inspected app.py and it is ready."),
    ])
    events = []

    result = run_agent([{"role": "user", "content": "Inspect app.py"}], lambda messages, schemas: next(turns), registry, on_event=events.append)

    assert result.completed
    assert result.response == "I inspected app.py and it is ready."
    assert result.steps == 2
    assert result.tool_calls == 1
    assert any(event.kind == "tool_result" and event.tool_name == "read_file" for event in events)
    tool_messages = [message for message in result.messages if message.get("role") == "tool"]
    assert tool_messages and '"success": true' in tool_messages[0]["content"]


def test_agent_loop_enforces_step_limit(registry):
    def endless_model(messages, schemas):
        return ModelTurn(tool_calls=(ToolCall("loop", "list_files", {}),))

    result = run_agent([], endless_model, registry, max_steps=2)

    assert not result.completed
    assert result.steps == 2
    assert result.error == "Agent exceeded the maximum number of steps."


def test_agent_loop_enforces_tool_call_limit(registry):
    def two_calls(messages, schemas):
        return ModelTurn(tool_calls=(
            ToolCall("one", "list_files", {}),
            ToolCall("two", "list_files", {}),
        ))

    result = run_agent([], two_calls, registry, max_steps=3, max_tool_calls=1)

    assert not result.completed
    assert result.tool_calls == 1
    assert result.error == "Agent exceeded the maximum number of tool calls."


def test_agent_loop_can_be_stopped_between_tool_calls(registry):
    stopped = False

    def stop_after_first_tool():
        return stopped

    def model(messages, schemas):
        nonlocal stopped
        stopped = True
        return ModelTurn(tool_calls=(ToolCall("one", "list_files", {}),))

    result = run_agent([], model, registry, should_stop=stop_after_first_tool)

    assert result.stopped
    assert not result.completed
