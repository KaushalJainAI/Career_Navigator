import { chromium } from 'playwright';
import path from 'node:path';
import fs from 'node:fs/promises';

const root = path.resolve('..');
const artifactsDir = path.join(root, 'docs', 'artifacts');
await fs.mkdir(artifactsDir, { recursive: true });

const browser = await chromium.launch({ headless: true });
const context = await browser.newContext({
  viewport: { width: 1440, height: 1000 },
  recordVideo: { dir: artifactsDir, size: { width: 1440, height: 1000 } },
});
const page = await context.newPage();

const pause = (ms = 1200) => page.waitForTimeout(ms);

await page.goto('http://127.0.0.1:5173/login', { waitUntil: 'networkidle' });
await pause();
await page.getByLabel('Email').fill('demo@career.local');
await page.getByLabel('Password').fill('DemoPass123!');
await pause(600);
await page.getByRole('button', { name: /log in and move/i }).click();
await page.waitForURL('http://127.0.0.1:5173/', { waitUntil: 'networkidle' });
await pause(1800);

await page.getByRole('link', { name: /discover jobs/i }).click();
await page.waitForURL('**/jobs', { waitUntil: 'networkidle' });
await pause(1200);
await page.getByPlaceholder(/search for roles/i).fill('engineer');
await pause(1200);
await page.getByRole('link', { name: /Senior Backend Engineer/i }).click();
await page.waitForURL('**/jobs/*', { waitUntil: 'networkidle' });
await pause(1800);

await page.getByRole('link', { name: /applications/i }).click();
await page.waitForURL('**/applications', { waitUntil: 'networkidle' });
await pause(1800);

await page.getByRole('link', { name: /resumes/i }).click();
await page.waitForURL('**/resumes', { waitUntil: 'networkidle' });
await pause(1200);

await page.getByRole('link', { name: /interview prep/i }).click();
await page.waitForURL('**/interview', { waitUntil: 'networkidle' });
await pause(1000);
await page.getByRole('button', { name: /begin grilling/i }).click();
await pause(1200);
await page.getByPlaceholder(/type your answer/i).fill(
  'I handled ambiguous requirements by aligning stakeholders around a written problem statement, shipping a small prototype in two days, and using adoption data from 3 teams to prioritize the final scope. The result was a simpler launch that reduced manual triage by 28%.',
);
await pause(1000);
await page.getByRole('button', { name: /submit answer/i }).click();
await pause(1800);

await page.getByRole('link', { name: /dashboard/i }).click();
await page.waitForURL('http://127.0.0.1:5173/', { waitUntil: 'networkidle' });
await pause(1600);

await context.close();
await browser.close();

const videos = await fs.readdir(artifactsDir);
const latest = (
  await Promise.all(
    videos
      .filter((name) => name.endsWith('.webm') && name !== 'career-navigator-walkthrough.webm')
      .map(async (name) => {
        const filePath = path.join(artifactsDir, name);
        return { name, path: filePath, mtimeMs: (await fs.stat(filePath)).mtimeMs };
      }),
  )
)
  .sort((a, b) => a.mtimeMs - b.mtimeMs)
  .at(-1);

if (!latest) throw new Error('No video was recorded.');

const finalPath = path.join(artifactsDir, 'career-navigator-walkthrough.webm');
await fs.copyFile(latest.path, finalPath);
console.log(finalPath);
