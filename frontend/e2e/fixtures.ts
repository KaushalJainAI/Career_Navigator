import { test as base, type LaunchOptions } from '@playwright/test';

/**
 * Shared `test` export. Set PW_CHROMIUM_PATH to a local Chromium or headless-shell binary to
 * use it instead of the browser Playwright downloaded for this version. Unset, the default is used.
 */
const executablePath = process.env.PW_CHROMIUM_PATH || undefined;

export const test = base.extend<object, { launchOptions: LaunchOptions }>({
  launchOptions: [{ executablePath }, { option: true, scope: 'worker' }],
});
export { expect } from '@playwright/test';
