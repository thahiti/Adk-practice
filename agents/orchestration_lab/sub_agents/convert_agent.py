"""단위 변환 전담 서브에이전트."""

from __future__ import annotations

from google.adk.agents import LlmAgent

from ..config import resolve_model
from ..schemas import ConvertRequest, NumericResult
from ..tools.units import convert

convert_agent = LlmAgent(
    name="convert_agent",
    model=resolve_model(),
    description=(
        "값의 단위를 변환한다. 길이(km/mile), 무게(kg/pound), "
        "온도(celsius/fahrenheit) 를 지원한다."
    ),
    instruction=(
        "너는 단위 변환 전담 에이전트다.\n"
        "입력은 value 와 conversion 을 담은 JSON이다.\n"
        "반드시 convert 툴을 호출해 계산하라. 직접 암산하지 마라.\n"
        "결과는 value 필드 하나를 가진 JSON으로 반환하라."
    ),
    tools=[convert],
    input_schema=ConvertRequest,
    output_schema=NumericResult,
)
