"""모델 백엔드 토글 테스트."""

from __future__ import annotations

import pytest
from google.adk.models.lite_llm import LiteLlm

from agents.orchestration_lab.config import resolve_model

pytestmark = pytest.mark.offline


def test_default_backend_is_vertex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MODEL_BACKEND", raising=False)
    monkeypatch.delenv("VERTEX_MODEL", raising=False)
    assert resolve_model() == "gemini-2.5-flash"


def test_vertex_model_is_overridable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "vertex")
    monkeypatch.setenv("VERTEX_MODEL", "gemini-2.5-pro")
    assert resolve_model() == "gemini-2.5-pro"


def test_openai_backend_returns_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "openai/gpt-4o")
    model = resolve_model()
    assert isinstance(model, LiteLlm)
    assert model.model == "openai/gpt-4o"


def test_unknown_backend_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "bedrock")
    with pytest.raises(ValueError, match="Unknown MODEL_BACKEND"):
        resolve_model()
