import { expect, test } from './fixtures';
import { company, httpError, mockCareerNavigatorApi } from './api-mocks';

const JOB_ID = 201;
const APP_ID = 701;

const jobDetail = {
  id: JOB_ID,
  title: 'Backend Engineer, Campus Hire',
  company: company('Zoho', 1),
  location: 'Chennai',
  remote: false,
  apply_url: 'https://careers.zoho.example/jobs/201',
  description: '<p>Build APIs.</p>',
  description_text: 'Build and maintain REST APIs in Python.\n• Write unit tests\n• Work with SQL databases',
  salary_min: null,
  salary_max: null,
  salary_currency: 'INR',
  posted_at: null,
  ghost_risk: 8,
  ghost_band: 'low',
  ghost_reasons: [],
  skills: { Python: 2, SQL: 1 },
};

const match = {
  fit: 78,
  score: 0.78,
  verdict: 'good',
  matched_skills: ['Python', 'SQL'],
  missing_skills: ['Kubernetes'],
  explanation: [
    { kind: 'positive', title: 'Strong skill overlap', detail: '2 of 3 required skills are on your résumé' },
    { kind: 'negative', title: 'One skill gap', detail: 'Not found in your résumé: Kubernetes' },
  ],
  breakdown: { skills: 0.66, title: 0.5, text: 0.7, location: 1, seniority_penalty: 0 },
};

test('save, tailor, write a cover letter, and mark the job as applied', async ({ page }) => {
  // Keep the "Open application page" click from launching a real tab.
  await page.addInitScript(() => {
    window.open = () => null;
  });

  const api = await mockCareerNavigatorApi(page);
  let resumeReady = false;
  let coverReady = false;
  let status = 'saved';

  api.on('GET', `/jobs/${JOB_ID}/`, () => jobDetail);
  api.on('GET', `/matching/jobs/${JOB_ID}/`, () => match);
  api.on('POST', '/applications/', () => ({
    id: APP_ID,
    job: JOB_ID,
    status: 'saved',
    tier_used: '',
    notes: '',
    applied_at: null,
    follow_up_at: null,
    next_interview_at: null,
    deadline: null,
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
    events: [],
    job_detail: jobDetail,
  }));
  api.on('POST', '/tailoring/resume/', () => {
    resumeReady = true;
    return { id: 801, application_id: APP_ID };
  });
  api.on('GET', '/tailoring/resume/', (c) => {
    if (!resumeReady || c.query.get('application_id') !== String(APP_ID)) return httpError(404);
    return {
      id: 801,
      application_id: APP_ID,
      model_used: 'rules',
      content: {
        full_name: 'Aarav Sharma', headline: 'B.Tech CSE', email: '', phone: '', location: 'Pune', links: [],
        summary: 'Final-year B.Tech CSE student with Python and SQL projects.',
        skills: [{ name: 'Python' }, { name: 'SQL' }, { name: 'Git' }],
        experiences: [],
        educations: [],
        projects: [{ name: 'Library Management System', description: 'Django app with PostgreSQL.' }],
      },
      diff_from_master: {
        changed_sections: ['skills'],
        summary_before: '',
        skills_moved_up: ['Python', 'SQL'],
        skills_added_from_experience: [],
        reordered_roles: [],
        bullets_trimmed: 0,
        keyword_coverage: 74,
        missing_skills: ['Kubernetes'],
        suggestions: ['Add a project that uses containers.'],
        verification: [],
      },
    };
  });
  api.on('POST', '/tailoring/cover-letter/', () => {
    coverReady = true;
    return { id: 901, application_id: APP_ID };
  });
  api.on('GET', '/tailoring/cover-letter/', () => {
    if (!coverReady) return httpError(404);
    return {
      id: 901,
      application_id: APP_ID,
      model_used: 'rules',
      content: 'Dear Zoho hiring team,\n\nI am a final-year B.Tech CSE student who has built REST APIs in Python.',
      verification: [],
    };
  });
  api.on('PATCH', `/applications/${APP_ID}/`, (c) => {
    status = String(c.body.status ?? status);
    return { id: APP_ID, status };
  });

  await page.goto(`/jobs/${JOB_ID}`);

  await expect(page.getByRole('heading', { name: 'Backend Engineer, Campus Hire' })).toBeVisible();
  await expect(page.getByText('Strong skill overlap')).toBeVisible();
  await expect(page.getByText('One skill gap')).toBeVisible();
  await expect(page.getByText('Kubernetes', { exact: true })).toBeVisible();

  // Save and tailor: creates the application, then generates the résumé.
  await page.getByRole('button', { name: 'Save & tailor my résumé' }).click();
  await expect.poll(() => api.find('POST', '/tailoring/resume/')).toBeTruthy();
  expect(api.find('POST', '/applications/')?.body.job).toBe(JOB_ID);
  expect(api.find('POST', '/tailoring/resume/')?.body.application_id).toBe(APP_ID);

  await page.getByRole('button', { name: 'Tailored résumé', exact: true }).click();
  await expect(page.getByText('Keyword coverage 74%')).toBeVisible();
  await expect(page.getByText('Skills moved up: Python, SQL')).toBeVisible();

  // Cover letter.
  await page.getByRole('button', { name: 'Cover letter', exact: true }).click();
  await page.getByRole('button', { name: 'Generate cover letter' }).click();
  await expect(page.getByLabel('Cover letter')).toHaveValue(/Dear Zoho hiring team/);

  // Apply flow: open the company page, then confirm it was submitted.
  await page.getByRole('button', { name: /Open application page/ }).click();
  await page.getByRole('button', { name: /mark as applied/i }).click();

  await expect.poll(() => api.find('PATCH', `/applications/${APP_ID}/`)).toBeTruthy();
  expect(api.find('PATCH', `/applications/${APP_ID}/`)?.body).toEqual({ status: 'applied' });
  await expect(page.getByLabel('Status')).toHaveValue('applied');
});
