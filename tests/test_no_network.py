"""요구사항 3 강제: 툴 계층은 네트워크 없이 동작해야 한다."""

from __future__ import annotations

import socket

import pytest

from agents.orchestration_lab.tools.arithmetic import calculate
from agents.orchestration_lab.tools.statistics_ops import aggregate
from agents.orchestration_lab.tools.units import convert

pytestmark = pytest.mark.offline


def test_guard_blocks_socket_creation(no_network: None) -> None:
    """가드 자체가 동작하는지 먼저 확인한다."""
    with pytest.raises(RuntimeError, match="네트워크 접근이 차단"):
        socket.socket()


def test_guard_blocks_connection(no_network: None) -> None:
    with pytest.raises(RuntimeError, match="네트워크 접근이 차단"):
        socket.create_connection(("example.com", 80))


def test_guard_blocks_dns(no_network: None) -> None:
    with pytest.raises(RuntimeError, match="네트워크 접근이 차단"):
        socket.getaddrinfo("example.com", 80)


def test_tools_run_without_network(no_network: None) -> None:
    """세 툴 모두 네트워크가 막힌 상태에서 정상 동작해야 한다."""
    assert calculate(2.0, 3.0, "add") == 5.0
    assert convert(0.0, "celsius_to_fahrenheit") == 32.0
    assert aggregate([12.0, 15.0, 21.0], "mean") == 16.0
