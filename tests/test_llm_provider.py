from __future__ import annotations

from src.llm.provider import LLMConfig, llm_enabled, run_completion


def test_llm_disabled_without_key(monkeypatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("DRY_LLM", "0")

    assert llm_enabled() is False
    cfg = LLMConfig(provider="openai", model="gpt-4o-mini", temperature=0.2, top_p=0.95)
    assert run_completion("prompt", cfg) == ""


def test_llm_disabled_with_dry_flag(monkeypatch) -> None:
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("DRY_LLM", "1")

    assert llm_enabled() is False
