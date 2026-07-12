// sage suggest
import { Database } from '../../db/index.js';

export async function suggestCmd(options: { failed?: boolean; id?: string }): Promise<void> {
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

  console.log(`Suggestions for run #${run.id}:\n`);
  console.log(`Command: ${run.command}`);
  console.log(`Exit code: ${run.exitCode}`);
  console.log();

  const suggestions = generateSuggestions(run.command, run.exitCode, run.compressed || run.stderr);
  
  if (suggestions.length === 0) {
    console.log('No specific suggestions. Review the output above.');
    return;
  }

  console.log('Next steps:');
  suggestions.forEach((suggestion, i) => {
    console.log(`  ${i + 1}. ${suggestion}`);
  });
}

function generateSuggestions(command: string, exitCode: number, output: string): string[] {
  const suggestions: string[] = [];
  const lower = output.toLowerCase();
  const cmdLower = command.toLowerCase();

  // Success suggestions
  if (exitCode === 0) {
    if (cmdLower.includes('test') || cmdLower.includes('pytest') || cmdLower.includes('jest')) {
      suggestions.push('All tests passed. Consider running with coverage: --coverage');
    }
    if (cmdLower.includes('build')) {
      suggestions.push('Build succeeded. Ready to deploy or run.');
    }
    if (cmdLower.includes('install')) {
      suggestions.push('Installation complete. Verify with --version or by importing.');
    }
    return suggestions;
  }

  // Error-based suggestions
  if (lower.includes('modulenotfounderror') || lower.includes('cannot find module')) {
    const moduleMatch = output.match(/No module named '([^']+)'|Cannot find module '([^']+)'/);
    const moduleName = moduleMatch?.[1] || moduleMatch?.[2];
    if (moduleName) {
      if (cmdLower.includes('python') || cmdLower.includes('pip')) {
        suggestions.push(`Install missing module: pip install ${moduleName}`);
      } else {
        suggestions.push(`Install missing module: npm install ${moduleName}`);
      }
    }
  }

  if (lower.includes('syntaxerror')) {
    suggestions.push('Fix the syntax error at the line number shown.');
    suggestions.push('Check for missing colons, brackets, or indentation.');
  }

  if (lower.includes('permission denied')) {
    suggestions.push('Try with elevated privileges: sudo (Unix) or Run as Administrator (Windows)');
    suggestions.push('Check file permissions: ls -la (Unix) or icacls (Windows)');
  }

  if (lower.includes('command not found')) {
    suggestions.push('Install the missing command or add it to PATH.');
    suggestions.push('Check spelling of the command name.');
  }

  if (lower.includes('connection refused')) {
    suggestions.push('Start the required service first.');
    suggestions.push('Check if the port is correct and not blocked by firewall.');
  }

  if (lower.includes('enoent') || lower.includes('no such file')) {
    suggestions.push('Check if the file/directory exists.');
    suggestions.push('Verify the path is correct (relative vs absolute).');
  }

  if (lower.includes('assertion') || lower.includes('test failed')) {
    suggestions.push('Review the failing test and expected vs actual values.');
    suggestions.push('Run with verbose output for more details.');
  }

  // Generic fallback
  if (suggestions.length === 0) {
    suggestions.push('Review the error output above.');
    suggestions.push('Search the error message online.');
    suggestions.push('Check documentation for the command.');
  }

  return suggestions;
}
