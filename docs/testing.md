# Testing

The testing policy is short, strict, and load-bearing.

## The rules

1. **Tests ship in the same commit as the code.** No model, view, tool, or adapter merges without at least a `tests/test_<thing>.py`.
2. **Tests do not touch the network.** No real LLMs, no real Google, no real Adzuna. Use injectable stubs (`llm=`, `provider_factory`, `httpx.MockTransport`).
3. **Tests do not depend on each other.** Pytest may reorder. The test DB is wiped between cases via the `@pytest.mark.django_db` marker.
4. **The HITL gate test is sacred.** [backend/agent/tests/test_graph.py](../backend/agent/tests/test_graph.py) contains the assertion that a `HITL_HARD_GATE` tool cannot run without a valid approval token. If you touch the agent, you must not break it.

## Layout

```
backend/<app>/tests/
    __init__.py
    test_models.py        # field constraints, validators, custom methods
    test_views.py         # DRF auth + permission + payload contracts
    test_<feature>.py     # service-layer / business-logic tests
    test_oauth.py         # accounts only
    test_scorer.py        # matching only
    test_grilling.py      # interview only
    test_graph.py         # agent only — contains the canary gate test
```

Frontend tests live next to the code they test:

```
frontend/src/stores/__tests__/useAuthStore.test.ts
frontend/src/routes/<area>/__tests__/<Page>.test.tsx
```

## Running

```bash
# Backend — everything
cd backend && pytest -q

# Backend — one module
pytest backend/agent/tests/test_graph.py -q

# Backend — one test
pytest backend/agent/tests/test_graph.py::test_hitl_hard_gate_pauses_without_approval_token -q

# Backend — with coverage (when pytest-cov is added)
pytest --cov=backend --cov-report=term-missing

# Frontend — everything
cd frontend && npm run test

# Frontend — watch
npm run test -- --watch
```

Pytest config is in [backend/pytest.ini](../backend/pytest.ini); it points at `config.settings.test` which uses in-memory SQLite, eager Celery, and MD5 password hashing for speed.

## Shared fixtures

[backend/conftest.py](../backend/conftest.py) exposes:

| Fixture | What you get |
|---|---|
| `user` | A Django `User` with `username='alice'`, password set, `UserProfile` auto-created. |
| `api_client` | A `rest_framework.test.APIClient`. |
| `auth_client` | Same client but pre-authenticated as `user` via `force_authenticate`. |

Per-app fixtures live in `<app>/tests/conftest.py` or inline in the test file.

## Patterns

### Mocking HTTP

Use `httpx.MockTransport`. Example from [accounts/tests/test_oauth.py](../backend/accounts/tests/test_oauth.py):

```python
def test_exchange_code_posts_form_to_token_url(settings):
    settings.GOOGLE_OAUTH_CLIENT_ID = 'cid'
    captured = {}

    def handler(req: httpx.Request) -> httpx.Response:
        captured['body'] = req.content.decode()
        return httpx.Response(200, json={'access_token': 'AT'})

    p = GoogleOAuthProvider(http=httpx.Client(transport=httpx.MockTransport(handler)))
    tokens = p.exchange_code('the-code')
    assert tokens['access_token'] == 'AT'
    assert 'code=the-code' in captured['body']
```

Same pattern for adapters: pass a mock client into `AdzunaAdapter(http=...)` once that becomes injectable (Phase 2 cleanup). For now, the `_normalise` static is the unit-tested part; the live `fetch` is integration-tested separately.

### Mocking the LLM

Every LLM-using function takes `llm=`. Pass any callable that returns a string:

```python
def test_tailor_resume_uses_injected_llm():
    captured = {}
    def llm(prompt, **_):
        captured['prompt'] = prompt
        return 'TAILORED'
    out = tailor_resume({'summary': 'engineer'}, 'Senior', 'JD', llm=llm)
    assert out['content']['raw_text'] == 'TAILORED'
    assert 'JD' in captured['prompt']
```

### Replacing a view's collaborator

For OAuth, the view exposes `provider_factory` as a class attribute. Tests swap it for a fake:

```python
class _FakeProvider:
    def __call__(self, **_): return self
    def exchange_code(self, _): return {'access_token': 'AT'}
    def get_user_info(self, _): return {'email': 'alice@example.com', 'given_name': 'A'}

@pytest.fixture(autouse=True)
def restore():
    original = GoogleLoginView.provider_factory
    yield
    GoogleLoginView.provider_factory = original

def test_creates_user(api_client):
    GoogleLoginView.provider_factory = _FakeProvider()
    resp = api_client.post(reverse('auth-google'), {'code': 'x'}, format='json')
    assert resp.status_code == 200
```

### Testing the agent registry

```python
from agent.tools import registry
from agent.tools.registry import HITL_HARD_GATE, tool

@pytest.fixture(autouse=True)
def fresh_registry():
    registry.clear()
    yield
    registry.clear()

def test_hard_gate_pauses_without_approval():
    @tool('do_dangerous', phase=3, hitl=HITL_HARD_GATE)
    def fn(**_):  return 'should not run'

    state = AgentState(user_id=1, objective='', phase_cap=3)
    out = run(state, planner=lambda s: [{'name': 'do_dangerous', 'args': {}}], max_steps=1)
    assert out.halt and out.paused_for_approval is not None
```

The autouse `fresh_registry` fixture is critical — the registry is process-global. Forgetting to clear it leaks tools between tests.

## What to test, per layer

| Layer | Cover |
|---|---|
| Models | Field constraints, partial unique indexes (e.g. `is_master`), property methods (`is_paid`), signal side-effects (auto-create UserProfile). |
| Serializers | write-only fields (`secret` in CredentialSerializer never appears in `to_representation`); required fields; choice validation. |
| Views | auth (`401` for anon), permission (`403` for wrong user), happy path payload shape, validation 400s. |
| Services | the deterministic kernel (`upsert_postings`, `score_resume_against_job`, `summarise_session`) — these have the highest test ROI. |
| Tools | phase gating, HITL gating, body re-check of approval token. |
| Adapters | `_normalise(row)` with realistic fixture; HTTP layer separately if at all. |

## What we don't test (yet)

- **Real-LLM eval suite.** Planned: `backend/tailoring/tests/eval/` with 20 JD↔resume pairs scored by a judge model on CI nightly. Not yet wired.
- **Channels consumer integration.** Planned: `channels.testing.WebsocketCommunicator` flows for notifications and live grilling.
- **Frontend E2E.** Playwright tests for the onboarding chat and the Interview Grill loop will be added with the browser extension in Phase 2.

## CI

Future GitHub Actions workflow (not committed yet) runs:
1. `pytest -q` in `backend/`
2. `npm run test` in `frontend/`
3. (Phase 2) `playwright test` against the extension build

All three block merge on failure.
