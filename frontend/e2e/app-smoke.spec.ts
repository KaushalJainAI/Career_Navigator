import { expect, test } from './fixtures';
import { mockCareerNavigatorApi } from './api-mocks';

test('signed-out visitors are sent to the login page', async ({ page }) => {
  await mockCareerNavigatorApi(page, { authenticated: false });

  await page.goto('/');

  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole('heading', { name: 'Welcome back' })).toBeVisible();
});

test('signed-in user can reach every main page from the navigation', async ({ page }) => {
  await mockCareerNavigatorApi(page);

  await page.goto('/');
  await expect(page.getByRole('heading', { name: 'Today', exact: true })).toBeVisible();

  const pages: { nav: string; heading: string }[] = [
    { nav: 'Jobs', heading: 'Jobs' },
    { nav: 'Pipeline', heading: 'Pipeline' },
    { nav: 'Practice', heading: 'Practice' },
    { nav: 'Assistant', heading: 'Assistant' },
    { nav: 'Profile', heading: 'Your profile' },
    { nav: 'Today', heading: 'Today' },
  ];

  for (const { nav, heading } of pages) {
    await page.getByRole('link', { name: nav, exact: true }).click();
    await expect(page.getByRole('heading', { name: heading, exact: true })).toBeVisible();
  }
});
