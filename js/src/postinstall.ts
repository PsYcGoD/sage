#!/usr/bin/env node
// SAGE npm postinstall.
//
// npm/npx is a convenience distribution path. The Python package is the
// canonical implementation, so postinstall installs/updates PyPI SAGE, runs
// zero-prompt setup, and prints API status in the same npm install run.
import { ensurePythonSage, setupPythonSage, showPythonSageApiStatus } from './python/bridge.js';
import { injectAllAgentConfigs } from './install/index.js';
import { installHooks } from './install/hooks.js';

async function main(): Promise<void> {
  console.log('');
  console.log('SAGE npm launcher: installing canonical Python SAGE core...');

  if (!ensurePythonSage()) {
    console.log('SAGE npm launcher installed, but Python SAGE setup could not complete.');
    console.log('Install Python 3.10+, then retry: npm install -g psycgod-sage');
    return;
  }

  setupPythonSage();

  console.log('');
  console.log('SAGE API connection result:');
  showPythonSageApiStatus();

  console.log('Installing npm/npx SAGE instructions for AI agents...');
  try {
    const injected = await injectAllAgentConfigs();
    console.log(`SAGE npm instructions configured for ${injected} target(s).`);
  } catch {
    console.log('SAGE npm instructions had warnings; run `sage setup --force` later if needed.');
  }

  try {
    const hooks = await installHooks();
    console.log(`SAGE npm enforcement hooks configured for ${hooks} target(s).`);
  } catch {
    console.log('SAGE npm enforcement hooks had warnings.');
  }

  console.log('');
  console.log('SAGE ready.');
  console.log('Use: sage run -- <command>');
  console.log('Optional ML V2 later: sage ml setup');
  console.log('');
}

main().catch((err) => {
  console.error(`SAGE npm postinstall warning: ${err?.message || err}`);
  process.exit(0);
});
