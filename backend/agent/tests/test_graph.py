import pytest

from agent.graph import AgentState, run
from agent.tools import registry
from agent.tools.registry import HITL_HARD_GATE, HITL_NONE, tool


@pytest.fixture(autouse=True)
def fresh_registry():
    registry.clear()
    yield
    registry.clear()


def test_run_executes_basic_tool_and_halts():
    calls = []

    @tool('hello', phase=1, hitl=HITL_NONE)
    def hello(*, name: str = 'world'):
        calls.append(name)
        return {'msg': f'hi {name}'}

    def planner(state):
        if state.observations:
            return []
        return [{'name': 'hello', 'args': {'name': 'alice'}}]

    state = AgentState(user_id=1, objective='greet', phase_cap=1)
    out = run(state, planner=planner, max_steps=3)
    assert calls == ['alice']
    assert out.halt is True
    assert out.observations[0]['result'] == {'msg': 'hi alice'}


def test_phase_gating_blocks_higher_phase_tool():
    @tool('phase3only', phase=3)
    def fn():
        return 'ran'

    def planner(state):
        return [{'name': 'phase3only', 'args': {}}]

    state = AgentState(user_id=1, objective='', phase_cap=1)
    out = run(state, planner=planner, max_steps=1)
    assert out.observations[0]['error'] == 'phase-gated'


def test_hitl_hard_gate_pauses_without_approval_token():
    @tool('do_dangerous', phase=3, hitl=HITL_HARD_GATE)
    def fn(**_):
        return 'should not run'

    def planner(state):
        return [{'name': 'do_dangerous', 'args': {}}]

    state = AgentState(user_id=1, objective='', phase_cap=3)
    out = run(state, planner=planner, max_steps=1)
    assert out.halt is True
    assert out.paused_for_approval is not None
    assert out.paused_for_approval['name'] == 'do_dangerous'


def test_hitl_hard_gate_runs_with_valid_token():
    @tool('with_gate', phase=3, hitl=HITL_HARD_GATE)
    def fn(*, approval_token: str = '', **_):
        return {'approved': approval_token}

    def planner(state):
        return [{'name': 'with_gate', 'args': {'approval_token': 'abc'},
                 'approval_token': 'abc'}]

    state = AgentState(user_id=1, objective='', phase_cap=3)
    out = run(state, planner=planner, max_steps=1)
    assert out.observations[0]['result'] == {'approved': 'abc'}
