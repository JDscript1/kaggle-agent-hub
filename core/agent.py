"""Small provider-independent tool-calling agent loop.

Provider adapters can translate their native tool-call format to ``ModelTurn``
and back.  Keeping the loop here means tool policy does not leak into the UI
or into any one provider implementation.
"""
from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Protocol

from core.logging_store import LOGS
from core.tools import ToolRegistry, ToolResult


class AgentModel(Protocol):
    def __call__(self, messages: list[dict[str, Any]], tools: list[dict[str, Any]]) -> "ModelTurn | str | dict[str, Any]": ...


@dataclass(frozen=True)
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class ModelTurn:
    content: str = ""
    tool_calls: tuple[ToolCall, ...] = ()


@dataclass(frozen=True)
class AgentEvent:
    kind: str
    step: int
    tool_name: str | None = None
    tool_call_id: str | None = None
    result: ToolResult | None = None


@dataclass(frozen=True)
class AgentRunResult:
    response: str
    messages: list[dict[str, Any]]
    steps: int
    tool_calls: int
    completed: bool
    stopped: bool = False
    error: str | None = None


class AgentError(RuntimeError):
    pass


def _normalize_turn(raw: ModelTurn | str | dict[str, Any]) -> ModelTurn:
    if isinstance(raw, ModelTurn):
        return raw
    if isinstance(raw, str):
        return ModelTurn(content=raw)
    if not isinstance(raw, dict):
        raise AgentError("Model returned an unsupported turn format.")

    calls: list[ToolCall] = []
    for index, raw_call in enumerate(raw.get("tool_calls", []) or []):
        if not isinstance(raw_call, dict):
            raise AgentError("Model returned an invalid tool call.")
        function = raw_call.get("function") if isinstance(raw_call.get("function"), dict) else raw_call
        name = function.get("name")
        arguments = function.get("arguments", {})
        if not isinstance(name, str) or not name:
            raise AgentError("Model returned a tool call without a name.")
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as exc:
                raise AgentError(f"Tool call {name} has invalid JSON arguments.") from exc
        if not isinstance(arguments, dict):
            raise AgentError(f"Tool call {name} arguments must be an object.")
        calls.append(ToolCall(str(raw_call.get("id", f"call-{index + 1}")), name, arguments))
    content = raw.get("content", "")
    if content is None:
        content = ""
    if not isinstance(content, str):
        content = str(content)
    return ModelTurn(content=content, tool_calls=tuple(calls))


def _emit(callback: Callable[[AgentEvent], None] | None, event: AgentEvent) -> None:
    if callback is not None:
        callback(event)


def run_agent(
    messages: list[dict[str, Any]],
    model: AgentModel,
    registry: ToolRegistry,
    *,
    max_steps: int = 8,
    max_tool_calls: int = 20,
    timeout: float = 300.0,
    should_stop: Callable[[], bool] | None = None,
    on_event: Callable[[AgentEvent], None] | None = None,
) -> AgentRunResult:
    """Run model/tool turns until a final response or a safety limit.

    ``model`` is intentionally a callback rather than a provider type.  A
    native provider adapter can later translate ``messages`` and schemas into
    OpenAI, Anthropic, Gemini, or another provider's format.
    """
    if not isinstance(messages, list):
        raise AgentError("messages must be a list.")
    if not isinstance(max_steps, int) or isinstance(max_steps, bool) or max_steps <= 0:
        raise AgentError("max_steps must be a positive integer.")
    if not isinstance(max_tool_calls, int) or isinstance(max_tool_calls, bool) or max_tool_calls <= 0:
        raise AgentError("max_tool_calls must be a positive integer.")
    if timeout <= 0:
        raise AgentError("timeout must be positive.")

    conversation = [dict(message) for message in messages]
    started = time.monotonic()
    total_tool_calls = 0
    tools = registry.schemas()

    for step in range(1, max_steps + 1):
        if should_stop is not None and should_stop():
            return AgentRunResult("Agent run stopped.", conversation, step - 1, total_tool_calls, False, stopped=True)
        if time.monotonic() - started >= timeout:
            return AgentRunResult("", conversation, step - 1, total_tool_calls, False, error="Agent timed out.")

        LOGS.add(f"Agent step {step}")
        _emit(on_event, AgentEvent("agent_step", step))
        try:
            turn = _normalize_turn(model(conversation, tools))
        except Exception as exc:
            error = f"Model turn failed: {exc}"
            LOGS.add(error, "ERROR")
            return AgentRunResult("", conversation, step, total_tool_calls, False, error=error)

        assistant_message: dict[str, Any] = {"role": "assistant", "content": turn.content}
        if turn.tool_calls:
            assistant_message["tool_calls"] = [
                {"id": call.id, "name": call.name, "arguments": call.arguments} for call in turn.tool_calls
            ]
        conversation.append(assistant_message)
        if not turn.tool_calls:
            return AgentRunResult(turn.content, conversation, step, total_tool_calls, True)

        for call in turn.tool_calls:
            total_tool_calls += 1
            if total_tool_calls > max_tool_calls:
                error = "Agent exceeded the maximum number of tool calls."
                LOGS.add(error, "ERROR")
                return AgentRunResult("", conversation, step, total_tool_calls - 1, False, error=error)
            if should_stop is not None and should_stop():
                return AgentRunResult("Agent run stopped.", conversation, step, total_tool_calls - 1, False, stopped=True)
            _emit(on_event, AgentEvent("tool_call", step, call.name, call.id))
            result = registry.execute(call.name, call.arguments)
            _emit(on_event, AgentEvent("tool_result", step, call.name, call.id, result))
            conversation.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": call.name,
                "content": json.dumps(result.to_dict(), ensure_ascii=False),
            })

    error = "Agent exceeded the maximum number of steps."
    LOGS.add(error, "ERROR")
    return AgentRunResult("", conversation, max_steps, total_tool_calls, False, error=error)
