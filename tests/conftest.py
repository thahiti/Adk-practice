"""테스트 공통 설정."""

from __future__ import annotations

import os
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


@pytest.fixture(scope="session", autouse=True)
def register_metrics() -> None:
    """커스텀 메트릭을 ADK 레지스트리에 등록한다.

    `AgentEvaluator` 는 커스텀 메트릭을 자동 등록하지 않으므로
    평가 실행 전에 반드시 한 번 수행되어야 한다.
    """
    from agents.orchestration_lab.metrics import register_custom_metrics

    register_custom_metrics()


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
