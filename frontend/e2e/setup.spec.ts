import { expect, test } from './fixtures';
import { PROFILE, mockCareerNavigatorApi } from './api-mocks';

const RESUME_TEXT = `Aarav Sharma
B.Tech Computer Science, VIT Pune (CGPA 8.4, 2027)
Skills: Python, SQL, Git, Django
Projects: Library Management System built with Django and PostgreSQL.`;

test('pasted résumé is read, targets are saved, and job search shows per-source results', async ({ page }) => {
  const api = await mockCareerNavigatorApi(page);

  api.on('POST', '/resumes/import-text/', () => ({
    id: 11,
    label: 'Pasted resume',
    parse_status: 'done',
    parse_error: '',
    is_master: true,
    parsed_json: {
      full_name: 'Aarav Sharma',
      headline: 'B.Tech CSE, final year',
      skills: [{ name: 'Python' }, { name: 'SQL' }, { name: 'Git' }, { name: 'Django' }],
      experiences: [],
      educations: [{ institution: 'VIT Pune', degree: 'B.Tech', field_of_study: 'Computer Science', gpa: '8.4' }],
      projects: [{ name: 'Library Management System' }],
    },
    profile_update: {
      changed: ['full_name', 'skills', 'educations', 'preference.target_titles'],
      added_skills: ['Django'],
    },
  }));

  api.on('POST', '/jobs/refresh/', () => ({
    sources: [
      { source: 'Greenhouse', fetched: 40, kept: 9, created: 5, updated: 0, ok: true },
      { source: 'Lever', fetched: 22, kept: 4, created: 2, updated: 0, ok: true },
      { source: 'Remotive', fetched: 0, kept: 0, created: 0, updated: 0, ok: false },
    ],
    new_jobs: 7,
  }));

  await page.goto('/setup');
  await expect(page.getByRole('heading', { name: 'Add your résumé' })).toBeVisible();

  // Step 1: paste the résumé text.
  await page.getByRole('tab', { name: 'Paste text' }).click();
  await page.getByLabel('Résumé text').fill(RESUME_TEXT);
  await page.getByRole('button', { name: 'Read this résumé' }).click();

  await expect(page.getByText('Résumé read. Here is what we found.')).toBeVisible();
  await expect(page.getByText('Aarav Sharma', { exact: true })).toBeVisible();
  await expect(page.getByText('VIT Pune')).toBeVisible();
  await expect(page.getByText('CGPA 8.4')).toBeVisible();
  await expect(page.getByText('Python', { exact: true })).toBeVisible();
  await expect(page.getByText('Filled in: Name, Skills, Education, Target roles.')).toBeVisible();

  const importCall = api.find('POST', '/resumes/import-text/');
  expect(String(importCall?.body.text)).toContain('Library Management System');

  await page.getByRole('button', { name: 'Continue' }).click();

  // Step 2: targets are pre-filled from the profile; add one more role and save.
  await expect(page.getByRole('heading', { name: 'What roles do you want?' })).toBeVisible();
  await expect(page.getByText(PROFILE.preference.target_titles[0])).toBeVisible();
  await page.getByPlaceholder('Type a role and press Enter').fill('Backend Developer');
  await page.getByPlaceholder('Type a role and press Enter').press('Enter');

  await page.getByRole('button', { name: 'Save job targets' }).click();
  await expect(page.getByText('Saved. Your job feed and daily plan use these from now on.')).toBeVisible();

  await expect.poll(() => api.find('PATCH', '/profile/')).toBeTruthy();
  const patch = api.find('PATCH', '/profile/');
  const pref = patch?.body.preference as { target_titles: string[] };
  expect(pref.target_titles).toEqual(['Software Engineer Intern', 'Backend Developer']);

  await page.getByRole('button', { name: 'Continue' }).click();

  // Step 3: search job boards; one source fails and is reported as such.
  await expect(page.getByRole('heading', { name: 'Find jobs' })).toBeVisible();
  await page.getByRole('button', { name: 'Find jobs' }).click();

  await expect(page.getByText('7 new jobs')).toBeVisible();
  const greenhouse = page.getByRole('listitem').filter({ hasText: 'Greenhouse' });
  await expect(greenhouse).toContainText('40 fetched · 9 kept · 5 new');
  await expect(greenhouse.getByText('OK', { exact: true })).toBeVisible();

  const remotive = page.getByRole('listitem').filter({ hasText: 'Remotive' });
  await expect(remotive.getByText('Failed', { exact: true })).toBeVisible();
});
