"""T21 依赖就绪检查；只暴露up/down，不透传下游异常。"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class DependencyProbe:
    name: str
    required: bool
    check: Callable[[], bool]


class HealthService:
    def __init__(self, probes: tuple[DependencyProbe, ...]) -> None:
        self.probes = probes

    def readiness(self) -> tuple[bool, dict[str, str]]:
        statuses: dict[str, str] = {}
        ready = True
        for probe in self.probes:
            try:
                up = probe.check() is True
            except Exception:
                up = False
            statuses[probe.name] = "up" if up else "down"
            if probe.required and not up:
                ready = False
        return ready, statuses


__all__ = ["DependencyProbe", "HealthService"]
