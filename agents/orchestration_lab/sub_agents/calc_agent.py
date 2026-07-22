"""산술 전담 서브에이전트."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ..config import resolve_model
from ..schemas import CalcRequest, NumericResult
from ..tools.arithmetic import calculate

calc_agent = LlmAgent(
    name="calc_agent",
    model=resolve_model(),
    description=(
        "두 수에 산술 연산을 적용한다. "
        "add, subtract, multiply, divide, power 를 지원한다."
    ),
    instruction=(
        "너는 산술 계산 전담 에이전트다.\n"
        "입력은 left, right, operation 을 담은 JSON이다.\n"
        "반드시 calculate 툴을 호출해 계산하라. 직접 암산하지 마라.\n"
        "결과는 value 필드 하나를 가진 JSON으로 반환하라."
    ),
    tools=[calculate],
    input_schema=CalcRequest,
    output_schema=NumericResult,
)
