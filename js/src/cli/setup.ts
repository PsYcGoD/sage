// SAGE Setup - First-run configuration
// ONE prompt (name), auto-connect, inject AI agent configs
import { createInterface } from 'readline';
import { homedir, userInfo, platform } from 'os';
import { existsSync, writeFileSync, readFileSync, mkdirSync } from 'fs';
import { join } from 'path';
import { autoConnect } from '../api/connect.js';
import { injectAllAgentConfigs } from '../install/index.js';
import { Database } from '../db/index.js';

interface SetupState {
  completed: boolean;
  displayName: string;
  machineId: string;
  completedAt: string;
}

function getDataDir(): string {
  const home = homedir();
  if (platform() === 'win32') {
    return join(process.env.LOCALAPPDATA || join(home, 'AppData', 'Local'), 'SAGE');
  }
  return join(home, '.sage');
}

function getSetupPath(): string {
  return join(getDataDir(), 'setup.json');
}

export function isSetupComplete(): boolean {
  try {
    const setupPath = getSetupPath();
    if (!existsSync(setupPath)) return false;
    const state: SetupState = JSON.parse(readFileSync(setupPath, 'utf-8'));
    return state.completed === true;
  } catch {
    return false;
  }
}

function getOsUsername(): string {
  try {
    return userInfo().username || 'User';
  } catch {
    return process.env.USER || process.env.USERNAME || 'User';
  }
}

async function prompt(question: string): Promise<string> {
  const rl = createInterface({
    input: process.stdin,
    output: process.stdout
  });

  return new Promise((resolve) => {
    rl.question(question, (answer) => {
      rl.close();
      resolve(answer.trim());
    });
  });
}

export async function setup(force: boolean = false): Promise<void> {
  const setupPath = getSetupPath();
  const dataDir = getDataDir();

  // Check if already complete
  if (!force && isSetupComplete()) {
    console.log('SAGE setup already completed. Use --force to re-run.');
    return;
  }

  // Ensure data directory exists
  if (!existsSync(dataDir)) {
    mkdirSync(dataDir, { recursive: true });
  }

  let displayName: string;
  const osUsername = getOsUsername();

  // Check if interactive terminal
  if (process.stdin.isTTY) {
    // Interactive - ask for name with OS username as default
    console.log('SAGE First-Time Setup');
    console.log('─'.repeat(40));
    console.log();
    
    const answer = await prompt(`What should SAGE call you [${osUsername}]: `);
    displayName = answer || osUsername;
  } else {
    // Non-interactive (CI/CD, scripts) - silent setup
    displayName = 'User';
  }

  console.log();
  console.log(`Setting up SAGE for ${displayName}...`);
  console.log();

  // Auto-connect to SAGE API (NO PROMPT)
  process.stdout.write('Connecting... ');
  try {
    const result = await autoConnect(displayName);
    if (result.ok) {
      console.log('✓ Connected');
    } else {
      console.log('⚠ Offline (will sync later)');
    }
  } catch {
    console.log('⚠ Offline (will sync later)');
  }

  // Inject AI agent configs (30 tools)
  process.stdout.write('Configuring AI agents... ');
  try {
    const injected = await injectAllAgentConfigs();
    console.log(`✓ ${injected} tools configured`);
  } catch (err) {
    console.log('⚠ Partial configuration');
  }

  // Initialize database
  process.stdout.write('Initializing database... ');
  try {
    Database.getInstance();
    console.log('✓ Ready');
  } catch (err) {
    console.log('⚠ Database warning');
  }

  // Save setup state
  const state: SetupState = {
    completed: true,
    displayName,
    machineId: '', // Set by autoConnect
    completedAt: new Date().toISOString()
  };
  
  writeFileSync(setupPath, JSON.stringify(state, null, 2));

  console.log();
  console.log('─'.repeat(40));
  console.log('✓ Setup complete!');
  console.log();
  console.log('Usage: sage run -- <command>');
  console.log('Example: sage run -- npm test');
  console.log();
}
