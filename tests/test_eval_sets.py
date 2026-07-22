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
