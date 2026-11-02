import { expect, test } from '@playwright/test';
import { application, company, isoFromNow, mockCareerNavigatorApi, ymdFromNow } from './api-mocks';

test('pipeline groups applications into stage columns and status changes save', async ({ page }) => {
  const api = await mockCareerNavigatorApi(page);
  api.on('GET', '/applications/', () => [
    application({
      id: 501, job: 201, status: 'saved', company: company('Zoho', 1),
      title: 'Software Engineer Intern', deadline: ymdFromNow(2),
    }),
    application({
      id: 502, job: 202, status: 'applied', company: company('Infosys', 2),
      title: 'Systems Engineer Trainee', applied_at: isoFromNow(-8, 9), follow_up_at: isoFromNow(-1, 9),
    }),
    application({
      id: 503, job: 203, status: 'assessment', company: company('TCS', 3),
      title: 'Digital Associate', next_interview_at: isoFromNow(1, 10),
    }),
    application({
      id: 504, job: 204, status: 'phone', company: company('Freshworks', 4),
      title: 'Associate Engineer', next_interview_at: isoFromNow(3, 15),
    }),
  ]);
  api.on('PATCH', '/applications/501/', (c) => ({ id: 501, status: c.body.status }));

  await page.goto('/pipeline');

  for (const name of ['To apply', 'Applied', 'Assessment', 'Interviewing', 'Outcome']) {
    await expect(page.getByRole('region', { name, exact: true })).toBeVisible();
  }
  await expect(page.getByRole('region', { name: 'To apply', exact: true })).toContainText('Zoho');
  await expect(page.getByRole('region', { name: 'Applied', exact: true })).toContainText('Infosys');
  await expect(page.getByRole('region', { name: 'Assessment', exact: true })).toContainText('TCS');
  await expect(page.getByRole('region', { name: 'Interviewing', exact: true })).toContainText('Freshworks');
  await expect(page.getByRole('region', { name: 'Outcome', exact: true })).toContainText('Nothing here');

  // Deadline within two days is shown as urgent.
  await expect(page.getByText(/Apply by .* · in 2 days/)).toBeVisible();

  // Changing a card's status saves it and moves the card to the new column.
  await page.getByRole('combobox', { name: 'Status for Zoho, Software Engineer Intern' }).selectOption('applied');

  await expect.poll(() => api.find('PATCH', '/applications/501/')).toBeTruthy();
  expect(api.find('PATCH', '/applications/501/')?.body).toEqual({ status: 'applied' });
  await expect(page.getByRole('region', { name: 'Applied', exact: true })).toContainText('Zoho');
});
