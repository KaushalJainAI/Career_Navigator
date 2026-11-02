import { expect, test } from './fixtures';
import { application, company, isoFromNow, mockCareerNavigatorApi } from './api-mocks';

const SESSION_ID = 9001;
const PROMPT = 'Tell me about a time you debugged a production issue in a project.';

test('practice an application: answer, see feedback, then the report', async ({ page }) => {
  const api = await mockCareerNavigatorApi(page);

  api.on('GET', '/applications/', () => [
    application({
      id: 501, job: 201, status: 'assessment', company: company('Zoho', 1),
      title: 'Software Engineer Intern', next_interview_at: isoFromNow(1, 10),
    }),
  ]);
  api.on('POST', '/interview/sessions/', () => ({
    id: SESSION_ID,
    role: 'Software Engineer Intern',
    stage: 'tech_phone',
    status: 'active',
    job: 201,
    company: 1,
    started_at: new Date().toISOString(),
    questions: [{ id: 1, prompt: PROMPT, category: 'behavioral', order: 1 }],
  }));
  api.on('POST', `/interview/sessions/${SESSION_ID}/answer/`, () => ({
    id: 1,
    question: 1,
    user_answer: 'I noticed a crash in the library app. I added logging and fixed a null check.',
    score: 0.72,
    feedback: 'Good structure. Quantify the impact next time.',
    evaluation: {
      structure: 0.7,
      specificity: 0.6,
      outcome: 0.5,
      score: 0.72,
      feedback: 'Good structure. Quantify the impact next time.',
      strengths: ['Clear STAR structure'],
      gaps: ['Say how much the fix helped'],
    },
  }));
  api.on('POST', `/interview/sessions/${SESSION_ID}/report/`, () => ({
    overall_score: 0.72,
    strengths: ['Clear STAR structure'],
    gaps: ['Quantify outcomes'],
    study_plan: [{ topic: 'Quantify outcomes', action: 'Add one metric to each project story.' }],
  }));

  await page.goto('/practice?application=501');

  await expect(page.getByRole('heading', { name: 'Practice', exact: true })).toBeVisible();
  await page.getByRole('button', { name: 'Start practice' }).click();

  await expect(page.getByText('Question 1 of 1')).toBeVisible();
  await expect(page.getByRole('heading', { name: PROMPT })).toBeVisible();

  const answer = 'I noticed a crash in the library app. I added logging and fixed a null check.';
  await page.getByLabel(/Your answer/).fill(answer);
  await page.getByRole('button', { name: 'Submit answer' }).click();

  await expect(page.getByText('Good structure. Quantify the impact next time.').first()).toBeVisible();
  await expect(page.getByText('Clear STAR structure')).toBeVisible();
  await expect(page.getByText('72%', { exact: true }).first()).toBeVisible();

  await expect.poll(() => api.find('POST', `/interview/sessions/${SESSION_ID}/answer/`)).toBeTruthy();
  expect(api.find('POST', `/interview/sessions/${SESSION_ID}/answer/`)?.body.answer).toBe(answer);

  await page.getByRole('button', { name: 'Finish & see report' }).click();

  await expect(page.getByRole('heading', { name: 'Your report' })).toBeVisible();
  await expect(page.getByText('Add one metric to each project story.')).toBeVisible();
  await expect(page.getByText('Quantify outcomes').first()).toBeVisible();
  await expect(page.getByText('72%', { exact: true }).first()).toBeVisible();
});
