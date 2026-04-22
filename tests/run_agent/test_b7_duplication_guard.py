import sys
import types
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

sys.modules.setdefault("fire", types.SimpleNamespace(Fire=lambda *a, **k: None))
sys.modules.setdefault("firecrawl", types.SimpleNamespace(Firecrawl=object))
sys.modules.setdefault("fal_client", types.SimpleNamespace())

import run_agent
from agent.output_guards import apply_adjacent_data_text_duplication_guard


def _patch_agent_bootstrap(monkeypatch):
    monkeypatch.setattr(
        run_agent,
        "get_tool_definitions",
        lambda **kwargs: [
            {
                "type": "function",
                "function": {
                    "name": "terminal",
                    "description": "Run shell commands.",
                    "parameters": {"type": "object", "properties": {}},
                },
            }
        ],
    )
    monkeypatch.setattr(run_agent, "check_toolset_requirements", lambda: {})


def _build_agent(monkeypatch, *, model="gpt-5-codex"):
    _patch_agent_bootstrap(monkeypatch)
    agent = run_agent.AIAgent(
        model=model,
        base_url="https://chatgpt.com/backend-api/codex",
        api_key="codex-token",
        quiet_mode=True,
        max_iterations=2,
        skip_context_files=True,
        skip_memory=True,
    )
    agent.client = MagicMock()
    return agent


def _codex_response(*parts):
    return SimpleNamespace(
        output=[
            SimpleNamespace(
                type="message",
                status="completed",
                content=list(parts),
            )
        ],
        usage=SimpleNamespace(input_tokens=5, output_tokens=3, total_tokens=8),
        status="completed",
        model="gpt-5-codex",
    )


def _data_part(payload):
    return SimpleNamespace(type="data", name="pipeline_status", data=payload)


def _text_part(text):
    return SimpleNamespace(type="output_text", text=text)


def test_b7_positive_keeps_non_matching_adjacent_text(monkeypatch):
    response = _codex_response(
        _data_part({"plan_id": "plan_001", "status": "ready"}),
        _text_part("ready to proceed"),
    )

    apply_adjacent_data_text_duplication_guard(response.output)

    content = response.output[0].content
    assert [part.type for part in content] == ["data", "output_text"]
    assert content[1].text == "ready to proceed"


def test_b7_hit_deletes_duplicate_text_and_keeps_data_at_normalize_hook(monkeypatch):
    agent = _build_agent(monkeypatch)
    response = _codex_response(
        _data_part({"status": "done", "plan_id": "plan_001"}),
        _text_part("done"),
    )

    assistant_message, finish_reason = agent._normalize_codex_response(response)

    content = response.output[0].content
    assert finish_reason == "stop"
    assert assistant_message.content == ""
    assert len(content) == 1
    assert content[0].type == "data"
    assert content[0].data["status"] == "done"


def test_b7_running_boundary_does_not_substring_match(monkeypatch):
    agent = _build_agent(monkeypatch)
    response = _codex_response(
        _data_part({"status": "running"}),
        _text_part("running late"),
    )

    assistant_message, _ = agent._normalize_codex_response(response)

    content = response.output[0].content
    assert [part.type for part in content] == ["data", "output_text"]
    assert assistant_message.content == "running late"


def test_b7_plan_001_token_boundary_requires_exact_match(monkeypatch):
    agent = _build_agent(monkeypatch)
    response = _codex_response(
        _data_part({"plan_id": "plan_001"}),
        _text_part("plan_0012"),
    )

    assistant_message, _ = agent._normalize_codex_response(response)

    content = response.output[0].content
    assert [part.type for part in content] == ["data", "output_text"]
    assert assistant_message.content == "plan_0012"


def test_b7_plan_001_token_boundary_matches_standalone_token(monkeypatch):
    agent = _build_agent(monkeypatch)
    response = _codex_response(
        SimpleNamespace(
            type="data",
            name="plan_compare",
            data={"plans": [{"planId": "plan_001"}]},
        ),
        _text_part("plan_001 已就绪"),
    )

    assistant_message, _ = agent._normalize_codex_response(response)

    content = response.output[0].content
    assert len(content) == 1
    assert content[0].type == "data"
    assert assistant_message.content == ""


def test_system_prompt_includes_b7_exact_rule(monkeypatch):
    agent = _build_agent(monkeypatch)

    prompt = agent._build_system_prompt()

    assert "B7" in prompt
    assert "exact field value" in prompt
    assert "substring-match" in prompt
