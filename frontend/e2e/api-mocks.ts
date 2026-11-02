import type { Page, Request, Route } from '@playwright/test';

/**
 * Method-aware mock for the Career Navigator REST API (`**\/api/v1/**`).
 *
 * - Every request is recorded in `api.calls` so specs can assert on bodies and query strings.
 * - Handlers are registered with `api.on(method, path, handler)`. Later registrations win, so a
 *   spec can override a default for one test. Paths are relative to /api/v1 (e.g. '/profile/').
 * - Return a plain value for HTTP 200, or `httpError(status, body)` for anything else.
 * - Nothing here talks to a real backend.
 */

export type Method = 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE';
export type Body = Record<string, unknown>;

export interface ApiCall {
  method: string;
  path: string;
  query: URLSearchParams;
  body: Body;
}

export class HttpReply {
  constructor(readonly status: number, readonly body: unknown) {}
}

export const httpError = (status: number, body: unknown = { detail: 'Not found.' }) => new HttpReply(status, body);

type Handler = (call: ApiCall) => unknown;

interface Entry { method: Method; match: string | RegExp; handle: Handler }

export class ApiMock {
  readonly calls: ApiCall[] = [];
  readonly unhandled: ApiCall[] = [];
  private entries: Entry[] = [];

  on(method: Method, match: string | RegExp, handle: Handler): this {
    this.entries.unshift({ method, match, handle });
    return this;
  }

  /** First recorded call matching the method and path (and optional predicate). */
  find(method: Method, path: string | RegExp, pred?: (c: ApiCall) => boolean): ApiCall | undefined {
    return this.calls.find((c) => c.method === method && matches(path, c.path) && (!pred || pred(c)));
  }

  /** All recorded calls matching the method and path. */
  findAll(method: Method, path: string | RegExp): ApiCall[] {
    return this.calls.filter((c) => c.method === method && matches(path, c.path));
  }

  dispatch(call: ApiCall): { status: number; body: unknown } {
    this.calls.push(call);
    const entry = this.entries.find((e) => e.method === call.method && matches(e.match, call.path));
    if (!entry) {
      this.unhandled.push(call);
      return { status: 200, body: {} };
    }
    const out = entry.handle(call);
    if (out instanceof HttpReply) return { status: out.status, body: out.body };
    return { status: 200, body: out ?? {} };
  }
}

function matches(pattern: string | RegExp, path: string): boolean {
  return typeof pattern === 'string' ? pattern === path : pattern.test(path);
}

// ---------- fixtures (fresher persona: Aarav, final-year B.Tech CSE) ----------

export const USER = {
  id: 1,
  email: 'aarav@example.com',
  first_name: 'Aarav',
  last_name: 'Sharma',
  cn_profile: { tier: 'free', credits_remaining: 10, stealth_domains: [] },
};

/** Local calendar date (YYYY-MM-DD) `days` from now. Matches how the app parses deadlines. */
export function ymdFromNow(days: number): string {
  const d = new Date(Date.now() + days * 86_400_000);
  const p = (n: number) => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
}

/** ISO timestamp `days` from now at a local hour. */
export function isoFromNow(days: number, hour: number): string {
  const d = new Date(Date.now() + days * 86_400_000);
  d.setHours(hour, 0, 0, 0);
  return d.toISOString();
}

export const PREFERENCE = {
  target_titles: ['Software Engineer Intern'],
  locations: ['Pune', 'Bengaluru'],
  remote: false,
  salary_min: null,
  seniority: 'intern',
  keywords: ['Python', 'SQL'],
  exclude_companies: [],
  work_auth: '',
  stealth_mode: false,
  watch_companies: [],
  weekly_goal: 5,
};

export const PROFILE = {
  full_name: 'Aarav Sharma',
  headline: 'B.Tech CSE, final year',
  summary: '',
  location: 'Pune',
  phone: '',
  website: '',
  linkedin: '',
  github: '',
  experiences: [],
  educations: [
    { institution: 'VIT Pune', degree: 'B.Tech', field_of_study: 'Computer Science', start: '2023', end: '2027', gpa: '8.4' },
  ],
  skills: [{ name: 'Python' }, { name: 'SQL' }, { name: 'Git' }],
  projects: [],
  preference: PREFERENCE,
  readiness: { score: 0.6, ready: false, missing: ['Add at least one project'] },
};

export const EMPTY_TODAY = {
  setup: { has_resume: true, has_targets: true, has_jobs: true, complete: true },
  steps: [],
  week: { applied: 0, goal: 5 },
  stats: {
    jobs_available: 0, strong_matches: 0, in_progress: 0, applied: 0,
    responses: 0, response_rate: null, interviewing: 0, offers: 0,
  },
  top_matches: [],
  targets: ['Software Engineer Intern'],
};

export function company(name: string, id: number) {
  return { id, name, domain: `${name.toLowerCase().replace(/[^a-z]/g, '')}.example` };
}

/** A job as the Jobs feed returns it (FeedJob). */
export function feedJob(overrides: Partial<Record<string, unknown>> & { id: number; title: string; company: { id: number; name: string; domain: string } }) {
  return {
    location: 'Pune',
    remote: false,
    apply_url: `https://careers.example/jobs/${overrides.id}`,
    posted_at: isoFromNow(-2, 9),
    created_at: isoFromNow(-2, 9),
    salary_min: null,
    salary_max: null,
    salary_currency: 'INR',
    source: 'greenhouse',
    ghost_risk: 10,
    ghost_band: 'low',
    fit: 70,
    verdict: 'good',
    matched_skills: [],
    missing_skills: [],
    reasons: [],
    application: null,
    ...overrides,
  };
}

/** An application as GET /applications/ returns it. */
export function application(overrides: { id: number; job: number; status: string; company: { id: number; name: string; domain: string }; title: string } & Partial<Record<string, unknown>>) {
  const { company: co, title, ...rest } = overrides;
  return {
    tier_used: 'assist',
    notes: '',
    applied_at: null,
    follow_up_at: null,
    next_interview_at: null,
    deadline: null,
    created_at: isoFromNow(-5, 9),
    updated_at: isoFromNow(-1, 9),
    events: [],
    job_detail: {
      id: overrides.job,
      title,
      company: co,
      location: 'Pune',
      remote: false,
      apply_url: `https://careers.example/jobs/${overrides.job}`,
      description: '',
      description_text: '',
      salary_min: null,
      salary_max: null,
      salary_currency: 'INR',
      posted_at: null,
      ghost_risk: 10,
      ghost_band: 'low',
      ghost_reasons: [],
      skills: {},
    },
    ...rest,
  };
}

/** Installs auth (optional) and the default API mock. Returns the recorder used by specs. */
export async function mockCareerNavigatorApi(page: Page, { authenticated = true }: { authenticated?: boolean } = {}): Promise<ApiMock> {
  if (authenticated) {
    await page.addInitScript(() => {
      try {
        window.localStorage.setItem('cn_access', 'test-access-token');
        window.localStorage.setItem('cn_refresh', 'test-refresh-token');
      } catch {
        /* storage blocked: the app will show the login page */
      }
    });
  }

  const api = new ApiMock();

  // Defaults, lowest priority first. Specs override by calling api.on(...) later.
  api
    .on('GET', '/auth/me/', () => USER)
    .on('GET', '/profile/', () => PROFILE)
    .on('PATCH', '/profile/', (c) => ({ ...PROFILE, ...c.body }))
    .on('GET', '/resumes/', () => [])
    .on('GET', '/notifications/alerts/', () => [])
    .on('GET', '/notifications/subscriptions/', () => [])
    .on('GET', '/applications/today/', () => EMPTY_TODAY)
    .on('GET', '/applications/', () => [])
    .on('GET', '/matching/feed/', () => ({ count: 0, total_jobs: 0, has_profile: true, results: [] }))
    .on('GET', '/interview/sessions/', () => [])
    .on('GET', '/agent/copilot/latest/', () => ({ id: null, status: 'active', pending_action: null, messages: [] }))
    .on('GET', '/tailoring/resume/', () => httpError(404))
    .on('GET', '/tailoring/cover-letter/', () => httpError(404));

  await page.route('**/api/v1/**', async (route: Route) => {
    const req: Request = route.request();
    const method = req.method();
    const headers = req.headers();
    const cors = {
      'access-control-allow-origin': headers.origin ?? '*',
      'access-control-allow-credentials': 'true',
      'access-control-allow-headers': headers['access-control-request-headers'] ?? '*',
      'access-control-allow-methods': 'GET,POST,PATCH,PUT,DELETE,OPTIONS',
    };
    if (method === 'OPTIONS') {
      return route.fulfill({ status: 204, headers: cors });
    }

    const url = new URL(req.url());
    const path = url.pathname.replace(/^.*\/api\/v1/, '');
    const call: ApiCall = { method, path, query: url.searchParams, body: parseBody(req) };
    const { status, body } = api.dispatch(call);
    return route.fulfill({
      status,
      headers: cors,
      contentType: 'application/json',
      body: JSON.stringify(body),
    });
  });

  return api;
}

function parseBody(request: Request): Body {
  try {
    const raw = request.postData();
    if (!raw) return {};
    const parsed: unknown = JSON.parse(raw);
    return parsed && typeof parsed === 'object' ? (parsed as Body) : {};
  } catch {
    return {}; // multipart uploads are not JSON
  }
}
