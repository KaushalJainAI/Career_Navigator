import { expect, test } from './fixtures';
import { company, feedJob, mockCareerNavigatorApi } from './api-mocks';

const zoho = feedJob({
  id: 201,
  title: 'Backend Engineer, Campus Hire',
  company: company('Zoho', 1),
  location: 'Chennai',
  fit: 86,
  verdict: 'strong',
  matched_skills: ['Python', 'SQL'],
  missing_skills: ['Kubernetes'],
  reasons: [{ kind: 'positive', title: 'Strong skill overlap', detail: '2 of 3 required skills are on your résumé' }],
});

const infosys = feedJob({
  id: 202,
  title: 'Systems Engineer Trainee',
  company: company('Infosys', 2),
  location: 'Pune',
  fit: 61,
  verdict: 'good',
  matched_skills: ['SQL'],
  missing_skills: ['Docker', 'AWS'],
});

test('feed ranks jobs by fit and the Strong 70+ filter sends min_fit=70', async ({ page }) => {
  const api = await mockCareerNavigatorApi(page);
  api.on('GET', '/matching/feed/', (c) => {
    const strongOnly = c.query.get('min_fit') === '70';
    const results = strongOnly ? [zoho] : [zoho, infosys];
    return { count: results.length, total_jobs: 2, has_profile: true, results };
  });

  await page.goto('/jobs');

  await expect(page.getByText('2 jobs · showing best matches first')).toBeVisible();
  await expect(page.getByText('Backend Engineer, Campus Hire')).toBeVisible();
  await expect(page.getByText('86', { exact: true })).toBeVisible();
  await expect(page.getByText('61', { exact: true })).toBeVisible();
  await expect(page.getByText('missing: Kubernetes')).toBeVisible();
  await expect(page.getByText('missing: Docker')).toBeVisible();

  await page.getByRole('button', { name: 'Strong 70+' }).click();

  await expect.poll(() => api.find('GET', '/matching/feed/', (c) => c.query.get('min_fit') === '70')).toBeTruthy();
  await expect(page.getByText('Backend Engineer, Campus Hire')).toBeVisible();
  await expect(page.getByText('Systems Engineer Trainee')).toHaveCount(0);
});

test('adding a job manually posts the details and opens its workspace', async ({ page }) => {
  const api = await mockCareerNavigatorApi(page);
  const deadline = '2026-11-14';

  api.on('GET', '/matching/feed/', () => ({ count: 1, total_jobs: 1, has_profile: true, results: [zoho] }));
  api.on('POST', '/jobs/add/', () => ({
    id: 330,
    application_id: 931,
    job: { id: 330, title: 'Software Engineer Intern' },
  }));
  api.on('GET', '/matching/jobs/330/', () => ({
    fit: 64,
    score: 0.64,
    verdict: 'good',
    matched_skills: ['Python'],
    missing_skills: ['Docker'],
    explanation: [{ kind: 'positive', title: 'Python matches', detail: 'Python is on your résumé' }],
    breakdown: { skills: 0.5, title: 0.6, text: 0.7, location: 1, seniority_penalty: 0 },
  }));
  api.on('GET', '/jobs/330/', () => ({
    id: 330,
    title: 'Software Engineer Intern',
    company: company('Freshworks', 3),
    location: 'Chennai',
    remote: false,
    apply_url: 'https://careers.example/freshworks/330',
    description: '',
    description_text: 'Build and test features for the support product.',
    salary_min: null,
    salary_max: null,
    salary_currency: 'INR',
    posted_at: null,
    ghost_risk: 5,
    ghost_band: 'low',
    ghost_reasons: [],
    skills: {},
  }));

  await page.goto('/jobs');
  await page.getByRole('button', { name: 'Add a job' }).click();

  const dialog = page.getByRole('dialog', { name: 'Add a job' });
  await expect(dialog).toBeVisible();
  await dialog.getByRole('button', { name: 'Enter details manually' }).click();

  await dialog.getByLabel(/Job title/).fill('Software Engineer Intern');
  await dialog.getByLabel(/Company/).fill('Freshworks');
  await dialog.getByLabel(/Application deadline/).fill(deadline);
  await dialog.getByLabel(/Job description/).fill(
    'Build and test features for the support product. Work with senior engineers on Python services.',
  );
  await dialog.getByRole('button', { name: 'Add job', exact: true }).click();

  await expect(page).toHaveURL(/\/jobs\/330$/);
  await expect(page.getByRole('heading', { name: 'Software Engineer Intern' })).toBeVisible();

  const add = api.find('POST', '/jobs/add/');
  expect(add?.body).toMatchObject({
    title: 'Software Engineer Intern',
    company: 'Freshworks',
    deadline,
  });
  expect(String(add?.body.description)).toContain('Python services');
});
