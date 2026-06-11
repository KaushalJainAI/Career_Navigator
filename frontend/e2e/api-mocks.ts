import type { Page, Route, Request } from '@playwright/test';

const user = {
  id: 1,
  email: 'demo@example.com',
  first_name: 'Demo',
  last_name: 'User',
  cn_profile: { tier: 'free', credits_remaining: 10, stealth_domains: [] },
};

const jobs = [
  {
    id: 101,
    title: 'Backend Engineer',
    location: 'Remote',
    remote: true,
    company: { id: 1, name: 'Acme Labs', domain: 'acme.example' },
  },
  {
    id: 102,
    title: 'Frontend Engineer',
    location: 'Bengaluru',
    remote: false,
    company: { id: 2, name: 'Bright Systems', domain: 'bright.example' },
  },
];

const jobDetail = {
  id: 101,
  title: 'Backend Engineer',
  description: '<p>Build resilient ingestion pipelines.</p>',
  apply_url: 'https://acme.example/careers/101',
  company: { id: 1, name: 'Acme Labs', domain: 'acme.example' },
  ghost_risk: 12,
  ghost_band: 'low',
  ghost_reasons: [],
};

const ghostJobDetail = {
  id: 999,
  title: 'Backend Engineer',
  description: '<p>Join our talent pool for future opportunities.</p>',
  apply_url: 'https://ghosty.example/careers/999',
  company: { id: 9, name: 'Ghosty Inc', domain: 'ghosty.example' },
  ghost_risk: 80,
  ghost_band: 'high',
  ghost_reasons: [
    'Same copy live for 90 days (over 60)',
    'No salary range disclosed',
    'Evergreen/pipeline language: future opportunities, talent pool',
  ],
};

const match = {
  score: 0.82,
  breakdown: { semantic: 0.74, skill_overlap: 0.66 },
  gaps: ['Kubernetes', 'gRPC'],
  matched_skills: ['python', 'django'],
  explanation: [
    { kind: 'positive', title: 'Skill coverage 66%', detail: 'Your resume matches 2 of 3 skills the role asks for: python, django' },
    { kind: 'negative', title: '1 skill gap', detail: 'Not found in your resume: Kubernetes, gRPC' },
    { kind: 'positive', title: 'Text similarity 74%', detail: 'How closely your resume wording mirrors the job description overall.' },
  ],
};

const applications = [
  {
    id: 501,
    job: 101,
    status: 'saved',
    tier_used: 'assist',
    job_detail: jobs[0],
  },
];

const interviewQuestions = [
  { id: 1, prompt: 'Tell me about a production bug you owned end to end.', category: 'behavioral', difficulty: 'medium' },
  { id: 2, prompt: 'Design a rate limiter for our public API.', category: 'system_design', difficulty: 'hard' },
];

export async function mockCareerNavigatorApi(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('cn_access', 'test-access-token');
    window.localStorage.setItem('cn_refresh', 'test-refresh-token');
  });

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const method = request.method();
    const path = new URL(request.url()).pathname;
    const body = parseBody(request);

    // --- reads ---
    if (method === 'GET' && path === '/api/v1/auth/me/') {
      return json(route, user);
    }
    if (method === 'GET' && path === '/api/v1/notifications/alerts/') {
      return json(route, []);
    }
    if (method === 'GET' && path === '/api/v1/applications/stats/') {
      return json(route, {
        active_applications: 1,
        new_matches: 2,
        interviews_ready: 0,
        offers_received: 0,
      });
    }
    if (method === 'GET' && path === '/api/v1/applications/analytics/') {
      return json(route, {
        total: 8,
        submitted: 6,
        responses: 2,
        offers: 1,
        rejections: 2,
        response_rate: 0.3333,
        offer_rate: 0.1667,
        funnel: { applied: 6, phone: 2, onsite: 1, offer: 1 },
        by_tier: { assist: { submitted: 6, responses: 2, offers: 1, response_rate: 0.3333 } },
        avg_days_to_first_response: 7.5,
      });
    }
    if (method === 'GET' && path === '/api/v1/jobs/') {
      return json(route, jobs);
    }
    if (method === 'GET' && /^\/api\/v1\/jobs\/\d+\/$/.test(path)) {
      return json(route, path.includes('/999/') ? ghostJobDetail : jobDetail);
    }
    if (method === 'GET' && /^\/api\/v1\/matching\/jobs\/\d+\/$/.test(path)) {
      return json(route, match);
    }
    if (method === 'GET' && path === '/api/v1/applications/') {
      return json(route, applications);
    }
    if (method === 'GET' && path === '/api/v1/profile/') {
      return json(route, {
        full_name: 'Demo User',
        preference: {
          target_titles: ['Backend Engineer'],
          locations: ['Remote'],
          keywords: ['Python'],
          exclude_companies: [],
          remote: true,
          salary_min: null,
          seniority: 'senior',
          work_auth: '',
          stealth_mode: false,
        },
      });
    }
    if (method === 'GET' && path === '/api/v1/notifications/subscriptions/') {
      return json(route, []);
    }

    // --- tiered apply + tailoring ---
    if (method === 'POST' && path === '/api/v1/applications/prepare/') {
      const tier = (body.tier as string) || 'assist';
      const autonomous = tier === 'autonomous';
      return json(route, {
        tier,
        status: autonomous ? 'pending_review' : 'saved',
        apply_url: jobDetail.apply_url,
        approval_token: autonomous ? 'tok-approval-1' : undefined,
        next_actions: ['Review the tailored resume', 'Confirm the application details'],
        application: { id: 501 },
      });
    }
    if (method === 'POST' && path === '/api/v1/tailoring/resume/') {
      return json(route, {
        id: 9001,
        content: { raw_text: 'Tailored resume emphasising ingestion + Python.' },
      });
    }
    if (method === 'POST' && path === '/api/v1/tailoring/cover-letter/') {
      return json(route, {
        id: 9002,
        content: 'Dear Acme Labs, I would love to build your pipelines...',
      });
    }
    if (method === 'GET' && path === '/api/v1/tailoring/resume/export/') {
      return route.fulfill({
        status: 200,
        contentType: 'text/plain; charset=utf-8',
        headers: { 'Content-Disposition': 'attachment; filename="resume-ats.txt"' },
        body: 'DEMO USER\n\nSKILLS\nPython, Django\n',
      });
    }

    // --- applications status change ---
    if (method === 'PATCH' && /^\/api\/v1\/applications\/\d+\/$/.test(path)) {
      return json(route, body);
    }

    // --- interview grill ---
    if (method === 'POST' && path === '/api/v1/interview/sessions/') {
      return json(route, { id: 9, role: body.role, stage: body.stage, questions: interviewQuestions });
    }
    if (method === 'POST' && /^\/api\/v1\/interview\/sessions\/\d+\/answer\/$/.test(path)) {
      return json(route, {
        id: 1,
        user_answer: body.answer,
        score: 0.8,
        feedback: 'Strong structure — quantify the outcome next time.',
      });
    }
    if (method === 'POST' && /^\/api\/v1\/interview\/sessions\/\d+\/report\/$/.test(path)) {
      return json(route, {
        overall_score: 0.78,
        gaps: ['distributed systems depth'],
        study_plan: [{ topic: 'System design', action: 'Practise rate limiter variants' }],
      });
    }

    // --- onboarding agent ---
    if (method === 'POST' && path === '/api/v1/agent/sessions/') {
      return json(route, { id: 4242, kind: body.kind });
    }
    if (method === 'POST' && /^\/api\/v1\/agent\/sessions\/\d+\/chat\/$/.test(path)) {
      return json(route, {
        reply: 'Got it — saved Backend Engineer as a target role.',
        observations: [],
        halt: true,
      });
    }

    return json(route, {});
  });
}

function parseBody(request: Request): Record<string, unknown> {
  try {
    return JSON.parse(request.postData() || '{}');
  } catch {
    return {};
  }
}

function json(route: Route, body: unknown) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}
