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
from google.adk.evaluation.eval_case import (
    ConversationScenario,
    Invocation,
    get_all_tool_calls,
)
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

    `intermediate_data` 는 `IntermediateData`(eval 셋의 기대값)와
    `InvocationEvents`(실제 런타임 결과) 두 타입의 Union 이다. 전자는
    `tool_uses` 를 직접 갖지만 후자는 이벤트 목록 안에 function_call 이
    흩어져 있다. ADK 의 `get_all_tool_calls` 헬퍼가 두 타입을 모두 처리하며,
    내장 `TrajectoryEvaluator` 도 같은 헬퍼를 쓴다.

    Args:
        invocation: 대상 invocation. None 이면 빈 목록을 돌려준다.

    Returns:
        호출 순서대로의 툴 이름 목록.
    """
    if invocation is None:
        return []
    return [call.name for call in get_all_tool_calls(invocation.intermediate_data)]


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

    `actual_invocations` 와 `expected` 의 길이가 다르면 `zip` 이 짧은 쪽
    기준으로 잘라내므로, 점수 합을 `len(results)` 가 아니라
    `max(len(actual_invocations), len(expected))` 로 나눈다. 이렇게 하면
    누락되거나 초과된 invocation 이 점수를 희석시켜, 조기 종료한 에이전트가
    실제보다 높은 점수를 받는 일을 막는다. `PerInvocationResult` 는
    `actual_invocation` 이 필수 필드라 짝이 없는 invocation 에 대해서는
    결과 행 자체를 만들 수 없기 때문에, 분모만 조정하는 방식을 쓴다.

    Args:
        eval_metric: 메트릭 정보. threshold 는 신뢰할 수 없다.
        actual_invocations: 실제 실행 결과.
        expected_invocations: 기대값. None 이면 평가하지 않는다.
        conversation_scenario: 사용하지 않는다.

    Returns:
        invocation 별 점수와 그 평균을 담은 결과.
    """
    expected = expected_invocations or []

    if not expected:
        return EvaluationResult(
            overall_score=None,
            overall_eval_status=EvalStatus.NOT_EVALUATED,
            per_invocation_results=[],
        )

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

    denominator = max(len(actual_invocations), len(expected))
    overall = sum(result.score for result in results) / denominator
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
