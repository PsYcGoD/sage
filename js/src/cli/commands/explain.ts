// sage explain
import { Database } from '../../db/index.js';

export async function explainCmd(options: { failed?: boolean; id?: string }): Promise<void> {
  const db = Database.getInstance();
  
  let run;
  if (options.id) {
    run = db.getRunById(parseInt(options.id, 10));
    if (!run) {
      console.error(`Run #${options.id} not found.`);
      process.exit(1);
    }
  } else if (options.failed) {
    run = db.getLatestFailedRun();
    if (!run) {
      console.log('No failed commands found.');
      return;
    }
  } else {
    run = db.getLatestRun();
    if (!run) {
      console.log('No commands in history yet.');
      return;
    }
  }

  console.log(`Explaining run #${run.id}:\n`);
  console.log(`Command: ${run.command}`);
  console.log(`Exit code: ${run.exitCode}`);
  console.log(`Duration: ${run.durationMs}ms`);
  console.log();

  if (run.exitCode === 0) {
    console.log('✓ Command succeeded.');
    console.log();
    console.log('Compressed output:');
    console.log(run.compressed || '(no output)');
  } else {
    console.log('✗ Command failed.');
    console.log();
    console.log('Error analysis:');
    console.log(run.compressed || run.stderr || '(no output)');
    
    // Pattern-based explanation
    const explanation = analyzeError(run.compressed || run.stderr);
    if (explanation) {
      console.log();
      console.log('Likely cause:');
      console.log(explanation);
    }
  }
}

function analyzeError(output: string): string | null {
  const lower = output.toLowerCase();
  
  if (lower.includes('modulenotfounderror') || lower.includes('cannot find module')) {
    return 'Missing dependency. Run: pip install <module> or npm install <module>';
  }
  if (lower.includes('syntaxerror')) {
    return 'Syntax error in code. Check the file and line number mentioned.';
  }
  if (lower.includes('permission denied')) {
    return 'Permission issue. Try running with elevated privileges or check file permissions.';
  }
  if (lower.includes('command not found')) {
    return 'Command not installed or not in PATH.';
  }
  if (lower.includes('connection refused')) {
    return 'Service not running or wrong port. Check if the server is started.';
  }
  if (lower.includes('timeout')) {
    return 'Operation timed out. Check network or increase timeout.';
  }
  if (lower.includes('out of memory') || lower.includes('heap')) {
    return 'Memory exhausted. Try processing smaller batches or increase memory.';
  }
  
  return null;
}
