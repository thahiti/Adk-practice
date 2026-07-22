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
