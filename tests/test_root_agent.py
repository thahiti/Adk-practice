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


def test_root_agent_has_no_planner() -> None:
    """오케스트레이션은 ReAct 단일 방식이다.

    PlanReActPlanner 는 프롬프트 프로토콜이 Gemini 관행(텍스트 태그 +
    함수호출 혼합 응답)을 전제해 OpenAI 백엔드에서 위임이 0회로 끝나는
    것을 실측 확인 후 제거했다. planner 가 다시 붙으면 이 테스트가 깨진다.
    """
    assert root_agent.planner is None
