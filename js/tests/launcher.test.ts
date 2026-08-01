import { readFileSync } from 'fs';
import { resolve } from 'path';
import { describe, expect, it } from 'vitest';

import { VERSION } from '../src/index.js';
import { EXPECTED_SAGE_VERSION } from '../src/python/bridge.js';

const packageJson = JSON.parse(
  readFileSync(resolve(process.cwd(), 'package.json'), 'utf8')
);

describe('wrapper-only npm launcher', () => {
  it('keeps the npm and Python-core compatibility versions synchronized', () => {
    expect(VERSION).toBe(packageJson.version);
    expect(EXPECTED_SAGE_VERSION).toBe(packageJson.version);
  });

  it('has no install-time lifecycle side effects', () => {
    expect(packageJson.scripts.preinstall).toBeUndefined();
    expect(packageJson.scripts.install).toBeUndefined();
    expect(packageJson.scripts.postinstall).toBeUndefined();
  });

  it('publishes only the thin launcher and Python bridge', () => {
    expect(packageJson.files).toEqual([
      'bin',
      'dist/index.*',
      'dist/cli/index.*',
      'dist/python/bridge.*',
    ]);
  });

  it('supports an explicit workspace from desktop hosts', () => {
    const bridge = readFileSync(resolve(process.cwd(), 'src/python/bridge.ts'), 'utf8');
    expect(bridge).toContain('SAGE_WORKSPACE_CWD');
  });
});
