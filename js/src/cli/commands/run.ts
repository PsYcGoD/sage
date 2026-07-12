// sage run -- <command>
import { runCommand, parseCommand } from '../../runner/index.js';
import { FailurePredictor } from '../../ml/index.js';

export async function runCmd(
  cmdParts: string[],
  options: { pty?: boolean; predict?: boolean }
): Promise<void> {
  if (cmdParts.length === 0) {
    console.error('Usage: sage run -- <command>');
    process.exit(1);
  }

  const fullCommand = cmdParts.join(' ');
  
  // Optional prediction
  if (options.predict) {
    const predictor = new FailurePredictor();
    const prediction = predictor.predict(fullCommand);
    
    console.log(`[SAGE] Failure risk: ${Math.round(prediction.risk * 100)}%`);
    console.log(`[SAGE] Confidence: ${Math.round(prediction.confidence * 100)}%`);
    console.log(`[SAGE] Reason: ${prediction.reason}`);
    console.log();
  }

  const { command, args } = parseCommand(fullCommand);
  
  const result = await runCommand(command, args, {
    pty: options.pty,
    cwd: process.cwd()
  });

  // Print compression stats
  console.log();
  console.log(`[SAGE] Run #${result.runId} | Exit: ${result.exitCode} | ${result.durationMs}ms`);
  console.log(`[SAGE] Compression: ${result.compression.originalTokens} → ${result.compression.compressedTokens} tokens (${result.compression.compressionRatio} saved)`);

  process.exit(result.exitCode);
}
