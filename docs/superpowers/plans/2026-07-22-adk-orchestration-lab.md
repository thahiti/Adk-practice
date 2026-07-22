# ADK Orchestration Lab Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ADK 1.36.1에서 3개 서브에이전트로의 위임과 위임 파라미터를 실제 모델로 정량 측정하는 레퍼런스 랩을 만든다.

**Architecture:** 루트 `LlmAgent`가 세 서브에이전트를 `AgentTool`로 감싸 도구처럼 호출한다. 각 서브에이전트는 `input_schema`를 선언해 위임 파라미터를 타입 있는 함수 인자로 노출하고, 실제 계산은 순수 함수 툴이 수행한다. 평가는 툴 이름만 보는 커스텀 메트릭과 이름+인자를 보는 내장 메트릭 두 축으로 나눠 채점한다.

**Tech Stack:** Python 3.13, uv, `google-adk[eval]==1.36.1`, litellm(OpenAI 백엔드용), pytest + pytest-asyncio, Pydantic v2

**설계 문서:** `docs/superpowers/specs/2026-07-22-adk-orchestration-lab-design.md`

## Global Constraints

- ADK 버전은 `google-adk[eval]==1.36.1`로 고정한다. `eval` extra 없이는 평가 모듈이 `pandas` 부재로 import 실패한다.
- `litellm`은 `>=1.83.7,<=1.83.14`로 명시적으로 핀을 건다. ADK가 의도적으로 상한을 고정했는데 `eval` extra가 전이 의존으로 그 위 버전을 끌어온다.
- 모든 툴은 **순수 함수**여야 한다. 외부 API, 파일 I/O, 네트워크 접근 금지. 표준 라이브러리만 사용한다.
- 서브에이전트의 연산 필드는 반드시 `Literal`로 제약한다. 자유 문자열을 허용하면 위임 파라미터 exact 비교가 성립하지 않는다.
- 에이전트 앱 패키지는 `agents/` 디렉토리 **안에** 둔다. `adk web`의 `list_agents()`가 대상 디렉토리의 모든 하위 디렉토리를 앱으로 간주하기 때문이다.
- `test_config.json`은 대응하는 `.test.json`과 **같은 폴더**에 둔다. ADK는 상위 폴더로 탐색하지 않는다.
- 타입힌트는 엄밀하게, docstring은 Google 스타일로 작성한다. 변수·함수는 snake_case, 클래스는 PascalCase.
- 커밋은 Conventional Commits 형식을 따르고 논리적 단위로 쪼갠다.

---

### Task 1: 프로젝트 스캐폴드와 pytest 설정

**Files:**
- Modify: `pyproject.toml`
- Create: `.env.example`
- Create: `agents/__init__.py`
- Delete: `main.py` (uv init 보일러플레이트)

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `agents` 패키지 경로 — 이후 모든 태스크가 `agents.orchestration_lab.*`로 import한다. pytest 마커 `offline`, `requires_model`. pytest `asyncio_mode = "auto"`와 `pythonpath = ["."]`.

`pythonpath = ["."]`가 중요하다. `AgentEvaluator.evaluate(agent_module="agents.orchestration_lab")`가 dotted 모듈 경로로 import하므로 프로젝트 루트가 `sys.path`에 있어야 한다.

- [ ] **Step 1: `pyproject.toml` 수정**

프로젝트 이름을 도메인 검토 시절 흔적인 `adk-triage-lab`에서 바꾸고, pytest 설정을 추가한다.

```toml
[project]
name = "adk-orchestration-lab"
version = "0.1.0"
description = "ADK 1.36.1 멀티 에이전트 위임 평가 레퍼런스 랩"
readme = "README.md"
requires-python = ">=3.13"
dependencies = [
    "google-adk[eval]==1.36.1",
    "litellm>=1.83.7,<=1.83.14",
]

[dependency-groups]
dev = [
    "pytest>=9.1.1",
    "pytest-asyncio>=1.4.0",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
pythonpath = ["."]
testpaths = ["tests"]
markers = [
    "offline: 네트워크가 차단된 상태에서 실행되는 테스트",
    "requires_model: 실제 모델 호출이 필요한 테스트",
]
```

- [ ] **Step 2: 잠금 파일 갱신**

Run: `uv lock`
Expected: 성공. 프로젝트 이름 변경만 반영되고 의존성 해석 결과는 동일하다.

- [ ] **Step 3: `.env.example` 생성**

```
# 토글
MODEL_BACKEND=vertex           # vertex | openai
ORCHESTRATION_MODE=react       # react | plan_execute

# MODEL_BACKEND=vertex 일 때
GOOGLE_GENAI_USE_VERTEXAI=TRUE
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-central1
VERTEX_MODEL=gemini-2.5-flash

# MODEL_BACKEND=openai 일 때
OPENAI_API_KEY=sk-...
OPENAI_MODEL=openai/gpt-4o
# OPENAI_API_BASE=https://internal-proxy/v1   # 사내 OpenAI 호환 엔드포인트를 쓸 경우
```

- [ ] **Step 4: `agents/__init__.py` 생성**

```python
"""ADK 에이전트 앱 패키지 디렉토리.

`adk web agents` 가 가리키는 대상이며, 각 하위 디렉토리가 하나의 앱이다.
`AgentEvaluator` 가 `agents.orchestration_lab` 형태의 dotted 경로로
import 할 수 있도록 패키지로 만들어 둔다.
"""
```

- [ ] **Step 5: uv 보일러플레이트 제거**

Run: `rm main.py`
Expected: 성공. 이 프로젝트의 진입점은 `agents/orchestration_lab/main.py`이다.

- [ ] **Step 6: 마커 등록 확인**

Run: `uv run pytest --markers | head -5`
Expected: 출력에 `@pytest.mark.offline`과 `@pytest.mark.requires_model`이 보인다.

- [ ] **Step 7: 커밋**

```bash
git add pyproject.toml uv.lock .env.example agents/__init__.py
git rm --cached main.py 2>/dev/null; rm -f main.py
git add -A
git commit -m "chore: configure pytest markers and agents package layout"
```

---

### Task 2: 순수 함수 툴 3종

**Files:**
- Create: `agents/orchestration_lab/__init__.py`
- Create: `agents/orchestration_lab/tools/__init__.py`
- Create: `agents/orchestration_lab/tools/arithmetic.py`
- Create: `agents/orchestration_lab/tools/units.py`
- Create: `agents/orchestration_lab/tools/statistics_ops.py`
- Test: `tests/test_tools.py`

**Interfaces:**
- Consumes: Task 1의 `agents` 패키지, pytest 마커
- Produces:
  - `calculate(left: float, right: float, operation: str) -> float`
  - `convert(value: float, conversion: str) -> float`
  - `aggregate(values: list[float], operation: str) -> float`

  세 함수 모두 지원하지 않는 연산명에 `ValueError`를 던진다. Task 6의 서브에이전트가 이 함수들을 툴로 등록한다.

`agents/orchestration_lab/__init__.py`는 ADK 규약상 `from . import agent`를 담아야 하지만, `agent.py`는 Task 7에서 만든다. 이 태스크에서는 docstring만 두고 Task 7에서 import 문을 추가한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_tools.py`:

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_tools.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.orchestration_lab'`

- [ ] **Step 3: 패키지 초기화 파일 생성**

`agents/orchestration_lab/__init__.py`:

```python
"""ADK 오케스트레이션 랩 에이전트 앱.

Task 7에서 `from . import agent` 를 추가해 ADK 발견 규약을 완성한다.
"""
```

`agents/orchestration_lab/tools/__init__.py`:

```python
"""서브에이전트가 사용하는 순수 함수 툴.

외부 의존이 전혀 없어야 한다. 네트워크·파일 I/O·전역 상태를 쓰지 않으며,
이 제약은 `tests/test_no_network.py` 가 강제한다.
"""
```

- [ ] **Step 4: 산술 툴 구현**

`agents/orchestration_lab/tools/arithmetic.py`:

```python
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
```

- [ ] **Step 5: 단위 변환 툴 구현**

`agents/orchestration_lab/tools/units.py`:

```python
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
```

- [ ] **Step 6: 통계 툴 구현**

`agents/orchestration_lab/tools/statistics_ops.py`:

```python
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
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `uv run pytest tests/test_tools.py -q`
Expected: PASS — 20개 전후의 테스트가 모두 통과한다.

- [ ] **Step 8: 커밋**

```bash
git add agents/orchestration_lab/__init__.py agents/orchestration_lab/tools tests/test_tools.py
git commit -m "feat(tools): add arithmetic, unit conversion and statistics tools"
```

---

### Task 3: 네트워크 차단 가드

**Files:**
- Create: `tests/conftest.py`
- Create: `tests/test_no_network.py`

**Interfaces:**
- Consumes: Task 2의 `calculate`, `convert`, `aggregate`
- Produces: `no_network` pytest fixture — 소켓 생성·연결·DNS 조회를 모두 차단한다. Task 8의 메트릭 테스트도 이 fixture를 쓴다.

이 태스크의 산출물은 "툴이 순수 함수"라는 주장을 **실행 가능한 제약**으로 바꾸는 것이다. 누가 나중에 툴에 HTTP 호출을 넣으면 테스트가 깨진다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_no_network.py`:

```python
"""요구사항 3 강제: 툴 계층은 네트워크 없이 동작해야 한다."""

from __future__ import annotations

import socket

import pytest

from agents.orchestration_lab.tools.arithmetic import calculate
from agents.orchestration_lab.tools.statistics_ops import aggregate
from agents.orchestration_lab.tools.units import convert

pytestmark = pytest.mark.offline


def test_guard_blocks_socket_creation(no_network: None) -> None:
    """가드 자체가 동작하는지 먼저 확인한다."""
    with pytest.raises(RuntimeError, match="네트워크 접근이 차단"):
        socket.socket()


def test_guard_blocks_connection(no_network: None) -> None:
    with pytest.raises(RuntimeError, match="네트워크 접근이 차단"):
        socket.create_connection(("example.com", 80))


def test_guard_blocks_dns(no_network: None) -> None:
    with pytest.raises(RuntimeError, match="네트워크 접근이 차단"):
        socket.getaddrinfo("example.com", 80)


def test_tools_run_without_network(no_network: None) -> None:
    """세 툴 모두 네트워크가 막힌 상태에서 정상 동작해야 한다."""
    assert calculate(2.0, 3.0, "add") == 5.0
    assert convert(0.0, "celsius_to_fahrenheit") == 32.0
    assert aggregate([12.0, 15.0, 21.0], "mean") == 16.0
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_no_network.py -q`
Expected: FAIL — `fixture 'no_network' not found`

- [ ] **Step 3: conftest 작성**

`tests/conftest.py`:

```python
"""테스트 공통 설정."""

from __future__ import annotations

import socket
from typing import Any, NoReturn

import pytest
from dotenv import load_dotenv

load_dotenv(override=False)


class NetworkBlockedError(RuntimeError):
    """네트워크가 차단된 상태에서 접근이 시도되었다."""


def _blocked(*args: Any, **kwargs: Any) -> NoReturn:
    raise NetworkBlockedError(
        "이 테스트에서는 네트워크 접근이 차단되어 있습니다."
    )


@pytest.fixture
def no_network(monkeypatch: pytest.MonkeyPatch) -> None:
    """소켓 생성·연결·DNS 조회를 모두 차단한다.

    툴 계층이 외부 의존 없이 동작한다는 사실을 강제하기 위한 가드다.
    """
    monkeypatch.setattr(socket, "socket", _blocked)
    monkeypatch.setattr(socket, "create_connection", _blocked)
    monkeypatch.setattr(socket, "getaddrinfo", _blocked)
```

`NetworkBlockedError`는 `RuntimeError`를 상속하므로 테스트의 `pytest.raises(RuntimeError, ...)`가 잡는다.

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_no_network.py -q`
Expected: PASS — 4개 통과.

- [ ] **Step 5: 가드가 실제로 회귀를 잡는지 수동 확인**

`agents/orchestration_lab/tools/arithmetic.py`의 `calculate` 첫 줄에 임시로 아래를 넣는다.

```python
    socket.create_connection(("example.com", 80))
```

(파일 상단에 `import socket`도 임시 추가)

Run: `uv run pytest tests/test_no_network.py::test_tools_run_without_network -q`
Expected: FAIL — 가드가 회귀를 잡아낸다.

확인 후 임시 코드 두 줄을 **반드시 되돌린다.**

Run: `uv run pytest tests/test_no_network.py -q`
Expected: PASS — 원복되었음을 확인.

- [ ] **Step 6: 커밋**

```bash
git add tests/conftest.py tests/test_no_network.py
git commit -m "test: enforce tool layer has no network dependency"
```

---

### Task 4: 위임 계약 스키마

**Files:**
- Create: `agents/orchestration_lab/schemas.py`
- Test: `tests/test_schemas.py`

**Interfaces:**
- Consumes: 없음 (Pydantic만 사용)
- Produces:
  - `CalcRequest(left: float, right: float, operation: Literal[...])`
  - `ConvertRequest(value: float, conversion: Literal[...])`
  - `StatsRequest(values: list[float], operation: Literal[...])`
  - `NumericResult(value: float)`

  Task 6의 서브에이전트가 `input_schema` / `output_schema`로 사용한다.

이 스키마가 설계의 핵심이다. `AgentTool`은 서브에이전트에 `input_schema`가 있으면 그 필드를 함수 파라미터로 노출하고, 없으면 `{"request": str}` 자유 텍스트 하나로 격하한다. `Literal` 제약은 모델이 `"평균"` 같은 변형을 못 쓰게 막아 인자 비교를 성립시킨다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_schemas.py`:

```python
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
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_schemas.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.orchestration_lab.schemas'`

- [ ] **Step 3: 스키마 구현**

`agents/orchestration_lab/schemas.py`:

```python
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
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_schemas.py -q`
Expected: PASS — 7개 통과.

- [ ] **Step 5: 커밋**

```bash
git add agents/orchestration_lab/schemas.py tests/test_schemas.py
git commit -m "feat(schemas): add typed delegation contracts with Literal operations"
```

---

### Task 5: 모델 백엔드와 플래너 토글

**Files:**
- Create: `agents/orchestration_lab/config.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Consumes: 없음
- Produces:
  - `resolve_model() -> str | LiteLlm`
  - `resolve_planner() -> BasePlanner | None`

  Task 6의 서브에이전트와 Task 7의 루트가 둘 다 호출한다.

`resolve_model()`은 모듈 import 시점에 호출되므로, 환경 변수는 에이전트 모듈을 import하기 **전에** 설정되어 있어야 한다. `tests/conftest.py`가 `load_dotenv()`를 최상단에서 수행하는 이유다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_config.py`:

```python
"""모델 백엔드와 플래너 토글 테스트."""

from __future__ import annotations

import pytest
from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import PlanReActPlanner

from agents.orchestration_lab.config import resolve_model, resolve_planner

pytestmark = pytest.mark.offline


def test_default_backend_is_vertex(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MODEL_BACKEND", raising=False)
    monkeypatch.delenv("VERTEX_MODEL", raising=False)
    assert resolve_model() == "gemini-2.5-flash"


def test_vertex_model_is_overridable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "vertex")
    monkeypatch.setenv("VERTEX_MODEL", "gemini-2.5-pro")
    assert resolve_model() == "gemini-2.5-pro"


def test_openai_backend_returns_litellm(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "openai")
    monkeypatch.setenv("OPENAI_MODEL", "openai/gpt-4o")
    model = resolve_model()
    assert isinstance(model, LiteLlm)
    assert model.model == "openai/gpt-4o"


def test_unknown_backend_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MODEL_BACKEND", "bedrock")
    with pytest.raises(ValueError, match="Unknown MODEL_BACKEND"):
        resolve_model()


def test_default_mode_is_react(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("ORCHESTRATION_MODE", raising=False)
    assert resolve_planner() is None


def test_plan_execute_returns_planner(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCHESTRATION_MODE", "plan_execute")
    assert isinstance(resolve_planner(), PlanReActPlanner)


def test_unknown_mode_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("ORCHESTRATION_MODE", "tree_of_thought")
    with pytest.raises(ValueError, match="Unknown ORCHESTRATION_MODE"):
        resolve_planner()
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_config.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.orchestration_lab.config'`

- [ ] **Step 3: config 구현**

`agents/orchestration_lab/config.py`:

```python
"""모델 백엔드와 오케스트레이션 모드 토글.

에이전트 배선은 어느 조합에서도 동일하고, 여기서 주입하는 두 값만 바뀐다.
백엔드 2종 × 오케스트레이션 2종 = 4개 조합이 랩의 측정 대상이다.
"""

from __future__ import annotations

import os

from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import BasePlanner, PlanReActPlanner

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


def resolve_planner() -> BasePlanner | None:
    """`ORCHESTRATION_MODE` 에 따라 플래너를 결정한다.

    `PlanReActPlanner` 는 프롬프트 기반이라 두 모델 백엔드 모두에서
    동일하게 동작한다.

    Returns:
        react 모드면 None, plan_execute 모드면 `PlanReActPlanner`.

    Raises:
        ValueError: 알 수 없는 모드인 경우.
    """
    mode = os.environ.get("ORCHESTRATION_MODE", "react")
    if mode == "react":
        return None
    if mode == "plan_execute":
        return PlanReActPlanner()
    raise ValueError(f"Unknown ORCHESTRATION_MODE: {mode}")
```

- [ ] **Step 4: 테스트 통과 확인**

Run: `uv run pytest tests/test_config.py -q`
Expected: PASS — 7개 통과.

- [ ] **Step 5: 커밋**

```bash
git add agents/orchestration_lab/config.py tests/test_config.py
git commit -m "feat(config): add model backend and planner toggles"
```

---

### Task 6: 서브에이전트 3종

**Files:**
- Create: `agents/orchestration_lab/sub_agents/__init__.py`
- Create: `agents/orchestration_lab/sub_agents/calc_agent.py`
- Create: `agents/orchestration_lab/sub_agents/convert_agent.py`
- Create: `agents/orchestration_lab/sub_agents/stats_agent.py`
- Test: `tests/test_sub_agents.py`

**Interfaces:**
- Consumes: Task 2의 툴 3종, Task 4의 스키마, Task 5의 `resolve_model`
- Produces: `calc_agent`, `convert_agent`, `stats_agent` — 모두 `LlmAgent` 인스턴스. Task 7의 루트가 `AgentTool`로 감싼다.

핵심 검증은 "`AgentTool`로 감쌌을 때 함수 선언이 타입 있는 파라미터를 갖는가"다. 이게 깨지면 위임 파라미터 평가 자체가 성립하지 않는다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_sub_agents.py`:

```python
"""서브에이전트 배선 테스트. 모델 호출은 하지 않는다."""

from __future__ import annotations

import pytest
from google.adk.tools.agent_tool import AgentTool

from agents.orchestration_lab.schemas import NumericResult
from agents.orchestration_lab.sub_agents.calc_agent import calc_agent
from agents.orchestration_lab.sub_agents.convert_agent import convert_agent
from agents.orchestration_lab.sub_agents.stats_agent import stats_agent

pytestmark = pytest.mark.offline

ALL_AGENTS = (stats_agent, convert_agent, calc_agent)


@pytest.mark.parametrize("agent", ALL_AGENTS)
def test_agent_has_input_and_output_schema(agent) -> None:
    """input_schema 가 없으면 위임 파라미터가 자유 텍스트로 격하된다."""
    assert agent.input_schema is not None
    assert agent.output_schema is NumericResult


@pytest.mark.parametrize("agent", ALL_AGENTS)
def test_agent_has_exactly_one_tool(agent) -> None:
    """LLM이 직접 계산하지 않고 반드시 툴을 거치게 한다."""
    assert len(agent.tools) == 1


@pytest.mark.parametrize("agent", ALL_AGENTS)
def test_agent_has_description(agent) -> None:
    """description 은 AgentTool 의 함수 설명이 되므로 비면 안 된다."""
    assert agent.description


def test_agent_names_are_stable() -> None:
    """이 이름이 그대로 eval 셋의 tool_uses[].name 이 된다."""
    assert [agent.name for agent in ALL_AGENTS] == [
        "stats_agent",
        "convert_agent",
        "calc_agent",
    ]


def _declared_parameter_names(agent) -> set[str]:
    """AgentTool 이 노출하는 함수 파라미터 이름을 뽑는다."""
    declaration = AgentTool(agent)._get_declaration()
    if declaration.parameters_json_schema:
        return set(declaration.parameters_json_schema["properties"])
    return set(declaration.parameters.properties)


def test_agent_tool_exposes_typed_parameters() -> None:
    """설계의 핵심: 위임 파라미터가 타입 있는 필드로 노출되어야 한다."""
    assert AgentTool(stats_agent)._get_declaration().name == "stats_agent"
    assert _declared_parameter_names(stats_agent) == {"values", "operation"}
    assert _declared_parameter_names(convert_agent) == {"value", "conversion"}
    assert _declared_parameter_names(calc_agent) == {
        "left",
        "right",
        "operation",
    }


def test_without_input_schema_parameters_degrade_to_free_text() -> None:
    """대조군. 이 설계가 왜 input_schema 를 요구하는지 고정한다.

    스키마를 빼면 위임 파라미터가 `request` 자유 텍스트 하나로 격하되어
    인자 단위 평가가 불가능해진다. 누가 스키마를 제거하면 위 테스트가
    깨지고, 이 테스트가 그 이유를 설명한다.
    """
    from google.adk.agents import LlmAgent

    from agents.orchestration_lab.tools.statistics_ops import aggregate

    bare = LlmAgent(
        name="bare_agent",
        model="gemini-2.5-flash",
        description="스키마 없는 대조군",
        instruction="i",
        tools=[aggregate],
    )

    assert _declared_parameter_names(bare) == {"request"}
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_sub_agents.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.orchestration_lab.sub_agents'`

- [ ] **Step 3: 서브에이전트 패키지 초기화**

`agents/orchestration_lab/sub_agents/__init__.py`:

```python
"""도메인별 전담 서브에이전트.

각 에이전트는 `input_schema` 로 위임 파라미터를 타입으로 고정하고,
실제 계산은 순수 함수 툴에 위임하며, `output_schema` 로 결과를 돌려준다.
"""
```

- [ ] **Step 4: 통계 에이전트 구현**

`agents/orchestration_lab/sub_agents/stats_agent.py`:

```python
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
```

- [ ] **Step 5: 단위 변환 에이전트 구현**

`agents/orchestration_lab/sub_agents/convert_agent.py`:

```python
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
```

- [ ] **Step 6: 산술 에이전트 구현**

`agents/orchestration_lab/sub_agents/calc_agent.py`:

```python
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
```

- [ ] **Step 7: 테스트 통과 확인**

Run: `uv run pytest tests/test_sub_agents.py -q`
Expected: PASS — 12개 통과. 특히 `test_agent_tool_exposes_typed_parameters`와 대조군 `test_without_input_schema_parameters_degrade_to_free_text`가 통과해야 한다. 이 두 테스트가 설계의 토대를 고정한다.

- [ ] **Step 8: 커밋**

```bash
git add agents/orchestration_lab/sub_agents tests/test_sub_agents.py
git commit -m "feat(agents): add calc, convert and stats sub-agents with typed schemas"
```

---

### Task 7: 루트 오케스트레이터

**Files:**
- Create: `agents/orchestration_lab/agent.py`
- Create: `agents/orchestration_lab/main.py`
- Modify: `agents/orchestration_lab/__init__.py`
- Test: `tests/test_root_agent.py`

**Interfaces:**
- Consumes: Task 5의 `resolve_model`/`resolve_planner`, Task 6의 서브에이전트 3종
- Produces: `root_agent` — `agent.py`의 모듈 레벨 변수. `adk web`, `adk run`, `AgentEvaluator` 모두 이 이름으로 발견한다.

루트 instruction이 이 랩의 실질적 변수다. 직접 계산 금지와 중간 결과를 다음 위임의 명시적 숫자 인자로 넘기라는 지시가 다중홉 파라미터 정확도를 좌우한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_root_agent.py`:

```python
"""루트 오케스트레이터 배선 테스트. 모델 호출은 하지 않는다."""

from __future__ import annotations

import pytest
from google.adk.tools.agent_tool import AgentTool

from agents.orchestration_lab.agent import root_agent

pytestmark = pytest.mark.offline


def test_root_agent_wraps_three_sub_agents_as_tools() -> None:
    tool_names = [tool.name for tool in root_agent.tools]
    assert tool_names == ["stats_agent", "convert_agent", "calc_agent"]


def test_root_tools_are_agent_tools() -> None:
    """AgentTool 이어야 루트가 제어권을 유지하며 다중홉을 연쇄할 수 있다."""
    assert all(isinstance(tool, AgentTool) for tool in root_agent.tools)


def test_root_agent_has_no_sub_agents() -> None:
    """transfer_to_agent 경로는 채택하지 않았다."""
    assert root_agent.sub_agents == []


def test_root_agent_is_discoverable_by_adk() -> None:
    """ADK 는 모듈 레벨 `root_agent` 를 찾는다."""
    import agents.orchestration_lab as app

    assert app.agent.root_agent is root_agent


def test_planner_follows_orchestration_mode(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """토글이 실제로 루트에 반영되는지 확인한다."""
    from google.adk.planners import PlanReActPlanner

    from agents.orchestration_lab.config import resolve_planner

    monkeypatch.setenv("ORCHESTRATION_MODE", "plan_execute")
    assert isinstance(resolve_planner(), PlanReActPlanner)
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_root_agent.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.orchestration_lab.agent'`

- [ ] **Step 3: 루트 에이전트 구현**

`agents/orchestration_lab/agent.py`:

```python
"""루트 오케스트레이터.

세 서브에이전트를 `AgentTool` 로 감싸 도구처럼 호출한다. 루트가 제어권을
유지하므로 다중홉 연쇄가 자연스럽고, 각 위임이 타입 있는 인자를 가진 함수
호출로 트레이스에 남아 그대로 평가 대상이 된다.
"""

from __future__ import annotations

from google.adk.agents import LlmAgent
from google.adk.tools.agent_tool import AgentTool

from .config import resolve_model, resolve_planner
from .sub_agents.calc_agent import calc_agent
from .sub_agents.convert_agent import convert_agent
from .sub_agents.stats_agent import stats_agent

_INSTRUCTION = """\
너는 계산 요청을 전담 에이전트에 위임하는 오케스트레이터다.

너에게는 세 개의 도구가 있다.
- stats_agent: 숫자 목록의 통계 (mean, median, stdev, min, max)
- convert_agent: 단위 변환 (길이, 무게, 온도)
- calc_agent: 두 수의 산술 (add, subtract, multiply, divide, power)

규칙:
1. 어떤 계산도 직접 하지 마라. 암산은 금지다. 반드시 도구를 호출하라.
2. 요청이 여러 단계를 필요로 하면 도구를 순서대로 여러 번 호출하라.
3. 앞 단계의 결과를 다음 도구에 넘길 때는, 반환된 value 를 그대로 숫자
   인자로 전달하라. 값을 반올림하거나 다시 계산하지 마라.
4. 모든 단계가 끝나면 최종 숫자만 간결하게 답하라.

예시: "3, 5, 10의 최댓값에 2를 곱해줘" 는 stats_agent 로 max 를 구한 뒤,
그 결과를 calc_agent 의 left 인자로 넘겨 multiply 를 수행한다.
"""

root_agent = LlmAgent(
    name="orchestration_lab",
    model=resolve_model(),
    planner=resolve_planner(),
    description=(
        "산술·단위변환·통계 요청을 전담 서브에이전트에 위임하는 오케스트레이터."
    ),
    instruction=_INSTRUCTION,
    tools=[
        AgentTool(stats_agent),
        AgentTool(convert_agent),
        AgentTool(calc_agent),
    ],
)
```

- [ ] **Step 4: 패키지 초기화 파일에 ADK 규약 추가**

`agents/orchestration_lab/__init__.py` 전체를 아래로 교체한다.

```python
"""ADK 오케스트레이션 랩 에이전트 앱.

`from . import agent` 는 ADK 샘플 규약이다. `adk web` / `adk run` 과
`AgentEvaluator` 가 이 패키지를 import 한 뒤 `agent.root_agent` 를 찾는다.
"""

from . import agent
```

- [ ] **Step 5: 단독 실행 스크립트 구현**

`agents/orchestration_lab/main.py`:

```python
"""단독 실행 스크립트.

Run:
    uv run python -m agents.orchestration_lab.main
"""

from __future__ import annotations

import asyncio

from dotenv import load_dotenv
from google.adk.runners import InMemoryRunner
from google.genai import types

from .agent import root_agent

load_dotenv(override=False)

_PROMPTS = (
    "12, 15, 21의 평균을 구해줘",
    "12, 15, 21의 평균을 구하고 그 값을 섭씨에서 화씨로 바꿔줘",
)


async def main() -> None:
    """샘플 프롬프트를 실행하고 위임 트레이스를 출력한다."""
    app_name = "orchestration_lab"
    user_id = "local_user"
    runner = InMemoryRunner(agent=root_agent, app_name=app_name)
    session = await runner.session_service.create_session(
        app_name=app_name, user_id=user_id
    )

    for prompt in _PROMPTS:
        print(f"\n=== {prompt} ===")
        content = types.Content(
            role="user", parts=[types.Part.from_text(text=prompt)]
        )
        async for event in runner.run_async(
            user_id=user_id, session_id=session.id, new_message=content
        ):
            if not event.content or not event.content.parts:
                continue
            for part in event.content.parts:
                if part.function_call:
                    print(
                        f"  [위임] {part.function_call.name}"
                        f"  args={part.function_call.args}"
                    )
                elif part.text and event.author == root_agent.name:
                    print(f"  [응답] {part.text.strip()}")


if __name__ == "__main__":
    asyncio.run(main())
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `uv run pytest tests/test_root_agent.py -q`
Expected: PASS — 5개 통과.

- [ ] **Step 7: 오프라인 계층 전체 회귀 확인**

Run: `uv run pytest -m offline -q`
Expected: PASS — Task 2~7의 모든 테스트가 통과한다.

- [ ] **Step 8: ADK 앱 발견 확인**

Run: `uv run adk web agents --help`
Expected: 명령이 오류 없이 실행된다. (서버를 실제로 띄우지는 않는다.)

- [ ] **Step 9: 커밋**

```bash
git add agents/orchestration_lab/agent.py agents/orchestration_lab/main.py \
        agents/orchestration_lab/__init__.py tests/test_root_agent.py
git commit -m "feat(agents): add root orchestrator delegating via AgentTool"
```

---

### Task 8: 위임 라우팅 커스텀 메트릭

**Files:**
- Create: `agents/orchestration_lab/metrics.py`
- Modify: `tests/conftest.py`
- Test: `tests/test_metrics.py`

**Interfaces:**
- Consumes: 없음 (ADK 평가 타입만 사용)
- Produces:
  - `delegation_route_score(eval_metric, actual_invocations, expected_invocations, conversation_scenario=None) -> EvaluationResult`
  - `register_custom_metrics() -> None` — conftest의 세션 fixture가 호출한다.

  Task 9의 `test_config.json`이 `agents.orchestration_lab.metrics.delegation_route_score` 경로로 참조한다.

내장 `tool_trajectory_avg_score`는 `EXACT`/`IN_ORDER`/`ANY_ORDER` 어느 매치 타입으로도 인자 비교를 건너뛰지 않는다. 그래서 "올바른 에이전트를 골랐는가"만 따로 보려면 커스텀 메트릭이 필요하다.

두 가지 함정에 주의한다. 첫째, ADK는 커스텀 메트릭을 레지스트리에 **사전 등록**해야 하는데 그 등록 코드가 `adk eval` CLI 경로에만 있고 `AgentEvaluator`에는 없다. 둘째, `_CustomMetricEvaluator`가 함수 호출 직전에 `eval_metric.threshold = None`으로 덮어쓰므로 커스텀 함수는 threshold를 읽을 수 없다. 합격 판정은 `AgentEvaluator`가 `test_config.json`의 threshold로 수행한다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_metrics.py`:

```python
"""위임 라우팅 커스텀 메트릭 테스트. 모델도 네트워크도 필요 없다."""

from __future__ import annotations

import pytest
from google.adk.evaluation.eval_case import IntermediateData, Invocation
from google.adk.evaluation.eval_metrics import EvalMetric
from google.adk.evaluation.evaluator import EvalStatus
from google.genai import types

from agents.orchestration_lab.metrics import delegation_route_score

pytestmark = pytest.mark.offline

_METRIC = EvalMetric(metric_name="delegation_route_score", threshold=1.0)


def _invocation(*calls: tuple[str, dict]) -> Invocation:
    """지정한 툴 호출 시퀀스를 갖는 Invocation 을 만든다."""
    return Invocation(
        user_content=types.Content(
            role="user", parts=[types.Part.from_text(text="q")]
        ),
        intermediate_data=IntermediateData(
            tool_uses=[
                types.FunctionCall(name=name, args=args) for name, args in calls
            ]
        ),
    )


def test_identical_route_scores_one() -> None:
    actual = [_invocation(("stats_agent", {"values": [1.0], "operation": "mean"}))]
    expected = [_invocation(("stats_agent", {"values": [1.0], "operation": "mean"}))]

    result = delegation_route_score(_METRIC, actual, expected)

    assert result.overall_score == 1.0
    assert result.overall_eval_status == EvalStatus.PASSED


def test_ignores_argument_differences() -> None:
    """이 메트릭의 존재 이유: 이름만 맞으면 인자가 달라도 만점이다."""
    actual = [_invocation(("stats_agent", {"values": [9.0], "operation": "max"}))]
    expected = [_invocation(("stats_agent", {"values": [1.0], "operation": "mean"}))]

    assert delegation_route_score(_METRIC, actual, expected).overall_score == 1.0


def test_wrong_agent_scores_zero() -> None:
    actual = [_invocation(("calc_agent", {}))]
    expected = [_invocation(("stats_agent", {}))]

    result = delegation_route_score(_METRIC, actual, expected)

    assert result.overall_score == 0.0
    assert result.overall_eval_status == EvalStatus.FAILED


def test_wrong_order_scores_zero() -> None:
    actual = [_invocation(("convert_agent", {}), ("stats_agent", {}))]
    expected = [_invocation(("stats_agent", {}), ("convert_agent", {}))]

    assert delegation_route_score(_METRIC, actual, expected).overall_score == 0.0


def test_missing_hop_scores_zero() -> None:
    actual = [_invocation(("stats_agent", {}))]
    expected = [_invocation(("stats_agent", {}), ("convert_agent", {}))]

    assert delegation_route_score(_METRIC, actual, expected).overall_score == 0.0


def test_partial_match_averages_across_invocations() -> None:
    actual = [_invocation(("stats_agent", {})), _invocation(("calc_agent", {}))]
    expected = [
        _invocation(("stats_agent", {})),
        _invocation(("convert_agent", {})),
    ]

    assert delegation_route_score(_METRIC, actual, expected).overall_score == 0.5


def test_no_expected_invocations_is_not_evaluated() -> None:
    result = delegation_route_score(_METRIC, [_invocation()], None)

    assert result.overall_score is None
    assert result.overall_eval_status == EvalStatus.NOT_EVALUATED


def test_metric_resolves_through_adk_registry() -> None:
    """등록 헬퍼가 실제로 ADK 레지스트리에 메트릭을 꽂는지 확인한다."""
    from google.adk.evaluation.custom_metric_evaluator import (
        _CustomMetricEvaluator,
    )
    from google.adk.evaluation.eval_config import (
        EvalConfig,
        get_eval_metrics_from_config,
    )
    from google.adk.evaluation.metric_evaluator_registry import (
        DEFAULT_METRIC_EVALUATOR_REGISTRY,
    )

    from agents.orchestration_lab.metrics import register_custom_metrics

    register_custom_metrics()
    config = EvalConfig.model_validate(
        {
            "criteria": {"delegation_route_score": 1.0},
            "customMetrics": {
                "delegation_route_score": {
                    "codeConfig": {
                        "name": (
                            "agents.orchestration_lab.metrics"
                            ".delegation_route_score"
                        )
                    }
                }
            },
        }
    )
    evaluator = DEFAULT_METRIC_EVALUATOR_REGISTRY.get_evaluator(
        get_eval_metrics_from_config(config)[0]
    )

    assert isinstance(evaluator, _CustomMetricEvaluator)
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_metrics.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'agents.orchestration_lab.metrics'`

- [ ] **Step 3: 메트릭 구현**

`agents/orchestration_lab/metrics.py`:

```python
"""위임 라우팅 전용 커스텀 평가 메트릭.

내장 `tool_trajectory_avg_score` 는 EXACT / IN_ORDER / ANY_ORDER 어느
매치 타입으로도 인자 비교를 건너뛰지 않는다. matchType 은 추가 호출 허용과
순서 완화만 조절한다. 따라서 "올바른 에이전트를 골랐는가" 만 격리해서 보려면
툴 이름만 비교하는 메트릭을 직접 만들어야 한다.

이 메트릭과 내장 메트릭을 같은 eval 케이스에 나란히 걸면 두 점수가 함께
나온다. route 는 만점인데 trajectory 가 낮으면 라우팅은 맞았고 인자 전달이
틀렸다는 뜻이다.
"""

from __future__ import annotations

from typing import Optional

from google.adk.cli.cli_eval import get_default_metric_info
from google.adk.evaluation.custom_metric_evaluator import _CustomMetricEvaluator
from google.adk.evaluation.eval_case import ConversationScenario, Invocation
from google.adk.evaluation.eval_metrics import EvalMetric
from google.adk.evaluation.evaluator import (
    EvalStatus,
    EvaluationResult,
    PerInvocationResult,
)
from google.adk.evaluation.metric_evaluator_registry import (
    DEFAULT_METRIC_EVALUATOR_REGISTRY,
)

METRIC_NAME = "delegation_route_score"
METRIC_DESCRIPTION = "위임 대상 에이전트의 호출 순서만 비교 (인자 무시)"


def _tool_names(invocation: Optional[Invocation]) -> list[str]:
    """Invocation 에서 툴 호출 이름 시퀀스를 뽑는다.

    Args:
        invocation: 대상 invocation. None 이면 빈 목록을 돌려준다.

    Returns:
        호출 순서대로의 툴 이름 목록.
    """
    if invocation is None or invocation.intermediate_data is None:
        return []
    return [call.name for call in invocation.intermediate_data.tool_uses]


def delegation_route_score(
    eval_metric: EvalMetric,
    actual_invocations: list[Invocation],
    expected_invocations: Optional[list[Invocation]],
    conversation_scenario: Optional[ConversationScenario] = None,
) -> EvaluationResult:
    """위임 대상 에이전트의 호출 순서만 비교한다. 인자는 무시한다.

    합격 판정은 `AgentEvaluator` 가 `test_config.json` 의 threshold 로
    수행하므로 여기서는 점수만 정확히 채운다. `eval_metric.threshold` 는
    호출 직전 None 으로 덮어써지므로 읽지 않는다.

    Args:
        eval_metric: 메트릭 정보. threshold 는 신뢰할 수 없다.
        actual_invocations: 실제 실행 결과.
        expected_invocations: 기대값. None 이면 평가하지 않는다.
        conversation_scenario: 사용하지 않는다.

    Returns:
        invocation 별 점수와 그 평균을 담은 결과.
    """
    expected = expected_invocations or []
    results: list[PerInvocationResult] = []

    for actual, exp in zip(actual_invocations, expected):
        matched = _tool_names(actual) == _tool_names(exp)
        results.append(
            PerInvocationResult(
                actual_invocation=actual,
                expected_invocation=exp,
                score=1.0 if matched else 0.0,
                eval_status=EvalStatus.PASSED if matched else EvalStatus.FAILED,
            )
        )

    if not results:
        return EvaluationResult(
            overall_score=None,
            overall_eval_status=EvalStatus.NOT_EVALUATED,
            per_invocation_results=[],
        )

    overall = sum(result.score for result in results) / len(results)
    return EvaluationResult(
        overall_score=overall,
        overall_eval_status=(
            EvalStatus.PASSED if overall == 1.0 else EvalStatus.FAILED
        ),
        per_invocation_results=results,
    )


def register_custom_metrics() -> None:
    """커스텀 메트릭을 ADK 기본 레지스트리에 등록한다.

    ADK 는 이 등록을 `adk eval` CLI 경로에서만 수행하고 `AgentEvaluator`
    에서는 하지 않는다. 다만 `AgentEvaluator` → `LocalEvalService` →
    `DEFAULT_METRIC_EVALUATOR_REGISTRY` 로 같은 모듈 싱글톤을 쓰므로
    여기서 등록하면 그대로 반영된다. 여러 번 호출해도 안전하다.
    """
    DEFAULT_METRIC_EVALUATOR_REGISTRY.register_evaluator(
        get_default_metric_info(METRIC_NAME, METRIC_DESCRIPTION),
        _CustomMetricEvaluator,
    )
```

- [ ] **Step 4: conftest에 등록 fixture 추가**

`tests/conftest.py` 하단에 아래를 덧붙인다.

```python
@pytest.fixture(scope="session", autouse=True)
def register_metrics() -> None:
    """커스텀 메트릭을 ADK 레지스트리에 등록한다.

    `AgentEvaluator` 는 커스텀 메트릭을 자동 등록하지 않으므로
    평가 실행 전에 반드시 한 번 수행되어야 한다.
    """
    from agents.orchestration_lab.metrics import register_custom_metrics

    register_custom_metrics()
```

import는 fixture 안에서 한다. 모듈 최상단에서 하면 `agents` 패키지가 `sys.path`에 오르기 전에 실행될 수 있다.

- [ ] **Step 5: 테스트 통과 확인**

Run: `uv run pytest tests/test_metrics.py -q`
Expected: PASS — 8개 통과.

- [ ] **Step 6: 커밋**

```bash
git add agents/orchestration_lab/metrics.py tests/conftest.py tests/test_metrics.py
git commit -m "feat(metrics): add delegation route score isolating routing from arguments"
```

---

### Task 9: eval 셋과 채점 기준

**Files:**
- Create: `agents/orchestration_lab/test_files/test_config.json`
- Create: `agents/orchestration_lab/test_files/single_hop.test.json`
- Create: `agents/orchestration_lab/test_files/multi_hop.test.json`
- Test: `tests/test_eval_sets.py`

**Interfaces:**
- Consumes: Task 6의 에이전트 이름(`stats_agent`, `convert_agent`, `calc_agent`), Task 8의 메트릭 이름
- Produces: `.test.json` 두 개와 `test_config.json`. Task 10의 평가 테스트가 소비한다.

`AgentTool`은 서브에이전트를 별도 `Runner`와 독립 `InMemorySessionService()`로 격리 실행하고 부모 세션에는 마지막 content만 돌려준다. 서브에이전트 내부의 툴 호출은 부모 트레이스에 남지 않으므로, `tool_uses`에는 **위임 호출만** 나열한다.

threshold는 `num_runs` 전체 점수 평균과 비교되므로 곧 반복 통과율의 하한이다.

- [ ] **Step 1: 실패하는 테스트 작성**

`tests/test_eval_sets.py`:

```python
"""eval 셋 JSON 이 ADK 스키마와 설계 기대값에 맞는지 검증한다."""

from __future__ import annotations

import json
import pathlib

import pytest
from google.adk.evaluation.eval_config import EvalConfig
from google.adk.evaluation.eval_set import EvalSet

pytestmark = pytest.mark.offline

EVAL_DIR = (
    pathlib.Path(__file__).parent.parent
    / "agents"
    / "orchestration_lab"
    / "test_files"
)
AGENT_NAMES = {"stats_agent", "convert_agent", "calc_agent"}


def _load(name: str) -> EvalSet:
    return EvalSet.model_validate_json((EVAL_DIR / name).read_text("utf-8"))


@pytest.mark.parametrize("name", ["single_hop.test.json", "multi_hop.test.json"])
def test_eval_set_validates(name: str) -> None:
    assert _load(name).eval_cases


@pytest.mark.parametrize("name", ["single_hop.test.json", "multi_hop.test.json"])
def test_tool_uses_reference_only_sub_agents(name: str) -> None:
    """AgentTool 격리 실행 때문에 트레이스에는 위임 호출만 남는다."""
    for case in _load(name).eval_cases:
        for invocation in case.conversation:
            names = {c.name for c in invocation.intermediate_data.tool_uses}
            assert names <= AGENT_NAMES, f"{case.eval_id}: {names}"


def test_single_hop_cases_have_exactly_one_delegation() -> None:
    for case in _load("single_hop.test.json").eval_cases:
        for invocation in case.conversation:
            assert len(invocation.intermediate_data.tool_uses) == 1


def test_multi_hop_cases_have_multiple_delegations() -> None:
    """요구사항 2: 한 요청이 여러 서브에이전트를 거쳐야 한다."""
    for case in _load("multi_hop.test.json").eval_cases:
        for invocation in case.conversation:
            assert len(invocation.intermediate_data.tool_uses) >= 2


def test_test_config_declares_both_axes() -> None:
    config = EvalConfig.model_validate_json(
        (EVAL_DIR / "test_config.json").read_text("utf-8")
    )
    assert "delegation_route_score" in config.criteria
    assert "tool_trajectory_avg_score" in config.criteria
    assert config.custom_metrics is not None
    assert (
        config.custom_metrics["delegation_route_score"].code_config.name
        == "agents.orchestration_lab.metrics.delegation_route_score"
    )


def test_trajectory_criterion_uses_exact_match() -> None:
    raw = json.loads((EVAL_DIR / "test_config.json").read_text("utf-8"))
    assert raw["criteria"]["tool_trajectory_avg_score"]["matchType"] == "EXACT"
```

- [ ] **Step 2: 실패 확인**

Run: `uv run pytest tests/test_eval_sets.py -q`
Expected: FAIL — `FileNotFoundError` (test_files 디렉토리가 없다)

- [ ] **Step 3: 채점 기준 작성**

`agents/orchestration_lab/test_files/test_config.json`:

```json
{
  "criteria": {
    "delegation_route_score": 1.0,
    "tool_trajectory_avg_score": { "threshold": 0.75, "matchType": "EXACT" },
    "response_match_score": { "threshold": 0.5 }
  },
  "customMetrics": {
    "delegation_route_score": {
      "codeConfig": {
        "name": "agents.orchestration_lab.metrics.delegation_route_score"
      },
      "description": "위임 대상 에이전트의 호출 순서만 비교 (인자 무시)"
    }
  }
}
```

라우팅은 쉬운 과제이므로 4회 모두 맞아야 하고(`1.0`), 인자 정확도는 어려우므로 4회 중 3회를 최소 기준으로 둔다(`0.75`). 최종 문장은 표현 편차가 크므로 느슨하게 둔다(`0.5`).

- [ ] **Step 4: 단일홉 eval 셋 작성**

`agents/orchestration_lab/test_files/single_hop.test.json`:

```json
{
  "eval_set_id": "single_hop",
  "name": "single_hop",
  "eval_cases": [
    {
      "eval_id": "stats_only",
      "conversation": [
        {
          "invocation_id": "single-hop-001",
          "user_content": {
            "role": "user",
            "parts": [{ "text": "12, 15, 21의 평균을 구해줘" }]
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "name": "stats_agent",
                "args": { "values": [12, 15, 21], "operation": "mean" }
              }
            ],
            "intermediate_responses": []
          },
          "final_response": {
            "role": "model",
            "parts": [{ "text": "16.0" }]
          }
        }
      ]
    },
    {
      "eval_id": "convert_only",
      "conversation": [
        {
          "invocation_id": "single-hop-002",
          "user_content": {
            "role": "user",
            "parts": [{ "text": "섭씨 25도를 화씨로 바꿔줘" }]
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "name": "convert_agent",
                "args": { "value": 25, "conversion": "celsius_to_fahrenheit" }
              }
            ],
            "intermediate_responses": []
          },
          "final_response": {
            "role": "model",
            "parts": [{ "text": "77.0" }]
          }
        }
      ]
    },
    {
      "eval_id": "calc_only",
      "conversation": [
        {
          "invocation_id": "single-hop-003",
          "user_content": {
            "role": "user",
            "parts": [{ "text": "7의 3승을 계산해줘" }]
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "name": "calc_agent",
                "args": { "left": 7, "right": 3, "operation": "power" }
              }
            ],
            "intermediate_responses": []
          },
          "final_response": {
            "role": "model",
            "parts": [{ "text": "343.0" }]
          }
        }
      ]
    }
  ]
}
```

- [ ] **Step 5: 다중홉 eval 셋 작성**

`agents/orchestration_lab/test_files/multi_hop.test.json`:

```json
{
  "eval_set_id": "multi_hop",
  "name": "multi_hop",
  "eval_cases": [
    {
      "eval_id": "mean_then_c2f",
      "conversation": [
        {
          "invocation_id": "multi-hop-001",
          "user_content": {
            "role": "user",
            "parts": [
              {
                "text": "12, 15, 21의 평균을 구하고 그 값을 섭씨에서 화씨로 바꿔줘"
              }
            ]
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "name": "stats_agent",
                "args": { "values": [12, 15, 21], "operation": "mean" }
              },
              {
                "name": "convert_agent",
                "args": { "value": 16, "conversion": "celsius_to_fahrenheit" }
              }
            ],
            "intermediate_responses": []
          },
          "final_response": {
            "role": "model",
            "parts": [{ "text": "60.8" }]
          }
        }
      ]
    },
    {
      "eval_id": "max_mul_km2mile",
      "conversation": [
        {
          "invocation_id": "multi-hop-002",
          "user_content": {
            "role": "user",
            "parts": [
              {
                "text": "3, 5, 10의 최댓값에 2를 곱하고 그 결과를 km에서 마일로 바꿔줘"
              }
            ]
          },
          "intermediate_data": {
            "tool_uses": [
              {
                "name": "stats_agent",
                "args": { "values": [3, 5, 10], "operation": "max" }
              },
              {
                "name": "calc_agent",
                "args": { "left": 10, "right": 2, "operation": "multiply" }
              },
              {
                "name": "convert_agent",
                "args": { "value": 20, "conversion": "km_to_mile" }
              }
            ],
            "intermediate_responses": []
          },
          "final_response": {
            "role": "model",
            "parts": [{ "text": "12.427423844746679" }]
          }
        }
      ]
    }
  ]
}
```

- [ ] **Step 6: 테스트 통과 확인**

Run: `uv run pytest tests/test_eval_sets.py -q`
Expected: PASS — 8개 통과.

- [ ] **Step 7: 커밋**

```bash
git add agents/orchestration_lab/test_files tests/test_eval_sets.py
git commit -m "test(eval): add single-hop and multi-hop delegation eval sets"
```

---

### Task 10: 실제 모델 평가 실행

**Files:**
- Create: `tests/test_delegation_eval.py`
- Modify: `tests/conftest.py`

**Interfaces:**
- Consumes: Task 7의 `root_agent`(모듈 경로 `agents.orchestration_lab`), Task 8의 등록 fixture, Task 9의 eval 셋
- Produces: 4개 조합의 측정 결과. Task 11의 README 표를 채운다.

`requires_model` 마커가 붙은 테스트는 선택된 백엔드의 자격증명이 없으면 skip한다. Vertex는 ADC, OpenAI는 `OPENAI_API_KEY`가 필요하다.

- [ ] **Step 1: conftest에 자격증명 skip 로직 추가**

`tests/conftest.py` 하단에 아래를 덧붙인다. `import os`를 파일 상단 import 블록에 추가한다.

```python
def _model_credentials_available() -> bool:
    """선택된 백엔드의 자격증명이 있는지 확인한다."""
    backend = os.environ.get("MODEL_BACKEND", "vertex")
    if backend == "openai":
        return bool(os.environ.get("OPENAI_API_KEY"))
    try:
        import google.auth

        google.auth.default()
    except Exception:
        return False
    return True


def pytest_collection_modifyitems(
    config: pytest.Config, items: list[pytest.Item]
) -> None:
    """모델 자격증명이 없으면 requires_model 테스트를 건너뛴다."""
    if _model_credentials_available():
        return
    backend = os.environ.get("MODEL_BACKEND", "vertex")
    skip = pytest.mark.skip(
        reason=f"MODEL_BACKEND={backend} 자격증명이 없습니다."
    )
    for item in items:
        if "requires_model" in item.keywords:
            item.add_marker(skip)
```

- [ ] **Step 2: 실패하는 테스트 작성**

`tests/test_delegation_eval.py`:

```python
"""실제 모델로 위임과 위임 파라미터를 평가한다.

두 메트릭이 함께 채점된다.
- delegation_route_score: 올바른 에이전트를 올바른 순서로 불렀는가
- tool_trajectory_avg_score: 넘긴 인자까지 정확한가

threshold 는 num_runs 전체 점수 평균과 비교되므로 곧 반복 통과율의 하한이다.
"""

from __future__ import annotations

import pathlib

import pytest
from google.adk.evaluation.agent_evaluator import AgentEvaluator

pytestmark = pytest.mark.requires_model

AGENT_MODULE = "agents.orchestration_lab"
EVAL_DIR = (
    pathlib.Path(__file__).parent.parent
    / "agents"
    / "orchestration_lab"
    / "test_files"
)
NUM_RUNS = 4


async def test_single_hop_delegation() -> None:
    """단일 위임: 세 영역 각각으로 올바르게 라우팅되는가."""
    await AgentEvaluator.evaluate(
        agent_module=AGENT_MODULE,
        eval_dataset_file_path_or_dir=str(EVAL_DIR / "single_hop.test.json"),
        num_runs=NUM_RUNS,
    )


async def test_multi_hop_delegation() -> None:
    """다중 위임: 중간 결과를 다음 위임의 인자로 정확히 넘기는가."""
    await AgentEvaluator.evaluate(
        agent_module=AGENT_MODULE,
        eval_dataset_file_path_or_dir=str(EVAL_DIR / "multi_hop.test.json"),
        num_runs=NUM_RUNS,
    )
```

- [ ] **Step 3: 자격증명 없이 skip 되는지 확인**

Run: `MODEL_BACKEND=openai OPENAI_API_KEY= uv run pytest tests/test_delegation_eval.py -q`
Expected: 2 skipped — 자격증명이 없으면 실패가 아니라 skip이다.

- [ ] **Step 4: 오프라인 계층 회귀 확인**

Run: `uv run pytest -m offline -q`
Expected: PASS — Task 2~9의 모든 테스트가 여전히 통과한다.

- [ ] **Step 5: 실제 모델로 실행**

사용 가능한 백엔드 하나로 실행한다. OpenAI면 `.env`에 `MODEL_BACKEND=openai`와 `OPENAI_API_KEY`를, Vertex면 `gcloud auth application-default login`을 먼저 수행한다.

Run: `uv run pytest tests/test_delegation_eval.py -v`
Expected: 실행이 완료되고 메트릭별 점수가 출력된다. **통과가 목표가 아니다.** `tool_trajectory_avg_score`가 threshold 미만이면 실패 메시지에 `Expected 0.75, but got <실측값>` 형태로 점수가 찍히는데, 그 숫자가 이 랩의 산출물이다.

실패 시 출력 예시:
```
tool_trajectory_avg_score for agents.orchestration_lab Failed. Expected 0.75, but got 0.5.
```

- [ ] **Step 6: 커밋**

```bash
git add tests/conftest.py tests/test_delegation_eval.py
git commit -m "test(eval): evaluate delegation and parameters against real model"
```

---

### Task 11: 측정 결과 문서화

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: Task 10의 실측 점수
- Produces: 없음 (최종 산출물)

- [ ] **Step 1: 4개 조합 측정 실행**

가용한 백엔드에 대해 아래를 실행하고 각 조합의 두 점수를 기록한다. 자격증명이 없는 백엔드는 skip되므로 그 칸은 `미측정`으로 남긴다.

```bash
for backend in vertex openai; do
  for mode in react plan_execute; do
    echo "=== $backend / $mode ==="
    MODEL_BACKEND=$backend ORCHESTRATION_MODE=$mode \
      uv run pytest tests/test_delegation_eval.py -v 2>&1 | tail -20
  done
done
```

- [ ] **Step 2: README 작성**

`README.md` 전체를 아래 구조로 교체하고, 결과표의 값을 Step 1의 실측치로 채운다.

````markdown
# ADK Orchestration Lab

ADK 1.36.1에서 멀티 에이전트 **위임(delegation)을 정량 측정**하는 레퍼런스 랩입니다.
도메인은 의도적으로 얇게 두고 오케스트레이션과 평가 하네스에 복잡도를 집중시켰습니다.

## 구조

```
root_agent (LlmAgent)
├── AgentTool(stats_agent)     통계
├── AgentTool(convert_agent)   단위 변환
└── AgentTool(calc_agent)      산술
```

각 서브에이전트는 `input_schema`를 선언해 위임 파라미터를 타입 있는 함수 인자로
노출합니다. 스키마가 없으면 `AgentTool`이 파라미터를 `{"request": str}` 자유
텍스트 하나로 격하시켜 인자 단위 평가가 불가능해집니다.

## 실행

```bash
cp .env.example .env

adk web agents                     # 대화형 디버깅
uv run pytest -m offline           # 모델 없이 즉시 실행
uv run pytest -m requires_model    # 실제 모델 평가
```

`MODEL_BACKEND`(`vertex` | `openai`)와 `ORCHESTRATION_MODE`(`react` |
`plan_execute`) 두 환경변수로 4개 조합을 전환합니다. gcloud 인증은 Vertex
백엔드에서만 필요하고, 평가 하네스 자체는 GCP에 의존하지 않습니다.

## 평가 축

| 메트릭 | 비교 대상 | 답하는 질문 |
|---|---|---|
| `delegation_route_score` (커스텀) | 툴 이름 시퀀스만 | 올바른 에이전트를 올바른 순서로 불렀나? |
| `tool_trajectory_avg_score` (내장, EXACT) | 툴 이름 + 인자 | 넘긴 파라미터까지 정확한가? |

내장 메트릭은 `EXACT`/`IN_ORDER`/`ANY_ORDER` 어느 매치 타입으로도 인자 비교를
건너뛰지 않기 때문에, 라우팅 축을 격리하려면 커스텀 메트릭이 필요합니다.

## 측정 결과

`num_runs=4`. 점수는 route / trajectory 순.

### 단일홉

| | `react` | `plan_execute` |
|---|---|---|
| **vertex** (gemini-2.5-flash) | _채우기_ | _채우기_ |
| **openai** (gpt-4o) | _채우기_ | _채우기_ |

### 다중홉

| | `react` | `plan_execute` |
|---|---|---|
| **vertex** (gemini-2.5-flash) | _채우기_ | _채우기_ |
| **openai** (gpt-4o) | _채우기_ | _채우기_ |

### 관찰

_실측 후 작성합니다. 최소한 아래 두 가설에 대한 답을 적습니다._

1. 다중홉에서 `plan_execute`가 `react`보다 파라미터 정확도가 높은가?
2. 라우팅 정확도는 두 모델이 비슷하고 파라미터 정확도에서 차이가 벌어지는가?

## 채택하지 않은 대안

`sub_agents` + `transfer_to_agent` 방식은 위임 파라미터가 `agent_name` 하나뿐이라
"무엇을 얼마나 정확히 넘겼는가"를 평가할 대상이 없습니다. ADK 1.x에서 transfer는
제어권이 넘어간 뒤 루트로 자동 복귀하지 않아 다중홉 연쇄에도 불리합니다.

## 설계 문서

`docs/superpowers/specs/2026-07-22-adk-orchestration-lab-design.md`
````

- [ ] **Step 3: 전체 오프라인 회귀 확인**

Run: `uv run pytest -m offline -q`
Expected: PASS

- [ ] **Step 4: 커밋**

```bash
git add README.md
git commit -m "docs: record delegation measurement results"
```

---

## 완료 확인

모든 태스크 완료 후 아래를 확인한다.

- [ ] `uv run pytest -m offline -q` — 모델 없이 전체 통과
- [ ] `agents/orchestration_lab/tools/arithmetic.py`에 네트워크 호출을 임시로 넣으면 `tests/test_no_network.py`가 실패 (확인 후 원복)
- [ ] `adk web agents`로 앱이 뜨고 트레이스에 세 서브에이전트 위임이 보인다
- [ ] `MODEL_BACKEND=openai`에서 GCP 자격증명 없이 전 계층이 실행된다
- [ ] `delegation_route_score`와 `tool_trajectory_avg_score`가 각각 독립된 점수로 출력된다
- [ ] README에 4개 조합의 점수가 기록되어 있다
