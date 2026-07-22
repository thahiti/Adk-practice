"""통계 연산 툴."""

from __future__ import annotations

import statistics
from typing import Callable, Final

_AGGREGATIONS: Final[dict[str, Callable[[list[float]], float]]] = {
    "mean": statistics.fmean,
    "median": statistics.median,
    "stdev": statistics.stdev,
    "min": min,
    "max": max,
}


def aggregate(values: list[float], operation: str) -> float:
    """숫자 목록에 통계 연산을 적용한다.

    Args:
        values: 대상 숫자 목록. 비어 있으면 안 된다.
        operation: mean, median, stdev, min, max 중 하나.

    Returns:
        연산 결과.

    Raises:
        ValueError: 목록이 비었거나, 지원하지 않는 연산이거나,
            표본이 2개 미만인 상태로 stdev를 요청한 경우.
    """
    if not values:
        raise ValueError("values must not be empty")
    aggregation = _AGGREGATIONS.get(operation)
    if aggregation is None:
        raise ValueError(f"Unsupported operation: {operation}")
    if operation == "stdev" and len(values) < 2:
        raise ValueError("stdev requires at least two values")
    return float(aggregation(values))
