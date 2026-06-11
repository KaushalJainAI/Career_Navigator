import { expect, test } from '@playwright/test';
import { mockCareerNavigatorApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockCareerNavigatorApi(page);
});

test('job detail shows match score, prepares an assist apply, and generates materials', async ({ page }) => {
  await page.goto('/jobs/101');

  // job + match are loaded, with an explainable breakdown
  await expect(page.getByRole('heading', { name: 'Backend Engineer' })).toBeVisible();
  await expect(page.getByText('Acme Labs')).toBeVisible();
  await expect(page.getByText('Match score: 82%')).toBeVisible();
  await expect(page.getByText('Skill coverage 66%')).toBeVisible();
  await expect(page.getByText(/Not found in your resume: Kubernetes, gRPC/)).toBeVisible();

  // prepare an assisted application
  await page.getByRole('button', { name: 'Assist apply' }).click();
  await expect(page.getByRole('heading', { name: 'Application saved for assisted apply' })).toBeVisible();
  await expect(page.getByText('Application #501 is now saved.')).toBeVisible();
  await expect(page.getByText('Review the tailored resume')).toBeVisible();

  // generate tailored resume + cover letter
  await page.getByRole('button', { name: 'Generate materials' }).click();
  await expect(page.getByRole('heading', { name: 'Tailored resume' })).toBeVisible();
  await expect(page.getByText('Tailored resume emphasising ingestion + Python.')).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Cover letter' })).toBeVisible();
  await expect(page.getByText(/I would love to build your pipelines/)).toBeVisible();

  // ATS-safe resume export downloads a file
  const downloadPromise = page.waitForEvent('download');
  await page.getByRole('button', { name: 'ATS resume .txt' }).click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toBe('resume-ats.txt');
});

test('autonomous apply surfaces the approval token and paused state', async ({ page }) => {
  await page.goto('/jobs/101');
  await expect(page.getByRole('heading', { name: 'Backend Engineer' })).toBeVisible();

  await page.getByRole('button', { name: 'Autonomous review' }).click();

  await expect(page.getByRole('heading', { name: 'Autonomous flow is paused for review' })).toBeVisible();
  await expect(page.getByText('Approval token issued')).toBeVisible();
});
