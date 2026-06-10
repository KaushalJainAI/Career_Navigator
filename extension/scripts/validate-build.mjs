import { existsSync, readFileSync } from 'node:fs';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';

const dist = fileURLToPath(new URL('../dist/', import.meta.url));
const requiredRootFiles = ['manifest.json', 'popup.html', 'background.js', 'popup.js'];

function assert(condition, message) {
  if (!condition) {
    console.error(`Extension build invalid: ${message}`);
    process.exitCode = 1;
  }
}

function exists(file) {
  return existsSync(join(dist, file));
}

for (const file of requiredRootFiles) {
  assert(exists(file), `missing ${file}`);
}

const manifestPath = join(dist, 'manifest.json');
if (existsSync(manifestPath)) {
  const manifest = JSON.parse(readFileSync(manifestPath, 'utf8'));
  assert(manifest.manifest_version === 3, 'manifest_version must be 3');
  assert(manifest.background?.service_worker && exists(manifest.background.service_worker), 'missing background service worker bundle');
  assert(manifest.action?.default_popup && exists(manifest.action.default_popup), 'missing default popup html');

  for (const script of manifest.content_scripts || []) {
    for (const js of script.js || []) {
      assert(exists(js), `missing content script bundle ${js}`);
    }
  }
}

if (!process.exitCode) {
  console.log('Extension build valid.');
}
