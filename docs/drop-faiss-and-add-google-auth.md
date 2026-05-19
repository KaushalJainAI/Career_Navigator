# Plan: Drop FAISS + Add Google OAuth (AIAAS pattern)

## Context

Two changes to the current scaffold:

1. **Remove FAISS** from the project. We never actually call into FAISS yet — only `FAISS_INDEX_DIR` in [config/settings/base.py](../backend/config/settings/base.py) and `faiss-cpu` + `sentence-transformers` in [requirements.txt](../backend/requirements.txt). Dropping both removes a heavyweight native dependency (libomp, BLAS, ~200 MB wheel) without losing functionality, since the live scorer already uses a pure-Python `hash_embed` cosine in [matching/embeddings.py](../backend/matching/embeddings.py).
2. **Add Google OAuth** login, mirroring the working pattern in AIAAS at [credentials/oauth.py](../../AIAAS/Backend/credentials/oauth.py) and [core/views.py:185 `GoogleLoginView`](../../AIAAS/Backend/core/views.py).

---

## Part 1 — Drop FAISS

### What replaces it

A **pure-Python cosine search** over vectors stored on `JobPosting.embedding` (a `JSONField`). This is fine for MVP scale (≤ ~50k jobs per query × 256-d vectors ≈ 12M floats ≈ 100 MB working set, still fast enough in numpy). When we need scale, the upgrade path is **pgvector** (one schema migration, one query rewrite — no FAISS detour).

The existing `matching/embeddings.py` and `matching/scorer.py` already work without FAISS, so this is mostly a deletion + a small storage tweak.

### Changes

**Code**
- `backend/requirements.txt` — remove `faiss-cpu>=1.8` and `sentence-transformers>=2.7`. (Sentence-transformers is heavy; keep using the deterministic `hash_embed` until we wire a real embeddings provider via NIM/OpenAI/Anthropic, which speaks HTTP and needs no local model.)
- `backend/config/settings/base.py` — delete the `FAISS_INDEX_DIR = …` and its `mkdir` call.
- `backend/jobs/models.py` — add `embedding = JSONField(default=list, blank=True)` on `JobPosting`. Backfilled at ingestion time by `ingestion/services.upsert_postings`.
- `backend/matching/embeddings.py` — keep `embed()`/`cosine()` as-is. Add a `top_k(query_vec, candidates, k)` helper that does brute-force cosine over a queryset.
- `backend/matching/scorer.py` — unchanged.
- `backend/matching/views.py` — unchanged at the public API; internally use the new `top_k` instead of any FAISS call (none today).
- `backend/ingestion/services.py` — when upserting a posting, compute `embedding = embed(title + '\n' + description[:4000])` and store it on the row.
- `README.md` — drop the "FAISS for embeddings" bullet; replace with "pure-Python cosine search now; pgvector when we need scale."

**Tests**
- `backend/matching/tests/test_scorer.py` already covers `embed`/`cosine`; add one test for `top_k` ordering correctness.
- `backend/ingestion/tests/test_services.py` — assert the row receives a non-empty `embedding` list after upsert.

### Migration

This is the first migration to land for the project. After the requirements change:
```
pip uninstall faiss-cpu sentence-transformers
pip install -r backend/requirements.txt
python manage.py makemigrations jobs
python manage.py migrate
```

### Upgrade path (not now)

When per-user candidate sets exceed ~50k jobs, drop in **pgvector**:
1. `pip install pgvector psycopg2-binary`, `CREATE EXTENSION vector`
2. Replace `JSONField` with `VectorField(dimensions=256)` (via `django-pgvector`)
3. Replace `top_k` with `JobPosting.objects.order_by(L2Distance('embedding', q))[:k]`

No FAISS, no auxiliary index files, no separate index sync job — the embeddings live in the same row as the posting.

---

## Part 2 — Add Google OAuth (AIAAS pattern)

### What we port

From AIAAS:
- [credentials/oauth.py](../../AIAAS/Backend/credentials/oauth.py) — `GoogleOAuthProvider` class that wraps the three Google endpoints (authorize / token / userinfo).
- [core/views.py:185 `GoogleLoginView`](../../AIAAS/Backend/core/views.py) — exchanges a code for tokens, fetches user info, finds-or-creates the local user, returns SimpleJWT access/refresh.
- [core/serializers.py:195 `GoogleLoginSerializer`](../../AIAAS/Backend/core/serializers.py) — accepts `code` + optional `redirect_uri`.
- The four `GOOGLE_OAUTH_*` settings that already exist in AIAAS `base.py` — we add the same to our `config/settings/base.py`.

### Adaptations for Career Navigator

The AIAAS `oauth.py` uses `aiohttp` and `async def`, but its `GoogleLoginView.post` calls those methods **synchronously** — which is actually a latent bug there. We'll port to **`httpx` (sync client)** to match DRF's request lifecycle and avoid the bug.

Also: AIAAS auto-creates `UserProfile` in the view; in our project the `accounts.signals.create_user_profile` post-save signal already does that, so we drop the manual call.

### Files to create / edit

**New**
- `backend/accounts/oauth.py` — port of AIAAS `credentials/oauth.py`, swapped to `httpx`. Public surface:
  - `class GoogleOAuthProvider:`
    - `__init__(redirect_uri=None)`
    - `get_auth_url(scopes=None, state=None, prompt='consent') -> str`
    - `exchange_code(code) -> dict`
    - `refresh_token(refresh_token) -> dict`
    - `get_user_info(access_token) -> dict`
- `backend/accounts/tests/test_oauth.py` — unit tests:
  - `get_auth_url` returns a URL with the expected params.
  - `exchange_code` posts to the right endpoint with the right form body (mock `httpx`).
  - `get_user_info` calls the userinfo endpoint with a bearer header.
  - `GoogleLoginView` happy path: stub the provider, assert user creation + JWT issuance.
  - `GoogleLoginView` failure paths: provider returns `{'error': …}`, missing email, token exchange exception → 400.

**Edits**
- `backend/accounts/serializers.py` — add `GoogleLoginSerializer(code=Char, redirect_uri=Char[optional])`.
- `backend/accounts/views.py` — add `GoogleLoginView(APIView)` that mirrors the AIAAS flow (exchange → userinfo → get-or-create user by email → JWT). Use the existing `UserSerializer` for the response payload.
- `backend/accounts/urls.py` — add `path('google/', GoogleLoginView.as_view(), name='auth-google')`.
- `backend/config/settings/base.py` — add:
  ```python
  GOOGLE_OAUTH_CLIENT_ID = os.environ.get('GOOGLE_OAUTH_CLIENT_ID', '')
  GOOGLE_OAUTH_CLIENT_SECRET = os.environ.get('GOOGLE_OAUTH_CLIENT_SECRET', '')
  GOOGLE_OAUTH_REDIRECT_URI = os.environ.get('GOOGLE_OAUTH_REDIRECT_URI', '')
  GOOGLE_OAUTH_LOGIN_SCOPES = [
      'https://www.googleapis.com/auth/userinfo.email',
      'https://www.googleapis.com/auth/userinfo.profile',
      'openid',
  ]
  ```
- `backend/.env.example` — add the three `GOOGLE_OAUTH_*` keys with blank values.

**Frontend**
- `frontend/src/api/endpoints.ts` — extend `Auth` with:
  - `googleAuthUrl(redirect_uri)` → builds the URL by hitting our backend or constructed client-side
  - `google(code, redirect_uri)` → `POST /auth/google/` returning `{access, refresh, user}`
- `frontend/src/stores/useAuthStore.ts` — add `loginWithGoogle(code, redirectUri)` action that stores tokens and `me` exactly like the password flow.
- `frontend/src/routes/auth/Login.tsx` — add a "Continue with Google" button that:
  - Redirects to `https://accounts.google.com/o/oauth2/v2/auth?...` with `VITE_GOOGLE_CLIENT_ID` and a `state` param.
  - On callback (a small `/auth/google/callback` route), reads `?code=`, calls `loginWithGoogle`, redirects to `/`.
- `frontend/.env.example` — add `VITE_GOOGLE_CLIENT_ID=` and `VITE_GOOGLE_REDIRECT_URI=http://localhost:5173/auth/google/callback`.

### Tests

Backend (`accounts/tests/test_oauth.py` and `test_views.py`):
- `test_get_auth_url_contains_required_params`
- `test_exchange_code_posts_form_to_token_url` (mock `httpx.Client.post`)
- `test_google_login_creates_user_when_missing` (mock provider; assert User and `cn_profile` exist)
- `test_google_login_returns_jwt_for_existing_user`
- `test_google_login_400_on_token_error` (provider returns `{'error': 'invalid_grant'}`)
- `test_google_login_400_on_missing_email`

Frontend (`stores/__tests__/useAuthStore.test.ts`):
- Extend existing tests with one for `loginWithGoogle` storing tokens.

### Critical files

To create:
- `backend/accounts/oauth.py`
- `backend/accounts/tests/test_oauth.py`
- `frontend/src/routes/auth/GoogleCallback.tsx`

To edit:
- `backend/accounts/serializers.py`, `backend/accounts/views.py`, `backend/accounts/urls.py`
- `backend/config/settings/base.py`
- `backend/.env.example`, `frontend/.env.example`
- `frontend/src/api/endpoints.ts`, `frontend/src/stores/useAuthStore.ts`, `frontend/src/routes/auth/Login.tsx`, `frontend/src/App.tsx` (route for callback)

### Reference (AIAAS)

- Provider class: `c:\Users\91700\Desktop\AIAAS\Backend\credentials\oauth.py:8-78`
- View: `c:\Users\91700\Desktop\AIAAS\Backend\core\views.py:185-268`
- Serializer: `c:\Users\91700\Desktop\AIAAS\Backend\core\serializers.py:195-198`
- URL: `c:\Users\91700\Desktop\AIAAS\Backend\core\urls.py:38`

---

## Verification

```bash
# Backend
cd backend
pip install -r requirements.txt        # confirms no faiss / no sentence-transformers needed
python manage.py makemigrations
python manage.py migrate
pytest -q                              # all green, including new oauth tests

# Manual smoke
# 1. Set GOOGLE_OAUTH_CLIENT_ID + SECRET in backend/.env, VITE_GOOGLE_CLIENT_ID in frontend/.env
# 2. npm run dev → click "Continue with Google" → land back logged-in
```

---

## Diff summary

- **Removed** : `faiss-cpu`, `sentence-transformers` from `requirements.txt`; `FAISS_INDEX_DIR` from settings; FAISS bullets from README.
- **Added**   : `embedding` JSONField on `JobPosting`; `top_k()` helper in `matching/embeddings.py`; embedding-on-upsert in `ingestion/services.py`; `accounts/oauth.py` + `GoogleLoginView` + tests + frontend callback route.
- **Unchanged**: scoring logic, agent, interview, all other apps.
