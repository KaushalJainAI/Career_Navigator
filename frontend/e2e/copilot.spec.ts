import { expect, test } from './fixtures';
import { mockCareerNavigatorApi } from './api-mocks';

const SESSION_ID = 77;

test('assistant answers a question and runs an approved change', async ({ page }) => {
  const api = await mockCareerNavigatorApi(page);
  let turn = 0;

  api.on('POST', '/agent/copilot/', (c) => {
    turn += 1;
    if (turn === 1) {
      return {
        session_id: SESSION_ID,
        message_id: 2,
        reply: 'You have an online assessment at Zoho tomorrow at 10:00 AM. Start with the aptitude practice.',
        steps: [{ tool: 'get_overview', args: {}, ok: true }],
        ui: [],
        pending_action: null,
        mode: 'rules',
      };
    }
    return {
      session_id: SESSION_ID,
      message_id: 4,
      reply: `Here is the change I would make for "${String(c.body.message)}".`,
      steps: [],
      ui: [],
      pending_action: {
        id: 'act-1',
        tool: 'update_application',
        args: { application_id: 501, status: 'applied' },
        summary: 'Mark Zoho, Software Engineer Intern as applied',
      },
      mode: 'rules',
    };
  });
  api.on('POST', `/agent/copilot/${SESSION_ID}/approve/`, () => ({
    session_id: SESSION_ID,
    message_id: 5,
    reply: 'Done. Zoho is marked as applied.',
    steps: [{ tool: 'update_application', args: {}, ok: true }],
    ui: [],
    pending_action: null,
    mode: 'rules',
  }));

  await page.goto('/assistant');
  await expect(page.getByRole('heading', { name: 'Assistant', exact: true })).toBeVisible();

  const composer = page.getByPlaceholder(/Ask in plain words/);
  await composer.fill('What should I do today?');
  await page.getByRole('button', { name: 'Send message' }).click();

  await expect(page.getByText('You have an online assessment at Zoho tomorrow at 10:00 AM.')).toBeVisible();
  expect(api.find('POST', '/agent/copilot/')?.body.message).toBe('What should I do today?');

  // A turn that needs approval shows the change and waits for the user.
  await composer.fill('I applied to Zoho today');
  await page.getByRole('button', { name: 'Send message' }).click();

  await expect(page.getByText('Confirm this change')).toBeVisible();
  await expect(page.getByText('Mark Zoho, Software Engineer Intern as applied')).toBeVisible();

  await page.getByRole('button', { name: 'Approve', exact: true }).click();

  await expect(page.getByText('Done. Zoho is marked as applied.')).toBeVisible();
  await expect(page.getByText('Confirm this change')).toHaveCount(0);

  await expect.poll(() => api.find('POST', `/agent/copilot/${SESSION_ID}/approve/`)).toBeTruthy();
  expect(api.find('POST', `/agent/copilot/${SESSION_ID}/approve/`)?.body).toMatchObject({
    action_id: 'act-1',
    approve: true,
  });
});
