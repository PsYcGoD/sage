import { spawnSync } from 'child_process';
import { existsSync, statSync } from 'fs';

export const EXPECTED_SAGE_VERSION = '2.6.0';

interface PythonCommand {
  command: string;
  prefixArgs: string[];
}

const PYTHON_CANDIDATES: PythonCommand[] = [
  ...(process.env.PYTHON ? [{ command: process.env.PYTHON, prefixArgs: [] }] : []),
  { command: 'python', prefixArgs: [] },
  { command: 'py', prefixArgs: ['-3'] },
  { command: 'python3', prefixArgs: [] },
];

let cachedPython: PythonCommand | null = null;

function runCandidate(candidate: PythonCommand, args: string[], stdio: 'pipe' | 'inherit' = 'pipe') {
  return spawnSync(candidate.command, [...candidate.prefixArgs, ...args], {
    stdio,
    encoding: 'utf8',
    env: process.env,
    cwd: childWorkingDirectory(),
  });
}

function childWorkingDirectory(): string {
  const configured = process.env.SAGE_WORKSPACE_CWD;
  if (configured && existsSync(configured) && statSync(configured).isDirectory()) {
    return configured;
  }
  return process.cwd();
}

function parseVersion(value: string): number[] {
  return value.trim().split('.').map((part) => Number.parseInt(part, 10) || 0);
}

function versionAtLeast(actual: string, expected: string): boolean {
  const left = parseVersion(actual);
  const right = parseVersion(expected);
  for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
    const difference = (left[index] || 0) - (right[index] || 0);
    if (difference !== 0) return difference > 0;
  }
  return true;
}

export function findPython(): PythonCommand | null {
  if (cachedPython) return cachedPython;

  for (const candidate of PYTHON_CANDIDATES) {
    const result = runCandidate(candidate, [
      '-c',
      'import sys; print(".".join(map(str, sys.version_info[:3])))',
    ]);
    const version = result.status === 0 ? String(result.stdout || '').trim() : '';
    if (version && versionAtLeast(version, '3.10.0')) {
      cachedPython = candidate;
      return candidate;
    }
  }

  return null;
}

function pythonSageVersion(python: PythonCommand): string | null {
  const result = runCandidate(python, ['-c', 'import sage; print(sage.__version__)']);
  return result.status === 0 ? String(result.stdout || '').trim() : null;
}

function installPythonSage(python: PythonCommand): boolean {
  console.log('Installing Python SAGE core from PyPI...');
  const install = runCandidate(
    python,
    ['-m', 'pip', 'install', '--upgrade', `psycgod-sage>=${EXPECTED_SAGE_VERSION}`],
    'inherit'
  );
  if (install.status === 0) {
    return true;
  }

  // PEP 668 "externally managed environment" (Debian/Ubuntu/Homebrew Python)
  // rejects plain pip installs; retry as a user install.
  const userInstall = runCandidate(
    python,
    ['-m', 'pip', 'install', '--upgrade', '--user', '--break-system-packages', `psycgod-sage>=${EXPECTED_SAGE_VERSION}`],
    'inherit'
  );
  if (userInstall.status !== 0) {
    console.error('Failed to install Python SAGE core: psycgod-sage');
    return false;
  }
  return true;
}

export function ensurePythonSage(): boolean {
  const python = findPython();
  if (!python) {
    console.error('SAGE npm launcher needs Python 3.10+ on PATH.');
    console.error('Install Python, then retry: npm install -g psycgod-sage');
    return false;
  }

  const installedVersion = pythonSageVersion(python);
  if (installedVersion && versionAtLeast(installedVersion, EXPECTED_SAGE_VERSION)) {
    return true;
  }

  if (installedVersion) {
    console.log(
      `Updating Python SAGE core ${installedVersion} -> ${EXPECTED_SAGE_VERSION} for npm compatibility...`
    );
  }
  if (!installPythonSage(python)) return false;
  const updatedVersion = pythonSageVersion(python);
  return Boolean(updatedVersion && versionAtLeast(updatedVersion, EXPECTED_SAGE_VERSION));
}

export function runPythonSage(args: string[]): number {
  if (!ensurePythonSage()) return 1;
  const python = findPython()!;
  const result = runCandidate(python, ['-m', 'sage', ...args], 'inherit');
  return typeof result.status === 'number' ? result.status : 1;
}

export function setupPythonSage(): boolean {
  const python = findPython();
  if (!python || !ensurePythonSage()) {
    return false;
  }

  const result = runCandidate(python, ['-m', 'sage'], 'inherit');
  return result.status === 0;
}

export function showPythonSageApiStatus(): boolean {
  const python = findPython();
  if (!python || !ensurePythonSage()) {
    return false;
  }

  const result = runCandidate(python, ['-m', 'sage', 'api', 'whoami'], 'inherit');
  return result.status === 0;
}
