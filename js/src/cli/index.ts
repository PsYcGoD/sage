#!/usr/bin/env node
// SAGE CLI - Smart Agent Guidance Engine
import { Command } from 'commander';
import { VERSION } from '../index.js';
import { runCmd } from './commands/run.js';
import { historyCmd } from './commands/history.js';
import { explainCmd } from './commands/explain.js';
import { suggestCmd } from './commands/suggest.js';
import { predictCmd } from './commands/predict.js';
import { setup, isSetupComplete } from './setup.js';

const program = new Command();

program
  .name('sage')
  .description('Smart Agent Guidance Engine - CLI wrapper with 97% compression')
  .version(VERSION);

// sage run -- <command>
program
  .command('run')
  .description('Run a command with compression and history tracking')
  .option('--pty', 'Use PTY mode for interactive commands')
  .option('--predict', 'Show failure prediction before running')
  .argument('[command...]', 'Command to run after --')
  .action(async (cmdParts: string[], options) => {
    await ensureSetup();
    await runCmd(cmdParts, options);
  });

// sage history
program
  .command('history')
  .description('Show recent command history')
  .option('-n, --limit <number>', 'Number of entries', '10')
  .option('--failed', 'Show only failed commands')
  .action(async (options) => {
    await ensureSetup();
    await historyCmd(options);
  });

// sage explain
program
  .command('explain')
  .description('Explain the most recent command output')
  .option('--failed', 'Explain the most recent failed command')
  .option('--id <number>', 'Explain a specific run by ID')
  .action(async (options) => {
    await ensureSetup();
    await explainCmd(options);
  });

// sage suggest
program
  .command('suggest')
  .description('Suggest next steps based on command output')
  .option('--failed', 'Suggest for the most recent failed command')
  .option('--id <number>', 'Suggest for a specific run by ID')
  .action(async (options) => {
    await ensureSetup();
    await suggestCmd(options);
  });

// sage predict
program
  .command('predict')
  .description('Predict if a command is likely to fail')
  .argument('<command...>', 'Command to analyze')
  .action(async (cmdParts: string[]) => {
    await ensureSetup();
    await predictCmd(cmdParts);
  });

// sage setup (manual trigger)
program
  .command('setup')
  .description('Run first-time setup')
  .option('--force', 'Re-run setup even if already completed')
  .action(async (options) => {
    await setup(options.force);
  });

// Default action: if no command, run setup or show help
program.action(async () => {
  if (!isSetupComplete()) {
    await setup(false);
  } else {
    program.help();
  }
});

async function ensureSetup(): Promise<void> {
  if (!isSetupComplete()) {
    await setup(false);
  }
}

program.parse();
