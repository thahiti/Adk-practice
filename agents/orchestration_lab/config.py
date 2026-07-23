"""모델 백엔드 토글.

에이전트 배선은 백엔드와 무관하게 동일하고, 여기서 주입하는 모델 값만 바뀐다.
오케스트레이션은 ReAct(관찰-행동 반복) 단일 방식이다.

이전에는 `ORCHESTRATION_MODE` 토글로 `PlanReActPlanner` 를 붙일 수 있었으나
제거했다. 해당 플래너의 프롬프트 프로토콜(/*PLANNING*/ 텍스트 태그 + 코드
스타일 액션)은 Gemini 의 텍스트/함수호출 혼합 응답 관행을 전제하며, OpenAI
모델은 계획 텍스트만 내고 툴을 호출하지 않아 위임이 0회로 끝나는 것을
실측으로 확인했다.
"""

from __future__ import annotations

import os

from google.adk.models.lite_llm import LiteLlm

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
