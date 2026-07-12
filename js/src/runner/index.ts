// SAGE Command Runner - Execute and capture commands
import { spawn, SpawnOptions } from 'child_process';
import { compress, CompressionResult } from '../compression/index.js';
import { Database } from '../db/index.js';

export interface RunResult {
  command: string;
  exitCode: number;
  stdout: string;
  stderr: string;
  combined: string;
  compression: CompressionResult;
  durationMs: number;
  runId: number;
}

export async function runCommand(
  command: string,
  args: string[] = [],
  options: { pty?: boolean; cwd?: string } = {}
): Promise<RunResult> {
  const startTime = Date.now();
  const db = Database.getInstance();

  return new Promise((resolve) => {
    const spawnOptions: SpawnOptions = {
      cwd: options.cwd || process.cwd(),
      shell: true,
      env: { ...process.env, FORCE_COLOR: '1' }
    };

    let stdout = '';
    let stderr = '';

    if (options.pty) {
      // PTY mode - inherit stdio for interactive commands
      spawnOptions.stdio = 'inherit';
      
      const child = spawn(command, args, spawnOptions);
      
      child.on('close', (code) => {
        const exitCode = code ?? 1;
        const durationMs = Date.now() - startTime;
        const combined = '[PTY mode - output not captured]';
        const compression = compress(combined, exitCode);
        
        const runId = db.saveRun({
          command: [command, ...args].join(' '),
          exitCode,
          stdout: '',
          stderr: '',
          compressed: compression.compressed,
          originalTokens: compression.originalTokens,
          compressedTokens: compression.compressedTokens,
          durationMs
        });

        resolve({
          command: [command, ...args].join(' '),
          exitCode,
          stdout: '',
          stderr: '',
          combined,
          compression,
          durationMs,
          runId
        });
      });
    } else {
      // Normal mode - capture output
      const child = spawn(command, args, {
        ...spawnOptions,
        stdio: ['inherit', 'pipe', 'pipe']
      });

      child.stdout?.on('data', (data) => {
        const chunk = data.toString();
        stdout += chunk;
        process.stdout.write(chunk);
      });

      child.stderr?.on('data', (data) => {
        const chunk = data.toString();
        stderr += chunk;
        process.stderr.write(chunk);
      });

      child.on('close', (code) => {
        const exitCode = code ?? 1;
        const durationMs = Date.now() - startTime;
        const combined = stdout + stderr;
        const compression = compress(combined, exitCode);

        const runId = db.saveRun({
          command: [command, ...args].join(' '),
          exitCode,
          stdout,
          stderr,
          compressed: compression.compressed,
          originalTokens: compression.originalTokens,
          compressedTokens: compression.compressedTokens,
          durationMs
        });

        resolve({
          command: [command, ...args].join(' '),
          exitCode,
          stdout,
          stderr,
          combined,
          compression,
          durationMs,
          runId
        });
      });

      child.on('error', (err) => {
        const durationMs = Date.now() - startTime;
        const errorMsg = `Command failed: ${err.message}`;
        const compression = compress(errorMsg, 1);

        const runId = db.saveRun({
          command: [command, ...args].join(' '),
          exitCode: 1,
          stdout: '',
          stderr: errorMsg,
          compressed: compression.compressed,
          originalTokens: compression.originalTokens,
          compressedTokens: compression.compressedTokens,
          durationMs
        });

        resolve({
          command: [command, ...args].join(' '),
          exitCode: 1,
          stdout: '',
          stderr: errorMsg,
          combined: errorMsg,
          compression,
          durationMs,
          runId
        });
      });
    }
  });
}

// Parse command string into command and args
export function parseCommand(cmdString: string): { command: string; args: string[] } {
  const parts = cmdString.match(/(?:[^\s"]+|"[^"]*")+/g) || [];
  const command = parts[0] || '';
  const args = parts.slice(1).map(arg => arg.replace(/^"|"$/g, ''));
  return { command, args };
}
