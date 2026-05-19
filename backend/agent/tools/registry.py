"""Phase-gated, HITL-aware tool registry — modelled on AIAAS chat/tools.py and
Faultline core/tools.py. Tools register themselves with `@tool(...)`. The
orchestrator looks them up by name, enforces phase and HITL gates, and
dispatches the call."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Iterable


HITL_NONE = 'none'
HITL_CONFIRM = 'confirm'
HITL_HARD_GATE = 'gate'


@dataclass
class ToolSpec:
    name: str
    description: str
    phase: int
    hitl: str
    fn: Callable[..., Any]
    params_schema: dict = field(default_factory=dict)

    def requires_approval(self) -> bool:
        return self.hitl == HITL_HARD_GATE


_REGISTRY: dict[str, ToolSpec] = {}


def tool(name: str, *, description: str = '', phase: int = 1, hitl: str = HITL_NONE,
         params_schema: dict | None = None):
    def deco(fn):
        spec = ToolSpec(
            name=name, description=description, phase=phase, hitl=hitl,
            fn=fn, params_schema=params_schema or {},
        )
        _REGISTRY[name] = spec
        return fn
    return deco


def get(name: str) -> ToolSpec | None:
    return _REGISTRY.get(name)


def all_tools(max_phase: int | None = None) -> Iterable[ToolSpec]:
    for spec in _REGISTRY.values():
        if max_phase is None or spec.phase <= max_phase:
            yield spec


def clear():
    """Test helper — wipe the registry between tests."""
    _REGISTRY.clear()
