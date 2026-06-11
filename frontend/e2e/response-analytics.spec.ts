import { expect, test } from '@playwright/test';
import { mockCareerNavigatorApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockCareerNavigatorApi(page);
});

test('dashboard shows the response-analytics panel with funnel and rate', async ({ page }) => {
  await page.goto('/');

  const panel = page.getByTestId('response-analytics');
  await expect(panel).toBeVisible();
  await expect(panel.getByRole('heading', { name: 'Response analytics' })).toBeVisible();

  // headline stats
  await expect(panel.getByText('Response rate')).toBeVisible();
  await expect(panel.getByText('33%')).toBeVisible();
  await expect(panel.getByText('Avg 7.5 days to first response')).toBeVisible();

  // funnel bars render for each stage
  await expect(panel.getByTestId('funnel-applied')).toBeVisible();
  await expect(panel.getByTestId('funnel-offer')).toBeVisible();
});
