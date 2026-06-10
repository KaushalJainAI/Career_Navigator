import { copyFileSync, mkdirSync } from 'node:fs';
import { resolve } from 'node:path';
import { defineConfig } from 'vite';

function copyExtensionAssets() {
  return {
    name: 'copy-extension-assets',
    closeBundle() {
      const root = process.cwd();
      const outDir = resolve(root, 'dist');
      mkdirSync(outDir, { recursive: true });
      copyFileSync(resolve(root, 'manifest.json'), resolve(outDir, 'manifest.json'));
      copyFileSync(resolve(root, 'popup.html'), resolve(outDir, 'popup.html'));
    },
  };
}

/**
 * Plain Vite build for the MV3 extension. Each content script is an entry
 * point so the same source can target different sites with different
 * `matches` patterns in manifest.json.
 */
export default defineConfig({
  plugins: [copyExtensionAssets()],
  build: {
    outDir: 'dist',
    emptyOutDir: true,
    rollupOptions: {
      input: {
        background: 'src/background.ts',
        popup: 'src/popup.ts',
        'content-linkedin-jobs': 'src/content/linkedin-jobs.ts',
        'content-linkedin-profile': 'src/content/linkedin-profile.ts',
        'content-greenhouse': 'src/content/greenhouse.ts',
        'content-lever': 'src/content/lever.ts',
        'content-naukri': 'src/content/naukri.ts',
        'content-unstop': 'src/content/unstop.ts',
        'content-mercor': 'src/content/mercor.ts',
      },
      output: {
        entryFileNames: '[name].js',
        format: 'esm',
      },
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
  },
});
