import { expect, test } from '@playwright/test';
import { mockCareerNavigatorApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockCareerNavigatorApi(page);
});

test('a high-risk posting shows the ghost-job badge and reasons panel', async ({ page }) => {
  await page.goto('/jobs/999');

  const badge = page.getByTestId('ghost-risk-badge');
  await expect(badge).toBeVisible();
  await expect(badge).toHaveAttribute('data-band', 'high');
  await expect(badge).toContainText('Ghost-job risk');

  // the high-risk warning panel lists the detection reasons
  await expect(page.getByText(/verify this role is genuinely open/i)).toBeVisible();
  await expect(page.getByText('No salary range disclosed')).toBeVisible();
});

test('a clean posting shows a low-risk badge and no warning panel', async ({ page }) => {
  await page.goto('/jobs/101');

  const badge = page.getByTestId('ghost-risk-badge');
  await expect(badge).toBeVisible();
  await expect(badge).toHaveAttribute('data-band', 'low');
  await expect(page.getByText(/verify this role is genuinely open/i)).toHaveCount(0);
});
