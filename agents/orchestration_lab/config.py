"""모델 백엔드와 오케스트레이션 모드 토글.

에이전트 배선은 어느 조합에서도 동일하고, 여기서 주입하는 두 값만 바뀐다.
백엔드 2종 × 오케스트레이션 2종 = 4개 조합이 랩의 측정 대상이다.
"""

from __future__ import annotations

import os

from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import BasePlanner, PlanReActPlanner

ModelLike = str | LiteLlm

_DEFAULT_VERTEX_MODEL = "gemini-2.5-flash"
_DEFAULT_OPENAI_MODEL = "openai/gpt-4o"


def resolve_model() -> ModelLike:
    """`MODEL_BACKEND` 에 따라 모델을 결정한다.

    Returns:
        vertex 백엔드면 모델명 문자열, openai 백엔드면 `LiteLlm` 인스턴스.

    Raises:
        ValueError: 알 수 없는 백엔드인 경우.
    """
    backend = os.environ.get("MODEL_BACKEND", "vertex")
    if backend == "vertex":
        return os.environ.get("VERTEX_MODEL", _DEFAULT_VERTEX_MODEL)
    if backend == "openai":
        return LiteLlm(
            model=os.environ.get("OPENAI_MODEL", _DEFAULT_OPENAI_MODEL)
        )
    raise ValueError(f"Unknown MODEL_BACKEND: {backend}")


def resolve_planner() -> BasePlanner | None:
    """`ORCHESTRATION_MODE` 에 따라 플래너를 결정한다.

    `PlanReActPlanner` 는 프롬프트 기반이라 두 모델 백엔드 모두에서
    동일하게 동작한다.

    Returns:
        react 모드면 None, plan_execute 모드면 `PlanReActPlanner`.

    Raises:
        ValueError: 알 수 없는 모드인 경우.
    """
    mode = os.environ.get("ORCHESTRATION_MODE", "react")
    if mode == "react":
        return None
    if mode == "plan_execute":
        return PlanReActPlanner()
    raise ValueError(f"Unknown ORCHESTRATION_MODE: {mode}")
