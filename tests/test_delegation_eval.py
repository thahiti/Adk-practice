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
