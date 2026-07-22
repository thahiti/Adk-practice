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
