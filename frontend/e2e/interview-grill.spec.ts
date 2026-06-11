import { expect, test } from '@playwright/test';
import { mockCareerNavigatorApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockCareerNavigatorApi(page);
});

test('interview grill runs start → answer each question → report', async ({ page }) => {
  await page.goto('/interview');

  // setup screen
  await expect(page.getByRole('heading', { name: 'Start an interview grilling session' })).toBeVisible();
  await page.getByRole('button', { name: 'Begin grilling' }).click();

  // question 1
  await expect(page.getByText('Question 1 of 2 - behavioral')).toBeVisible();
  await expect(page.getByText('Tell me about a production bug you owned end to end.')).toBeVisible();
  await page.getByRole('textbox').fill('I traced a memory leak to an unbounded cache and added eviction.');
  await page.getByRole('button', { name: 'Submit answer' }).click();

  // feedback shown, advanced to question 2
  await expect(page.getByText('Strong structure — quantify the outcome next time.')).toBeVisible();
  await expect(page.getByText('Question 2 of 2 - system_design')).toBeVisible();
  await page.getByRole('textbox').fill('Token bucket per client key, stored in Redis with a sliding window.');
  await page.getByRole('button', { name: 'Submit answer' }).click();

  // all answered → report
  await expect(page.getByRole('heading', { name: 'All questions answered' })).toBeVisible();
  await page.getByRole('button', { name: 'Generate report' }).click();

  await expect(page.getByText('Overall: 78%')).toBeVisible();
  await expect(page.getByText('Gaps: distributed systems depth')).toBeVisible();
  await expect(page.getByText(/Practise rate limiter variants/)).toBeVisible();
});
