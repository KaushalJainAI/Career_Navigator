import { expect, test } from '@playwright/test';
import { mockCareerNavigatorApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockCareerNavigatorApi(page);
});

test('authenticated user can navigate core Phase 2 surfaces', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByText('Career Navigator').first()).toBeVisible();
  await expect(page.getByRole('heading', { name: /One focused session today/i })).toBeVisible();
  await expect(page.getByText('Active Applications')).toBeVisible();
  await expect(page.getByText('Backend Engineer')).toBeVisible();

  await page.getByRole('link', { name: /Discover Jobs/i }).click();
  await expect(page).toHaveURL(/\/jobs$/);
  await expect(page.getByRole('heading', { name: 'Discover Jobs' })).toBeVisible();
  await expect(page.getByText('Acme Labs')).toBeVisible();

  await page.getByRole('link', { name: /Applications/i }).click();
  await expect(page).toHaveURL(/\/applications$/);
  await expect(page.getByRole('heading', { name: 'Applications' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'saved' })).toBeVisible();
  await expect(page.getByText('Backend Engineer')).toBeVisible();

  await page.getByRole('link', { name: 'Settings' }).click();
  await expect(page).toHaveURL(/\/settings$/);
  await expect(page.getByRole('heading', { name: 'Settings' })).toBeVisible();
  await expect(page.getByRole('heading', { name: 'Alert subscriptions' })).toBeVisible();
  await expect(page.getByText('Browser extension API tokens')).toBeVisible();
});

test('unauthenticated users are sent to login', async ({ page }) => {
  await page.addInitScript(() => {
    window.localStorage.removeItem('cn_access');
    window.localStorage.removeItem('cn_refresh');
  });

  await page.goto('/applications');

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
});
