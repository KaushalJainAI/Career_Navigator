import { expect, test } from '@playwright/test';
import { mockCareerNavigatorApi } from './api-mocks';

test.beforeEach(async ({ page }) => {
  await mockCareerNavigatorApi(page);
});

test('onboarding chat echoes the user message and shows the assistant reply', async ({ page }) => {
  await page.goto('/onboarding');

  await expect(page.getByRole('heading', { name: 'Tell me about you' })).toBeVisible();

  const input = page.getByRole('textbox');
  await input.fill("I'm a backend engineer targeting remote Python roles.");
  await page.getByRole('button', { name: 'Send' }).click();

  // user's own message is rendered immediately
  await expect(page.getByText("I'm a backend engineer targeting remote Python roles.")).toBeVisible();
  // assistant reply comes back from the agent session
  await expect(page.getByText('Got it — saved Backend Engineer as a target role.')).toBeVisible();
});
