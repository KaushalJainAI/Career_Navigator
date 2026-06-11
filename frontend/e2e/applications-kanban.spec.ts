import { expect, test } from '@playwright/test';
import { mockCareerNavigatorApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockCareerNavigatorApi(page);
});

test('moving an application to a new status PATCHes the API and updates the board', async ({ page }) => {
  await page.goto('/applications');

  await expect(page.getByRole('heading', { name: 'Applications' })).toBeVisible();
  await expect(page.getByText('Backend Engineer')).toBeVisible();

  const statusSelect = page.getByRole('combobox');
  await expect(statusSelect).toHaveValue('saved');

  const patchRequest = page.waitForRequest(
    (req) => req.url().includes('/api/v1/applications/501/') && req.method() === 'PATCH',
  );

  await statusSelect.selectOption('applied');

  const req = await patchRequest;
  expect(JSON.parse(req.postData() || '{}')).toEqual({ status: 'applied' });

  // optimistic store update moves the card into the new column
  await expect(statusSelect).toHaveValue('applied');
});
