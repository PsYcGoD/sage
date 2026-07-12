import { spawnSync } from 'child_process';

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
  });
}

export function findPython(): PythonCommand | null {
  if (cachedPython) return cachedPython;

  for (const candidate of PYTHON_CANDIDATES) {
    const result = runCandidate(candidate, ['--version']);
    if (result.status === 0) {
      cachedPython = candidate;
      return candidate;
    }
  }

  return null;
}

export function ensurePythonSage(): boolean {
  const python = findPython();
  if (!python) {
    console.error('SAGE npm launcher needs Python 3.10+ on PATH.');
    console.error('Install Python, then retry: npx -y psycgod-sage-js');
    return false;
  }

  const probe = runCandidate(python, ['-m', 'sage', '--version']);
  if (probe.status === 0) {
    return true;
  }

  console.log('Installing Python SAGE core from PyPI...');
  const install = runCandidate(
    python,
    ['-m', 'pip', 'install', '--upgrade', 'psycgod-sage'],
    'inherit'
  );

  if (install.status !== 0) {
    console.error('Failed to install Python SAGE core: psycgod-sage');
    return false;
  }

  return runCandidate(python, ['-m', 'sage', '--version']).status === 0;
}

export function runPythonSage(args: string[]): number {
  const python = findPython();
  if (!python || !ensurePythonSage()) {
    return 1;
  }

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
