"""위임 계약 스키마 테스트."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from agents.orchestration_lab.schemas import (
    CalcRequest,
    ConvertRequest,
    NumericResult,
    StatsRequest,
)

pytestmark = pytest.mark.offline


def test_stats_request_accepts_valid_operation() -> None:
    request = StatsRequest(values=[12, 15, 21], operation="mean")
    assert request.values == [12.0, 15.0, 21.0]
    assert request.operation == "mean"


def test_stats_request_rejects_freeform_operation() -> None:
    """Literal 제약이 없으면 exact 비교가 성립하지 않는다."""
    with pytest.raises(ValidationError):
        StatsRequest(values=[1, 2], operation="average")


def test_stats_request_rejects_empty_values() -> None:
    with pytest.raises(ValidationError):
        StatsRequest(values=[], operation="mean")


def test_calc_request_rejects_unknown_operation() -> None:
    with pytest.raises(ValidationError):
        CalcRequest(left=1, right=2, operation="modulo")


def test_convert_request_rejects_unknown_conversion() -> None:
    with pytest.raises(ValidationError):
        ConvertRequest(value=1, conversion="km_to_lightyear")


def test_numeric_result_coerces_int_to_float() -> None:
    assert NumericResult(value=16).value == 16.0


def test_schemas_produce_json_schema_with_enum() -> None:
    """AgentTool이 이 JSON 스키마로 함수 선언을 만든다."""
    schema = StatsRequest.model_json_schema()
    operation = schema["properties"]["operation"]
    assert set(operation["enum"]) == {"mean", "median", "stdev", "min", "max"}
