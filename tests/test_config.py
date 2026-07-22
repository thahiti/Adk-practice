"""모델 백엔드와 플래너 토글 테스트."""

from __future__ import annotations

import pytest
from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import PlanReActPlanner

from agents.orchestration_lab.config import resolve_model, resolve_planner

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


def test_default_mode_is_react(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORCHESTRATION_MODE", raising=False)
    assert resolve_planner() is None


def test_plan_execute_returns_planner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCHESTRATION_MODE", "plan_execute")
    assert isinstance(resolve_planner(), PlanReActPlanner)


def test_unknown_mode_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCHESTRATION_MODE", "tree_of_thought")
    with pytest.raises(ValueError, match="Unknown ORCHESTRATION_MODE"):
        resolve_planner()
