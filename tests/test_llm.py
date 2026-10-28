from types import SimpleNamespace as NS

import pytest

from src import llm


def _resp(*blocks):
    return NS(content=list(blocks))


def _fake_client(responses, calls):
    def create(**kw):
        calls.append(kw)
        return responses[len(calls) - 1]
    return NS(messages=NS(create=create))


def test_no_forced_tool_choice_and_retry_on_text(monkeypatch):
    calls = []
    text = NS(type="text", text="Aqui está...")
    tool = NS(type="tool_use", name="registrar", input={"ok": True})
    monkeypatch.setattr(llm, "client", lambda: _fake_client([_resp(text), _resp(tool)], calls))
    out = llm.call_tool("sys", "oi", "registrar", "desc", {"type": "object"})
    assert out == {"ok": True}
    assert all("tool_choice" not in c for c in calls)   # o modelo não aceita tool_choice forçado
    assert len(calls) == 2 and calls[1]["messages"][-1]["role"] == "user"


def test_gives_up_after_rounds(monkeypatch):
    calls = []
    text = NS(type="text", text="sem ferramenta")
    monkeypatch.setattr(llm, "client", lambda: _fake_client([_resp(text)] * 3, calls))
    with pytest.raises(RuntimeError, match="não chamou"):
        llm.call_tool("sys", "oi", "registrar", "desc", {"type": "object"})
