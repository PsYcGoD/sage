// sage history
import { Database } from '../../db/index.js';

export async function historyCmd(options: { limit: string; failed?: boolean }): Promise<void> {
  const db = Database.getInstance();
  const limit = parseInt(options.limit, 10) || 10;
  
  const runs = db.getRecentRuns(limit * 2); // Get more, then filter
  
  let filtered = runs;
  if (options.failed) {
    filtered = runs.filter(r => r.exitCode !== 0);
  }
  filtered = filtered.slice(0, limit);

  if (filtered.length === 0) {
    console.log(options.failed 
      ? 'No failed commands in history.' 
      : 'No commands in history yet.');
    return;
  }

  console.log('Recent commands:\n');
  
  for (const run of filtered) {
    const status = run.exitCode === 0 ? '✓' : '✗';
    const saved = run.originalTokens - run.compressedTokens;
    const time = new Date(run.createdAt).toLocaleString();
    
    console.log(`#${run.id} ${status} ${run.command}`);
    console.log(`   Exit: ${run.exitCode} | Saved: ${saved} tokens | ${time}`);
    console.log();
  }

  // Show stats
  const stats = db.getTotalStats();
  console.log('─'.repeat(50));
  console.log(`Total: ${stats.runs} runs | ${stats.savedTokens.toLocaleString()} tokens saved`);
}
