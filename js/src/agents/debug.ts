// Debug Agent - Traceback parsing, root cause analysis
import type { Agent, AgentAnalysis } from './index.js';

export class DebugAgent implements Agent {
  type = 'debug';
  name = 'Debug Agent';
  capabilities = ['trace', 'root_cause', 'fix_plan'];
  triggers = [
    'debug', 'error', 'traceback', 'failed', 'failure',
    'exception', 'crash', 'stacktrace', 'stack trace',
    'broken', 'hang', 'freeze', 'timeout', 'regression',
    'root cause', 'diagnose', 'issue', 'bug', 'fix',
    'panic', 'fatal', 'cannot', 'missing', 'invalid', 'slow'
  ];
  description = 'Investigates failures and root causes.';

  analyze(input: string): AgentAnalysis {
    const findings: string[] = [];
    const suggestions: string[] = [];
    const lower = input.toLowerCase();

    // Python tracebacks
    if (lower.includes('traceback') || lower.includes('most recent call')) {
      findings.push('Python traceback detected');
      
      // Extract the actual error
      const errorMatch = input.match(/(\w+Error): (.+)/);
      if (errorMatch) {
        findings.push(`Error type: ${errorMatch[1]}`);
        findings.push(`Message: ${errorMatch[2]}`);
      }

      // Find the file and line
      const fileMatch = input.match(/File "([^"]+)", line (\d+)/);
      if (fileMatch) {
        findings.push(`Location: ${fileMatch[1]}:${fileMatch[2]}`);
        suggestions.push(`Check ${fileMatch[1]} at line ${fileMatch[2]}`);
      }
    }

    // JavaScript errors
    if (lower.includes('at ') && (lower.includes('error') || lower.includes('exception'))) {
      findings.push('JavaScript stack trace detected');
      
      const errorMatch = input.match(/(\w+Error): (.+)/);
      if (errorMatch) {
        findings.push(`Error type: ${errorMatch[1]}`);
        findings.push(`Message: ${errorMatch[2]}`);
      }

      // Extract file:line from stack
      const stackMatch = input.match(/at .+ \((.+):(\d+):(\d+)\)/);
      if (stackMatch) {
        findings.push(`Location: ${stackMatch[1]}:${stackMatch[2]}`);
        suggestions.push(`Check ${stackMatch[1]} at line ${stackMatch[2]}`);
      }
    }

    // Rust panics
    if (lower.includes('panic') || lower.includes('thread') && lower.includes('panicked')) {
      findings.push('Rust panic detected');
      const panicMatch = input.match(/panicked at '([^']+)'/);
      if (panicMatch) {
        findings.push(`Panic message: ${panicMatch[1]}`);
      }
    }

    // Common error patterns
    if (lower.includes('connection refused')) {
      findings.push('Connection refused error');
      suggestions.push('Check if the service is running');
      suggestions.push('Verify the port number and host');
    }

    if (lower.includes('permission denied')) {
      findings.push('Permission denied error');
      suggestions.push('Check file/directory permissions');
      suggestions.push('Try running with elevated privileges');
    }

    if (lower.includes('out of memory') || lower.includes('heap')) {
      findings.push('Memory exhaustion detected');
      suggestions.push('Reduce batch size or data being processed');
      suggestions.push('Increase available memory');
    }

    if (lower.includes('timeout')) {
      findings.push('Timeout error detected');
      suggestions.push('Increase timeout value');
      suggestions.push('Check network connectivity');
    }

    // No specific errors found
    if (findings.length === 0) {
      findings.push('No specific error patterns detected');
      suggestions.push('Review the full output for clues');
    }

    return {
      agent: this.name,
      score: findings.length > 1 ? 0.9 : 0.5,
      findings,
      suggestions
    };
  }
}
