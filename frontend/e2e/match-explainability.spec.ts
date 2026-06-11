import { expect, test } from '@playwright/test';
import { mockCareerNavigatorApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockCareerNavigatorApi(page);
});

test('job detail explains the match with colour-coded positive and negative reasons', async ({ page }) => {
  await page.goto('/jobs/101');

  const card = page.getByTestId('match-card');
  await expect(card).toBeVisible();

  // positive skill-coverage reason
  const positive = card.locator('li[data-kind="positive"]').first();
  await expect(positive).toContainText('Skill coverage 66%');

  // negative skill-gap reason
  const negative = card.locator('li[data-kind="negative"]');
  await expect(negative).toContainText('skill gap');
  await expect(negative).toContainText('Kubernetes, gRPC');

  // text-similarity reason is always present
  await expect(card.getByText('Text similarity 74%')).toBeVisible();
});
