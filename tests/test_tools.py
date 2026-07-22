"""툴 계층 단위 테스트. 모델도 네트워크도 필요 없다."""

from __future__ import annotations

import pytest

from agents.orchestration_lab.tools.arithmetic import calculate
from agents.orchestration_lab.tools.statistics_ops import aggregate
from agents.orchestration_lab.tools.units import convert

pytestmark = pytest.mark.offline


@pytest.mark.parametrize(
    ("left", "right", "operation", "expected"),
    [
        (2.0, 3.0, "add", 5.0),
        (10.0, 4.0, "subtract", 6.0),
        (10.0, 2.0, "multiply", 20.0),
        (9.0, 3.0, "divide", 3.0),
        (7.0, 3.0, "power", 343.0),
    ],
)
def test_calculate_supported_operations(
    left: float, right: float, operation: str, expected: float
) -> None:
    assert calculate(left, right, operation) == expected


def test_calculate_rejects_unknown_operation() -> None:
    with pytest.raises(ValueError, match="Unsupported operation"):
        calculate(1.0, 2.0, "modulo")


def test_calculate_rejects_division_by_zero() -> None:
    with pytest.raises(ValueError, match="Division by zero"):
        calculate(1.0, 0.0, "divide")


@pytest.mark.parametrize(
    ("value", "conversion", "expected"),
    [
        (0.0, "celsius_to_fahrenheit", 32.0),
        (25.0, "celsius_to_fahrenheit", 77.0),
        (32.0, "fahrenheit_to_celsius", 0.0),
        (1.609344, "km_to_mile", 1.0),
        (1.0, "mile_to_km", 1.609344),
    ],
)
def test_convert_supported_conversions(
    value: float, conversion: str, expected: float
) -> None:
    assert convert(value, conversion) == pytest.approx(expected)


def test_convert_matches_eval_expectation() -> None:
    """eval 케이스 max_mul_km2mile 의 마지막 단계 정답."""
    assert convert(20.0, "km_to_mile") == pytest.approx(12.427423844746679)


def test_convert_rejects_unknown_conversion() -> None:
    with pytest.raises(ValueError, match="Unsupported conversion"):
        convert(1.0, "km_to_lightyear")


@pytest.mark.parametrize(
    ("values", "operation", "expected"),
    [
        ([12.0, 15.0, 21.0], "mean", 16.0),
        ([1.0, 3.0, 2.0], "median", 2.0),
        ([3.0, 5.0, 10.0], "max", 10.0),
        ([3.0, 5.0, 10.0], "min", 3.0),
        ([2.0, 4.0], "stdev", pytest.approx(1.4142135623730951)),
    ],
)
def test_aggregate_supported_operations(
    values: list[float], operation: str, expected: float
) -> None:
    assert aggregate(values, operation) == expected


def test_aggregate_rejects_empty_values() -> None:
    with pytest.raises(ValueError, match="must not be empty"):
        aggregate([], "mean")


def test_aggregate_rejects_stdev_with_single_value() -> None:
    with pytest.raises(ValueError, match="at least two values"):
        aggregate([1.0], "stdev")


def test_aggregate_rejects_unknown_operation() -> None:
    with pytest.raises(ValueError, match="Unsupported operation"):
        aggregate([1.0, 2.0], "variance")
