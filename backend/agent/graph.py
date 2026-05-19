"""LangGraph-style orchestrator — plan → execute → observe → King supervisor.
This is a deliberately simple, sync, deterministic reference implementation
that mirrors the structure of AIAAS chat/graph.py and Faultline core/agent.py.

Production use should swap `_plan_with_llm` for a real provider call (NVIDIA
NIM for guests, OpenRouter/OpenAI/Anthropic for authenticated users) and
expand the King supervisor with budget/quality checks."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import Any

from .tools import registry


@dataclass
class AgentState:
    user_id: int | None
    objective: str = ''
    phase_cap: int = 1
    messages: list[dict] = field(default_factory=list)
    pending_tool_calls: list[dict] = field(default_factory=list)
    observations: list[dict] = field(default_factory=list)
    halt: bool = False
    paused_for_approval: dict | None = None


def _plan_with_llm(state: AgentState) -> list[dict]:
    """Stub planner. Production overrides this via dependency injection or settings."""
    return []


async def _execute_tools(state: AgentState, parallelism: int = 8) -> list[dict]:
    """Execute pending_tool_calls in parallel via asyncio.gather, bounded by a semaphore.
    Mirrors Faultline's batching pattern."""
    sem = asyncio.Semaphore(parallelism)

    async def _one(call: dict):
        spec = registry.get(call['name'])
        if spec is None:
            return {'name': call['name'], 'error': 'unknown tool'}
        if spec.phase > state.phase_cap:
            return {'name': call['name'], 'error': 'phase-gated'}
        if spec.requires_approval() and not call.get('approval_token'):
            state.paused_for_approval = call
            state.halt = True
            return {'name': call['name'], 'error': 'approval required'}
        async with sem:
            try:
                result = await asyncio.to_thread(spec.fn, **call.get('args', {}))
                return {'name': call['name'], 'result': result}
            except Exception as exc:  # noqa: BLE001
                return {'name': call['name'], 'error': str(exc)}

    return list(await asyncio.gather(*(_one(c) for c in state.pending_tool_calls)))


def king_review(state: AgentState) -> dict:
    """Cheap deterministic supervisor — surfaces a verdict and a recommendation.
    Replace with an LLM critique call in production (AIAAS executor/king.py pattern)."""
    errors = [o for o in state.observations if isinstance(o, dict) and 'error' in o]
    return {
        'ok': not errors,
        'errors': errors,
        'recommendation': 'halt-and-ask-user' if errors else 'continue',
    }


def step(state: AgentState, *, planner=None) -> AgentState:
    """One plan→execute→observe→supervise iteration."""
    planner = planner or _plan_with_llm
    state.pending_tool_calls = planner(state)
    if not state.pending_tool_calls:
        state.halt = True
        return state
    state.observations = asyncio.run(_execute_tools(state))
    verdict = king_review(state)
    state.messages.append({'role': 'system', 'content': f'king: {verdict}'})
    if verdict['recommendation'] == 'halt-and-ask-user':
        state.halt = True
    return state


def run(state: AgentState, *, planner=None, max_steps: int = 6) -> AgentState:
    for _ in range(max_steps):
        if state.halt:
            break
        state = step(state, planner=planner)
    return state
