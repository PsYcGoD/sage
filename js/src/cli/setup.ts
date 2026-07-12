import { setupPythonSage } from '../python/bridge.js';

export function isSetupComplete(): boolean {
  // Setup state is owned by the Python package. The npm launcher should not
  // keep a second, divergent setup flag.
  return false;
}

export async function setup(_force: boolean = false, _yes: boolean = true): Promise<void> {
  setupPythonSage();
}
