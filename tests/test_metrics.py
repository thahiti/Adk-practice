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
