#!/usr/bin/env node
// SAGE npm postinstall.
//
// npm/npx is a convenience distribution path. The Python package is the
// canonical implementation, so postinstall installs/updates PyPI SAGE and runs
// the same zero-prompt setup users get from:
//   python -m pip install --upgrade psycgod-sage; python -m sage
import { ensurePythonSage, setupPythonSage } from './python/bridge.js';
import { injectAllAgentConfigs } from './install/index.js';
import { installHooks } from './install/hooks.js';

async function main(): Promise<void> {
  console.log('');
  console.log('SAGE npm launcher: installing canonical Python SAGE core...');

  if (!ensurePythonSage()) {
    console.log('SAGE npm launcher installed, but Python SAGE setup could not complete.');
    console.log('Install Python 3.10+, then run: npx -y psycgod-sage-js');
    return;
  }

  setupPythonSage();

  console.log('Installing npm/npx SAGE instructions for AI agents...');
  try {
    const injected = await injectAllAgentConfigs();
    console.log(`SAGE npm instructions configured for ${injected} target(s).`);
  } catch {
    console.log('SAGE npm instructions had warnings; run `npx -y psycgod-sage-js setup` later if needed.');
  }

  try {
    const hooks = await installHooks();
    console.log(`SAGE npm enforcement hooks configured for ${hooks} target(s).`);
  } catch {
    console.log('SAGE npm enforcement hooks had warnings.');
  }

  console.log('');
  console.log('SAGE ready.');
  console.log('Use: npx -y psycgod-sage-js run -- <command>');
  console.log('Optional ML V2 later: npx -y psycgod-sage-js ml setup');
  console.log('');
}

main().catch((err) => {
  console.error(`SAGE npm postinstall warning: ${err?.message || err}`);
  process.exit(0);
});
