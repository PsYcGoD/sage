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

function pythonSageImportable(python: PythonCommand): boolean {
  // Cheap probe: imports the package without loading the full CLI.
  return runCandidate(python, ['-c', 'import sage']).status === 0;
}

function installPythonSage(python: PythonCommand): boolean {
  console.log('Installing Python SAGE core from PyPI...');
  const install = runCandidate(
    python,
    ['-m', 'pip', 'install', '--upgrade', 'psycgod-sage'],
    'inherit'
  );
  if (install.status === 0) {
    return true;
  }

  // PEP 668 "externally managed environment" (Debian/Ubuntu/Homebrew Python)
  // rejects plain pip installs; retry as a user install.
  const userInstall = runCandidate(
    python,
    ['-m', 'pip', 'install', '--upgrade', '--user', '--break-system-packages', 'psycgod-sage'],
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

  if (pythonSageImportable(python)) {
    return true;
  }

  return installPythonSage(python) && pythonSageImportable(python);
}

export function runPythonSage(args: string[]): number {
  const python = findPython();
  if (!python) {
    console.error('SAGE npm launcher needs Python 3.10+ on PATH.');
    console.error('Install Python, then retry: npm install -g psycgod-sage');
    return 1;
  }

  // Run directly: the common case pays one Python start, not three. Only when
  // the run fails AND the package is missing do we install and retry once.
  const result = runCandidate(python, ['-m', 'sage', ...args], 'inherit');
  if (result.status === 0) {
    return 0;
  }
  if (pythonSageImportable(python)) {
    return typeof result.status === 'number' ? result.status : 1;
  }

  if (!installPythonSage(python)) {
    return 1;
  }
  const retry = runCandidate(python, ['-m', 'sage', ...args], 'inherit');
  return typeof retry.status === 'number' ? retry.status : 1;
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
