"""산술 연산 툴."""

from __future__ import annotations

from typing import Callable, Final

_OPERATIONS: Final[dict[str, Callable[[float, float], float]]] = {
    "add": lambda left, right: left + right,
    "subtract": lambda left, right: left - right,
    "multiply": lambda left, right: left * right,
    "divide": lambda left, right: left / right,
    "power": lambda left, right: left**right,
}


def calculate(left: float, right: float, operation: str) -> float:
    """두 수에 산술 연산을 적용한다.

    Args:
        left: 왼쪽 피연산자.
        right: 오른쪽 피연산자.
        operation: add, subtract, multiply, divide, power 중 하나.

    Returns:
        연산 결과.

    Raises:
        ValueError: 지원하지 않는 연산이거나 0으로 나누는 경우.
    """
    operator = _OPERATIONS.get(operation)
    if operator is None:
        raise ValueError(f"Unsupported operation: {operation}")
    if operation == "divide" and right == 0:
        raise ValueError("Division by zero")
    return float(operator(left, right))
