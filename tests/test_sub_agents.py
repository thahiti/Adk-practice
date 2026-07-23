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
