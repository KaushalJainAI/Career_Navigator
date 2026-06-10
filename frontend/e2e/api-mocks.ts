import type { Page, Route } from '@playwright/test';

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

const applications = [
  {
    id: 501,
    job: 101,
    status: 'saved',
    tier_used: 'assist',
    job_detail: jobs[0],
  },
];

export async function mockCareerNavigatorApi(page: Page) {
  await page.addInitScript(() => {
    window.localStorage.setItem('cn_access', 'test-access-token');
    window.localStorage.setItem('cn_refresh', 'test-refresh-token');
  });

  await page.route('**/api/v1/**', async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname;

    if (path === '/api/v1/auth/me/') {
      return json(route, user);
    }
    if (path === '/api/v1/notifications/alerts/') {
      return json(route, []);
    }
    if (path === '/api/v1/applications/stats/') {
      return json(route, {
        active_applications: 1,
        new_matches: 2,
        interviews_ready: 0,
        offers_received: 0,
      });
    }
    if (path === '/api/v1/jobs/') {
      return json(route, jobs);
    }
    if (path === '/api/v1/applications/') {
      return json(route, applications);
    }
    if (path === '/api/v1/profile/') {
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
    if (path === '/api/v1/notifications/subscriptions/') {
      return json(route, []);
    }

    return json(route, {});
  });
}

function json(route: Route, body: unknown) {
  return route.fulfill({
    status: 200,
    contentType: 'application/json',
    body: JSON.stringify(body),
  });
}
