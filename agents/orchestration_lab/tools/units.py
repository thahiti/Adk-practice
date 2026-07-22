"""단위 변환 툴."""

from __future__ import annotations

from typing import Callable, Final

_KM_PER_MILE: Final[float] = 1.609344
_KG_PER_POUND: Final[float] = 0.45359237

_CONVERSIONS: Final[dict[str, Callable[[float], float]]] = {
    "km_to_mile": lambda value: value / _KM_PER_MILE,
    "mile_to_km": lambda value: value * _KM_PER_MILE,
    "kg_to_pound": lambda value: value / _KG_PER_POUND,
    "pound_to_kg": lambda value: value * _KG_PER_POUND,
    "celsius_to_fahrenheit": lambda value: value * 9 / 5 + 32,
    "fahrenheit_to_celsius": lambda value: (value - 32) * 5 / 9,
}


def convert(value: float, conversion: str) -> float:
    """값을 지정한 단위로 변환한다.

    Args:
        value: 변환할 값.
        conversion: km_to_mile, mile_to_km, kg_to_pound, pound_to_kg,
            celsius_to_fahrenheit, fahrenheit_to_celsius 중 하나.

    Returns:
        변환 결과.

    Raises:
        ValueError: 지원하지 않는 변환인 경우.
    """
    converter = _CONVERSIONS.get(conversion)
    if converter is None:
        raise ValueError(f"Unsupported conversion: {conversion}")
    return float(converter(value))
