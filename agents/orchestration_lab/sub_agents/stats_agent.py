"""통계 전담 서브에이전트."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ..config import resolve_model
from ..schemas import NumericResult, StatsRequest
from ..tools.statistics_ops import aggregate

stats_agent = LlmAgent(
    name="stats_agent",
    model=resolve_model(),
    description=(
        "숫자 목록에 통계 연산을 적용한다. "
        "mean, median, stdev, min, max 를 지원한다."
    ),
    instruction=(
        "너는 통계 계산 전담 에이전트다.\n"
        "입력은 values 와 operation 을 담은 JSON이다.\n"
        "반드시 aggregate 툴을 호출해 계산하라. 직접 암산하지 마라.\n"
        "결과는 value 필드 하나를 가진 JSON으로 반환하라."
    ),
    tools=[aggregate],
    input_schema=StatsRequest,
    output_schema=NumericResult,
)
