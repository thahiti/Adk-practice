"""루트와 서브에이전트 사이의 위임 계약.

`AgentTool` 은 서브에이전트의 `input_schema` 를 그대로 함수 선언으로
변환한다. 스키마가 없으면 위임 파라미터가 `{"request": str}` 자유 텍스트
하나로 격하되어 인자 단위 평가가 불가능해진다.

연산 필드를 `Literal` 로 제약하는 이유도 같다. 모델이 "average" 나 "평균"
같은 변형을 쓰지 못하게 막아야 실제 모델 환경에서도 인자 비교가 성립한다.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

CalcOperation = Literal["add", "subtract", "multiply", "divide", "power"]

Conversion = Literal[
    "km_to_mile",
    "mile_to_km",
    "kg_to_pound",
    "pound_to_kg",
    "celsius_to_fahrenheit",
    "fahrenheit_to_celsius",
]

StatsOperation = Literal["mean", "median", "stdev", "min", "max"]


class CalcRequest(BaseModel):
    """산술 연산 위임 요청."""

    left: float = Field(description="왼쪽 피연산자")
    right: float = Field(description="오른쪽 피연산자")
    operation: CalcOperation = Field(description="적용할 산술 연산")


class ConvertRequest(BaseModel):
    """단위 변환 위임 요청."""

    value: float = Field(description="변환할 값")
    conversion: Conversion = Field(description="적용할 단위 변환")


class StatsRequest(BaseModel):
    """통계 연산 위임 요청."""

    values: list[float] = Field(min_length=1, description="대상 숫자 목록")
    operation: StatsOperation = Field(description="적용할 통계 연산")


class NumericResult(BaseModel):
    """세 서브에이전트가 공통으로 반환하는 결과."""

    value: float = Field(description="계산 결과")
