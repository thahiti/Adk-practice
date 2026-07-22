# ADK Orchestration Lab — 설계 문서

- **작성일:** 2026-07-22
- **대상 버전:** `google-adk[eval]==1.36.1`
- **상태:** 승인됨

---

## 1. 목적

ADK 1.36.1에서 **멀티 에이전트 위임(delegation)을 정량 평가**하는 레퍼런스 랩을 만든다.
도메인은 의도적으로 얇게 유지하고, 오케스트레이션과 평가 하네스에 복잡도를 집중시킨다.

결과물은 실제 도메인으로 갈아끼울 수 있는 템플릿이다.

### 충족할 요구사항

| # | 요구사항 | 충족 방식 |
|---|---|---|
| 1 | 3개 서브에이전트, 각각 별도 영역 | `calc_agent` / `convert_agent` / `stats_agent` |
| 2 | 한 요청에 여러 서브에이전트 호출 필요 | 다중홉 eval 케이스 + ReAct/Plan-Execute 토글 |
| 3 | 네트워크 없는 상황에서 동작 테스트 | 모든 툴이 순수 함수, socket 차단 테스트로 강제 |
| 4 | 위임과 위임 파라미터 평가 | 커스텀 메트릭(이름만) + 내장 메트릭(이름+인자) 2축 분리 채점 |

### 비목표

- 실제 외부 서비스 연동 (DB, HTTP API, 파일 I/O)
- 프로덕션 배포, 인증, 멀티 유저
- ADK 2.x 마이그레이션

---

## 2. 전제 조건

- **LLM:** 두 백엔드를 모두 지원한다 — Vertex AI `gemini-2.5-flash`, OpenAI(`LiteLlm`)
- **툴의 외부 연동:** 없음
- "오프라인 테스트"란 *툴이 외부 API에 의존하지 않는다*는 뜻이며, LLM을 mock으로 대체한다는 뜻이 아니다. 모든 동작과 평가는 실제 모델로 수행한다.

이 전제에서 파생되는 핵심 제약: **모델이 비결정론적이므로 평가는 반복 실행 + 임계값 기반이어야 한다.**

### GCP 의존 범위

`gcloud` 인증(ADC)이 필요한 곳은 **Vertex 백엔드의 모델 호출 단 한 곳**이다. 평가 하네스 전체가 GCP에 의존하지 않는다 (F15). 따라서 OpenAI 백엔드를 선택하면 GCP 없이 전 계층이 동작한다.

---

## 3. 검증된 ADK 1.36.1 사실

설계의 근거. 모두 소스 확인 또는 실제 실행으로 검증했다.

| # | 사실 | 근거 |
|---|---|---|
| F1 | `AgentTool`은 서브에이전트에 `input_schema`가 있으면 그 필드를 함수 파라미터로 노출하고, 없으면 `{"request": str}` 단일 자유 텍스트로 격하한다 | `tools/agent_tool.py:143` `_get_declaration()` |
| F2 | `TrajectoryEvaluator`는 `actual.name != expected.name or actual.args != expected.args`로 **인자까지** 비교한다 | `evaluation/trajectory_evaluator.py:240` |
| F3 | `output_schema`와 `tools`를 **함께** 쓸 수 있다 (구버전 제약 해소됨) | `agents/llm_agent.py:342` docstring |
| F4 | `AgentTool.run_async`는 별도 `Runner` + 독립 `InMemorySessionService()`로 서브에이전트를 격리 실행하고, 부모 세션에는 `state_delta`와 **마지막 content만** 전달한다. 서브에이전트 내부 툴 호출은 부모 트레이스에 남지 않는다 | `tools/agent_tool.py:203-290` |
| F5 | `test_config.json`은 `.test.json`과 **같은 폴더**에서만 탐색된다 (상위로 올라가지 않음) | `evaluation/agent_evaluator.py` `find_config_for_test_file()` |
| F6 | **`EXACT`/`IN_ORDER`/`ANY_ORDER` 세 매치 타입 모두 `args`를 비교한다.** matchType은 *추가 호출 허용*과 *순서 완화*만 조절하며, 인자 비교를 건너뛰는 옵션은 없다 | `trajectory_evaluator.py:166-268` 세 메서드 모두 `actual.args == expected.args` 포함 |
| F7 | `agent_loader.list_agents()`는 `agents_dir`의 **모든 비숨김 하위 디렉토리를 앱으로 간주**한다 | `cli/utils/agent_loader.py:364` |
| F8 | ADK 자체 통합 테스트는 `num_runs=4`를 쓰며, 주석에 "helps us manage the variances"라 명시 | `tests/integration/` |
| F9 | `PlanReActPlanner`가 내장되어 있다 | `planners/__init__.py` |
| F10 | 커스텀 메트릭은 `test_config.json`의 `customMetrics`로 선언하고, 함수는 `(eval_metric, actual_invocations, expected_invocations, scenario) -> EvaluationResult` 시그니처를 갖는다 | `evaluation/custom_metric_evaluator.py` |
| F11 | 커스텀 메트릭은 **레지스트리에 사전 등록이 필요**하며, 그 등록은 `adk eval` CLI 경로에만 있고 `AgentEvaluator`에는 없다. 다만 `AgentEvaluator` → `LocalEvalService` → `DEFAULT_METRIC_EVALUATOR_REGISTRY`(모듈 싱글톤)이므로 테스트 코드에서 직접 등록하면 반영된다 | `cli/cli_tools_click.py:933`, `local_eval_service.py:129`. **실행 검증 완료** |
| F12 | 평가 모듈은 `eval` extra를 요구한다 (`pandas` 등). `google-adk`만 설치하면 `metric_evaluator_registry` import가 실패한다 | 실행 검증 완료 |
| F13 | `AgentEvaluator`는 `num_runs` 전체에 걸친 **점수 평균**을 criteria threshold와 비교해 합격을 판정한다. 평가기가 반환한 `overall_eval_status`는 이 판정에 사용되지 않고 `score`만 쓰인다. 따라서 threshold는 곧 **반복 통과율의 하한**이다 | `agent_evaluator.py:664-698` `_process_metrics_and_get_failures()` |
| F14 | `_CustomMetricEvaluator`는 커스텀 함수 호출 직전에 `eval_metric.threshold = None`으로 덮어쓴다. 커스텀 함수는 threshold를 읽을 수 없다 | `custom_metric_evaluator.py:60` |
| F15 | **평가 계층 전체가 GCP 비의존이다.** `response_match_score`는 ROUGE 기반이며(`response_evaluator.py:83-89` → `RougeEvaluator`), Vertex를 타는 것은 설계에서 쓰지 않는 `response_evaluation_score`(COHERENCE)뿐이다. 커스텀 메트릭 레지스트리 등록과 ROUGE 채점을 ADC 없이 실행해 확인했다 | 실행 검증 완료 |
| F16 | `LiteLlm`은 `parameters_json_schema`를 처리하므로(`lite_llm.py:1488`) `input_schema` 기반 위임 파라미터가 OpenAI tool 스펙으로 정상 변환된다. `output_schema`도 지원되며 `contributing/samples/litellm_structured_output/` 공식 샘플이 있다 | 소스 + 샘플 확인 |
| F17 | `PlanReActPlanner`는 프롬프트 기반이라 모델 비종속이다 — *"this planner does not require the model to support built-in thinking features"* | `planners/plan_re_act_planner.py:35` |
| F18 | ADK 1.36.1은 `litellm>=1.83.7,<=1.83.14`로 상한을 의도적으로 고정한다. 그러나 `eval` extra가 전이 의존으로 1.85.7을 끌어오므로, LiteLlm을 쓰려면 **명시적으로 핀을 다시 걸어야** 한다 | `pyproject.toml:127` "bump deliberately. See #5488" |

**F1 + F2 + F4가 설계의 토대다.** 서브에이전트에 `input_schema`를 주면 위임 파라미터가 타입 있는 인자로 노출되고(F1), 트레이스에는 위임 호출만 깨끗이 남으며(F4), 평가기가 인자까지 비교한다(F2).

**F6이 평가 설계를 결정한다.** 내장 메트릭만으로는 "라우팅 축"과 "파라미터 축"을 분리할 수 없으므로 커스텀 메트릭이 필요하다(F10, F11).

---

## 4. 아키텍처

```
root_agent  (LlmAgent, gemini-2.5-flash, planner 토글)
├── AgentTool(calc_agent)      산술
├── AgentTool(convert_agent)   단위 변환
└── AgentTool(stats_agent)     통계
```

`AgentTool` 방식을 채택한 이유는 루트가 제어권을 유지해 다중홉 연쇄가 자연스럽고, 위임이 타입 있는 함수 호출로 트레이스에 남기 때문이다.

**`sub_agents` + `transfer_to_agent` 방식은 채택하지 않는다.** 위임 파라미터가 `agent_name` 하나뿐이라 요구사항 4의 "위임 파라미터" 축을 평가할 대상이 없고, ADK 1.x에서 transfer는 루트로 자동 복귀하지 않아 다중홉이 어색하다. 비교군으로 README에만 기록한다.

### 서브에이전트 공통 구조

각 서브에이전트는 세 가지를 모두 갖는다 (F3):

- `input_schema` — 루트가 넘기는 위임 파라미터 (타입 고정)
- `tools` — 실제 계산을 수행하는 순수 함수
- `output_schema` — 루트에 돌려주는 결과 (타입 고정)

LLM이 직접 산술하지 않고 반드시 툴을 거치게 한다.

---

## 5. 위임 계약

`schemas.py`에 정의한다. **모든 연산 필드는 `Literal`로 제약**한다 — 모델이 `"average"`, `"평균"` 같은 변형을 쓰지 못하게 막아야 인자 비교가 성립한다.

```python
from typing import Literal
from pydantic import BaseModel, Field


class CalcRequest(BaseModel):
    """산술 연산 위임 요청."""
    left: float
    right: float
    operation: Literal["add", "subtract", "multiply", "divide", "power"]


class ConvertRequest(BaseModel):
    """단위 변환 위임 요청."""
    value: float
    conversion: Literal[
        "km_to_mile", "mile_to_km",
        "kg_to_pound", "pound_to_kg",
        "celsius_to_fahrenheit", "fahrenheit_to_celsius",
    ]


class StatsRequest(BaseModel):
    """통계 연산 위임 요청."""
    values: list[float] = Field(min_length=1)
    operation: Literal["mean", "median", "stdev", "min", "max"]


class NumericResult(BaseModel):
    """세 서브에이전트가 공통으로 반환하는 결과."""
    value: float
```

숫자 인자는 파이썬 dict 비교에서 `3 == 3.0`이 참이므로 부동소수점 표기 차이가 자동 흡수된다. `Literal`과 숫자만으로 스키마를 구성한 것은 이 성질을 노린 것이다.

### 툴 시그니처

`tools/` 아래 순수 함수. 표준 라이브러리 `math` / `statistics`만 사용한다.

| 모듈 | 함수 | 비고 |
|---|---|---|
| `arithmetic.py` | `calculate(left: float, right: float, operation: str) -> float` | `divide` 시 0 나눗셈은 `ValueError` |
| `units.py` | `convert(value: float, conversion: str) -> float` | 변환 계수는 모듈 상수 |
| `statistics_ops.py` | `aggregate(values: list[float], operation: str) -> float` | `stdev`는 표본 2개 미만 시 `ValueError` |

---

## 6. 두 개의 토글

배선을 바꾸지 않고 `config.py`가 주입하는 값 두 개만 교체한다. 에이전트 구조, 위임 계약, 평가 하네스는 어느 조합에서도 동일하다.

### 6.1 오케스트레이션 모드

| `ORCHESTRATION_MODE` | 설정 | 의미 |
|---|---|---|
| `react` (기본) | `planner=None` | 계획 없이 관찰-행동 반복 |
| `plan_execute` | `planner=PlanReActPlanner()` | 계획 선언 후 실행 (F9) |

`PlanReActPlanner`는 프롬프트 기반이라 두 모델 백엔드 모두에서 동일하게 동작한다 (F17).

### 6.2 모델 백엔드

| `MODEL_BACKEND` | 설정 | 인증 |
|---|---|---|
| `vertex` (기본) | `model="gemini-2.5-flash"` | ADC 필요 |
| `openai` | `model=LiteLlm(model="openai/gpt-4o")` | `OPENAI_API_KEY` |

`LiteLlm` 경로가 `input_schema`/`output_schema`를 온전히 지원하므로(F16) 위임 파라미터 평가가 두 백엔드에서 동일하게 성립한다.

```python
# config.py
import os
from google.adk.models.lite_llm import LiteLlm
from google.adk.planners import BasePlanner, PlanReActPlanner

ModelLike = str | LiteLlm


def resolve_model() -> ModelLike:
    """MODEL_BACKEND에 따라 모델을 결정한다."""
    backend = os.environ.get("MODEL_BACKEND", "vertex")
    if backend == "vertex":
        return os.environ.get("VERTEX_MODEL", "gemini-2.5-flash")
    if backend == "openai":
        return LiteLlm(model=os.environ.get("OPENAI_MODEL", "openai/gpt-4o"))
    raise ValueError(f"Unknown MODEL_BACKEND: {backend}")


def resolve_planner() -> BasePlanner | None:
    """ORCHESTRATION_MODE에 따라 플래너를 결정한다."""
    mode = os.environ.get("ORCHESTRATION_MODE", "react")
    if mode == "react":
        return None
    if mode == "plan_execute":
        return PlanReActPlanner()
    raise ValueError(f"Unknown ORCHESTRATION_MODE: {mode}")
```

`resolve_model()`은 루트와 세 서브에이전트 모두에 같은 값을 주입한다.

### 6.3 측정 대상

두 토글의 곱으로 4개 조합이 생기고, 각 조합마다 `delegation_route_score`와 `tool_trajectory_avg_score` 두 점수가 나온다. 이 표를 채우는 것이 랩의 산출물이다.

| | `react` | `plan_execute` |
|---|---|---|
| **`vertex`** (gemini-2.5-flash) | route / trajectory | route / trajectory |
| **`openai`** (gpt-4o) | route / trajectory | route / trajectory |

**검증할 가설 두 가지**

1. 다중홉에서 중간 결과를 다음 위임의 인자로 넘겨야 할 때 `plan_execute`가 `react`보다 파라미터 정확도가 높다.
2. 라우팅 정확도는 두 모델이 비슷하지만, 파라미터 정확도에서는 차이가 벌어진다.

두 가설 모두 틀릴 수 있다. 틀렸다는 사실 자체가 유효한 측정 결과다.

---

## 7. 오프라인 보장 (요구사항 3)

툴이 순수 함수라는 사실을 문서로 주장하지 않고 **테스트로 강제**한다.

`tests/conftest.py`에 `socket.socket`을 monkeypatch해 모든 연결을 차단하는 fixture를 둔다. 툴 레이어 테스트는 이 fixture 안에서 실행되므로, 누군가 나중에 툴에 HTTP 호출을 추가하면 테스트가 깨진다.

pytest 마커로 두 계층을 분리한다:

| 마커 | 의미 | 자격증명 |
|---|---|---|
| `offline` | socket 차단 상태로 실행. 툴 순수성 검증 | 불필요 |
| `requires_model` | 실제 모델 호출. 평가 계층 | `MODEL_BACKEND`에 따라 ADC 또는 `OPENAI_API_KEY` |

```bash
uv run pytest -m offline           # 네트워크 없이 즉시 실행
uv run pytest -m requires_model    # 모델 자격증명 필요
```

`requires_model`은 백엔드에 따라 요구 조건이 달라지므로, `conftest.py`가 선택된 백엔드의 자격증명 유무를 확인해 없으면 skip한다. 평가 하네스 자체는 GCP에 의존하지 않으므로(F15) OpenAI 백엔드에서는 GCP 없이 전 계층이 돈다.

---

## 8. 평가 설계 (요구사항 4)

### 3계층

| 계층 | 대상 | 방법 | LLM |
|---|---|---|---|
| L1 | 툴 순수 함수 | pytest 직접 호출 | 불필요 |
| L2 | **위임 라우팅 + 파라미터** | 커스텀 + 내장 메트릭 2종 | 필요 |
| L3 | 최종 응답 | `response_match_score` | 필요 |

L2가 요구사항 4의 본체다.

### 두 축 분리 — 커스텀 메트릭이 필요한 이유

F6에 따라 내장 `tool_trajectory_avg_score`는 **어떤 matchType으로도 인자 비교를 건너뛸 수 없다.** matchType은 추가 호출 허용과 순서 완화만 조절한다. 따라서 "올바른 에이전트를 골랐는가"만 따로 보려면 커스텀 메트릭을 직접 작성해야 한다.

두 메트릭을 **하나의 `test_config.json`에 나란히** 둔다.

```jsonc
{
  "criteria": {
    "delegation_route_score": 1.0,
    "tool_trajectory_avg_score": { "threshold": 0.75, "matchType": "EXACT" },
    "response_match_score": { "threshold": 0.5 }
  },
  "customMetrics": {
    "delegation_route_score": {
      "codeConfig": { "name": "agents.orchestration_lab.metrics.delegation_route_score" },
      "description": "위임 대상 에이전트의 호출 순서만 비교 (인자 무시)"
    }
  }
}
```

F13에 따라 threshold는 **`num_runs` 반복 통과율의 하한**이다. 값을 이렇게 정한 근거:

| 메트릭 | threshold | 근거 |
|---|---|---|
| `delegation_route_score` | `1.0` | 라우팅은 쉬운 과제다. 4회 모두 올바른 에이전트를 골라야 한다 |
| `tool_trajectory_avg_score` | `0.75` | 인자 정확도는 어려운 과제다. 4회 중 3회 통과를 최소 기준으로 둔다 |
| `response_match_score` | `0.5` | 최종 문장은 표현 편차가 크므로 느슨하게 둔다 |

| 메트릭 | 비교 대상 | 답하는 질문 |
|---|---|---|
| `delegation_route_score` (커스텀) | 툴 **이름 시퀀스만** | 올바른 에이전트를 올바른 순서로 불렀나? |
| `tool_trajectory_avg_score` (내장, EXACT) | 툴 이름 **+ 인자** | 넘긴 파라미터까지 정확한가? |

같은 eval 케이스에 두 점수가 나란히 나오므로 진단이 즉시 가능하다. `route=1.0, trajectory=0.5`면 "라우팅은 완벽한데 인자 전달이 틀렸다"는 뜻이고, 이는 다중홉에서 중간 결과 전달 실패를 정확히 가리킨다.

### 커스텀 메트릭 구현

`agents/orchestration_lab/metrics.py`:

```python
from typing import Optional

from google.adk.evaluation.eval_case import ConversationScenario, Invocation
from google.adk.evaluation.eval_metrics import EvalMetric
from google.adk.evaluation.evaluator import (
    EvalStatus, EvaluationResult, PerInvocationResult,
)


def _tool_names(invocation: Optional[Invocation]) -> list[str]:
    """Invocation에서 툴 호출 이름 시퀀스를 뽑는다."""
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

    합격 판정은 AgentEvaluator가 test_config.json의 threshold로 수행하므로
    (F13) 여기서는 점수만 정확히 채운다. eval_metric.threshold는 호출 직전
    None으로 덮어써지므로 읽지 않는다 (F14).
    """
    expected = expected_invocations or []
    results: list[PerInvocationResult] = [
        PerInvocationResult(
            actual_invocation=actual,
            expected_invocation=exp,
            score=1.0 if _tool_names(actual) == _tool_names(exp) else 0.0,
            eval_status=(
                EvalStatus.PASSED
                if _tool_names(actual) == _tool_names(exp)
                else EvalStatus.FAILED
            ),
        )
        for actual, exp in zip(actual_invocations, expected)
    ]

    overall = sum(r.score for r in results) / len(results) if results else None
    return EvaluationResult(
        overall_score=overall,
        overall_eval_status=(
            EvalStatus.NOT_EVALUATED if overall is None
            else EvalStatus.PASSED if overall == 1.0
            else EvalStatus.FAILED
        ),
        per_invocation_results=results,
    )
```

### 커스텀 메트릭 등록 (F11)

`AgentEvaluator`는 커스텀 메트릭을 자동 등록하지 않는다. `tests/conftest.py`에서 세션 스코프로 직접 등록한다.

```python
import pytest
from google.adk.cli.cli_eval import get_default_metric_info
from google.adk.evaluation.custom_metric_evaluator import _CustomMetricEvaluator
from google.adk.evaluation.metric_evaluator_registry import (
    DEFAULT_METRIC_EVALUATOR_REGISTRY,
)


@pytest.fixture(scope="session", autouse=True)
def register_custom_metrics() -> None:
    """커스텀 메트릭을 ADK 기본 레지스트리에 등록한다 (F11)."""
    DEFAULT_METRIC_EVALUATOR_REGISTRY.register_evaluator(
        get_default_metric_info(
            "delegation_route_score",
            "위임 대상 에이전트의 호출 순서만 비교",
        ),
        _CustomMetricEvaluator,
    )
```

### eval 케이스 포맷

ADK 실제 포맷을 그대로 사용한다. F4에 의해 트레이스에는 위임 호출만 남으므로 `tool_uses`에 서브에이전트 이름만 나열한다.

```jsonc
{
  "eval_set_id": "multi_hop",
  "name": "multi_hop",
  "eval_cases": [{
    "eval_id": "mean_then_c2f",
    "conversation": [{
      "invocation_id": "inv-001",
      "user_content": {
        "role": "user",
        "parts": [{ "text": "12, 15, 21의 평균을 구하고 그 값을 섭씨에서 화씨로 바꿔줘" }]
      },
      "intermediate_data": {
        "tool_uses": [
          { "name": "stats_agent",   "args": { "values": [12, 15, 21], "operation": "mean" } },
          { "name": "convert_agent", "args": { "value": 16.0, "conversion": "celsius_to_fahrenheit" } }
        ],
        "intermediate_responses": []
      },
      "final_response": { "role": "model", "parts": [{ "text": "60.8" }] }
    }],
    "session_input": null
  }]
}
```

`AgentTool`이 서브에이전트 이름을 툴 이름으로 사용하므로(`super().__init__(name=agent.name, ...)`) `name` 필드가 곧 "어느 에이전트에 위임했나"이다.

### 케이스 목록

**`single_hop.test.json`** — 단일 위임 3건

| eval_id | 입력 | 기대 위임 |
|---|---|---|
| `stats_only` | "12, 15, 21의 평균을 구해줘" | `stats_agent(values=[12,15,21], operation="mean")` |
| `convert_only` | "섭씨 25도를 화씨로 바꿔줘" | `convert_agent(value=25.0, conversion="celsius_to_fahrenheit")` |
| `calc_only` | "7의 3승을 계산해줘" | `calc_agent(left=7.0, right=3.0, operation="power")` |

**`multi_hop.test.json`** — 다중 위임 2건

| eval_id | 입력 | 기대 위임 순서 (인자 포함) |
|---|---|---|
| `mean_then_c2f` | "12, 15, 21의 평균을 구하고 그 값을 섭씨에서 화씨로 바꿔줘" | `stats_agent(values=[12,15,21], operation="mean")` → `convert_agent(value=16.0, conversion="celsius_to_fahrenheit")` |
| `max_mul_km2mile` | "3, 5, 10의 최댓값에 2를 곱하고 그 결과를 km에서 마일로 바꿔줘" | `stats_agent(values=[3,5,10], operation="max")` → `calc_agent(left=10.0, right=2.0, operation="multiply")` → `convert_agent(value=20.0, conversion="km_to_mile")` |

기대 정답: `mean([12,15,21]) = 16.0`, `16 × 9/5 + 32 = 60.8` / `max = 10`, `10 × 2 = 20`, `20 km ≈ 12.4274 mile`.

### 비결정론 처리

`num_runs=4`로 반복 실행한다 (F8, ADK 자체 통합 테스트와 동일).

F13에 따라 판정은 자동으로 통과율 기반이 된다 — `AgentEvaluator`가 4회 실행의 점수 평균을 threshold와 비교하므로, `tool_trajectory_avg_score: 0.75`는 "4회 중 3회 이상 인자까지 정확해야 한다"는 의미가 된다. 별도의 통계 처리 코드를 작성할 필요가 없다.

`tool_trajectory_avg_score`가 반복적으로 실패하면 그것은 테스트 버그가 아니라 **측정 결과**로 기록한다 — `gemini-2.5-flash`가 다중홉에서 중간 결과를 정확히 전달하지 못한다는 사실 자체가 이 랩의 산출물이다.

---

## 9. 디렉토리 구조

ADK 샘플 규약을 따른다. F7 때문에 에이전트 패키지는 전용 `agents/` 디렉토리 안에 두어야 한다 — `tests/`와 같은 레벨에 두면 `adk web`이 `tests`를 앱으로 착각한다.

```
demo_project/
├── pyproject.toml                          # name: adk-orchestration-lab
├── README.md
├── .env.example                            # Vertex 설정 템플릿
│
├── agents/
│   ├── __init__.py                         # agent_module 경로 확보용
│   └── orchestration_lab/                  # 디렉토리명 = 앱 이름
│       ├── __init__.py                     # from . import agent
│       ├── agent.py                        # root_agent  ← ADK 발견 진입점
│       ├── main.py                         # 단독 실행 스크립트
│       ├── config.py                       # 모델 백엔드 + 플래너 토글
│       ├── schemas.py                      # 위임 계약
│       ├── metrics.py                      # delegation_route_score
│       ├── sub_agents/
│       │   ├── __init__.py
│       │   ├── calc_agent.py
│       │   ├── convert_agent.py
│       │   └── stats_agent.py
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── arithmetic.py
│       │   ├── units.py
│       │   └── statistics_ops.py
│       └── test_files/                     # ADK eval 규약 (F5)
│           ├── test_config.json
│           ├── single_hop.test.json
│           └── multi_hop.test.json
│
├── docs/superpowers/specs/                 # 본 문서
│
└── tests/
    ├── conftest.py                         # socket 차단, 커스텀 메트릭 등록, 마커
    ├── test_tools.py                       # L1
    ├── test_no_network.py                  # 요구 3 강제
    └── test_delegation_eval.py             # L2/L3
```

`sub_agents/`, `tools/`, `test_files/`는 `agents/` 직속이 아니라 앱 패키지 **내부**이므로 앱으로 오인되지 않는다.

---

## 10. 실행 방법

```bash
cp .env.example .env

# Vertex 백엔드를 쓸 경우에만 필요
gcloud auth application-default login

# 대화형 디버깅 — 트레이스에서 위임을 눈으로 확인
adk web agents

# CLI 실행
adk run agents/orchestration_lab

# 오프라인 검증 (모델 인증 불필요)
uv run pytest -m offline

# 위임 평가
uv run pytest -m requires_model

# 4개 조합 측정
for backend in vertex openai; do
  for mode in react plan_execute; do
    MODEL_BACKEND=$backend ORCHESTRATION_MODE=$mode uv run pytest -m requires_model
  done
done
```

평가는 `AgentEvaluator.evaluate(agent_module="agents.orchestration_lab", eval_dataset_file_path_or_dir=..., num_runs=4)` 형태로 호출한다.

`requires_model` 마커는 백엔드에 따라 필요한 자격증명이 다르므로, `conftest.py`가 `MODEL_BACKEND`를 보고 해당 자격증명이 없으면 skip 처리한다.

### `.env.example`

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

### 의존성

```
google-adk[eval]==1.36.1
litellm>=1.83.7,<=1.83.14
```

`eval` extra는 평가 모듈이 `pandas` 등을 요구하므로 필수다 (F12). `litellm` 핀은 F18 때문에 명시적으로 걸어야 한다 — `eval` extra가 전이 의존으로 ADK 검증 범위를 벗어난 버전을 끌어온다.

---

## 11. 리스크

| 리스크 | 영향 | 대응 |
|---|---|---|
| **모델 자격증명 미설정** | L2/L3 실행 불가 | Vertex는 `gcloud auth application-default login`, OpenAI는 `OPENAI_API_KEY`. 둘 중 하나만 있으면 되며, 없는 쪽은 `conftest.py`가 skip 처리한다. L1과 오프라인 계층은 무관하게 선행 가능 |
| **모델별 threshold 편차** | 한쪽 백엔드 기준으로 잡은 threshold가 다른 쪽에서 부당하게 실패 | threshold는 두 백엔드 공통으로 두되, 목적이 합격/불합격 게이트가 아니라 **비교 측정**임을 명시한다. 조합별 점수를 README 표에 기록하는 것이 산출물이고, 실패 자체가 결과다 |
| **litellm 버전 드리프트** | `eval` extra가 ADK 검증 범위 밖 버전을 끌어옴 (F18) | `pyproject.toml`에 `litellm>=1.83.7,<=1.83.14` 명시적 핀. 설치 후 `uv pip list`로 확인 |
| **ADK 비공개 API 의존** | 마이너 업그레이드 시 파손 가능 | 커스텀 메트릭 등록이 `_CustomMetricEvaluator`(private)와 `google.adk.cli.cli_eval.get_default_metric_info`(CLI 내부)에 의존한다. 버전을 1.36.1로 고정하고, `conftest.py` 한 곳에 격리해 파손 지점을 좁힌다 |
| 모델이 다중홉에서 중간 결과를 잘못 전달 | `tool_trajectory_avg_score` 하락 | 실패가 아니라 측정 결과로 기록. `plan_execute` 모드와 비교하는 것이 실험 목적 |
| `AgentTool` 격리 실행(F4)으로 서브에이전트가 대화 맥락을 못 봄 | 맥락 의존 질의 처리 불가 | 본 랩의 스코프에서는 제약이 아니라 이점 — 위임 인자만으로 동작해야 평가가 성립 |
| 반복 실행으로 인한 테스트 시간 증가 | CI 지연 | `num_runs=4` 유지, 마커로 분리해 빠른 피드백 경로 확보 |

---

## 12. 완료 기준

- [ ] `adk web agents`로 루트 에이전트가 뜨고 세 서브에이전트로 위임하는 것이 트레이스에서 확인된다
- [ ] `uv run pytest -m offline`이 네트워크 없이 통과한다
- [ ] 툴에 HTTP 호출을 임의로 추가하면 `test_no_network.py`가 실패한다
- [ ] `delegation_route_score`와 `tool_trajectory_avg_score`가 각각 독립된 점수로 리포트된다
- [ ] `MODEL_BACKEND=openai`에서 GCP 자격증명 없이 L1~L3 전 계층이 실행된다
- [ ] 4개 조합(백엔드 2 × 오케스트레이션 2)의 두 점수가 README에 비교표로 기록된다
