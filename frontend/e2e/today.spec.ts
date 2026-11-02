import { expect, test } from './fixtures';
import { EMPTY_TODAY, mockCareerNavigatorApi } from './api-mocks';

test('Today lists the next steps and logs a follow-up', async ({ page }) => {
  const api = await mockCareerNavigatorApi(page);
  api.on('GET', '/applications/today/', () => ({
    ...EMPTY_TODAY,
    steps: [
      {
        kind: 'deadline',
        title: 'Zoho campus drive closes soon',
        detail: 'Apply by the cut-off to stay in the drive.',
        action: { label: 'Open in pipeline', to: '/pipeline?focus=501' },
        application_id: 501,
      },
      {
        kind: 'interview',
        title: 'Online assessment at Zoho tomorrow',
        detail: 'Practise the aptitude and coding round.',
        action: { label: 'Practise for this interview', to: '/practice?application=501' },
        application_id: 501,
      },
      {
        kind: 'follow_up',
        title: 'Follow up with Infosys',
        detail: 'You applied 8 days ago and have not heard back.',
        action: { label: 'Open', to: '/pipeline?focus=502' },
        application_id: 502,
      },
    ],
    week: { applied: 2, goal: 5 },
  }));

  await page.goto('/');

  await expect(page.getByRole('heading', { name: 'Next steps' })).toBeVisible();
  await expect(page.getByText('Zoho campus drive closes soon')).toBeVisible();
  await expect(page.getByRole('link', { name: 'Practise for this interview' })).toHaveAttribute('href', '/practice?application=501');
  await expect(page.getByRole('link', { name: 'Open in pipeline' })).toBeVisible();

  await page.getByRole('button', { name: 'I followed up' }).click();

  await expect(page.getByText('Follow-up logged. Nice work.')).toBeVisible();
  await expect.poll(() => api.find('POST', '/applications/502/followed-up/')).toBeTruthy();
});

test('response rate shows a dash when there are no submitted applications yet', async ({ page }) => {
  await mockCareerNavigatorApi(page);

  await page.goto('/');

  const tile = page.getByRole('link', { name: /Response rate/ });
  await expect(tile).toBeVisible();
  await expect(tile).toContainText('—');
});
