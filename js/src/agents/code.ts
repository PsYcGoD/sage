// Code Agent - Syntax, edits, secrets detection
import type { Agent, AgentAnalysis } from './index.js';

export class CodeAgent implements Agent {
  type = 'code';
  name = 'Code Agent';
  capabilities = ['implement', 'refactor', 'review'];
  triggers = [
    'code', 'coding', 'implement', 'refactor', 'rewrite',
    'function', 'class', 'module', 'method', 'bugfix',
    'patch', 'edit', 'modify', 'compile', 'syntax',
    'python', 'javascript', 'typescript', 'node', 'api',
    'endpoint', 'logic', 'algorithm', 'repository'
  ];
  description = 'Inspects code changes: syntax, scoped edits, leaked secrets.';

  analyze(input: string): AgentAnalysis {
    const findings: string[] = [];
    const suggestions: string[] = [];

    // Check for potential secrets
    const secretPatterns = [
      { pattern: /api[_-]?key\s*[=:]\s*['"][^'"]+['"]/gi, type: 'API key' },
      { pattern: /password\s*[=:]\s*['"][^'"]+['"]/gi, type: 'Password' },
      { pattern: /secret\s*[=:]\s*['"][^'"]+['"]/gi, type: 'Secret' },
      { pattern: /token\s*[=:]\s*['"][^'"]+['"]/gi, type: 'Token' },
      { pattern: /sk-[a-zA-Z0-9]{20,}/g, type: 'OpenAI key' },
      { pattern: /ghp_[a-zA-Z0-9]{36}/g, type: 'GitHub token' },
      { pattern: /AKIA[A-Z0-9]{16}/g, type: 'AWS key' },
    ];

    for (const { pattern, type } of secretPatterns) {
      if (pattern.test(input)) {
        findings.push(`⚠️ Potential ${type} detected in code`);
        suggestions.push(`Remove ${type} and use environment variables`);
      }
    }

    // Check for syntax issues (basic patterns)
    if (/\(\s*\)[\s\n]*{/.test(input) && !/function|if|for|while|class/.test(input)) {
      findings.push('Possible syntax issue: empty parentheses before block');
    }

    // Check for common mistakes
    if (/console\.log/.test(input) && /production|prod|deploy/.test(input.toLowerCase())) {
      findings.push('console.log found - consider removing for production');
      suggestions.push('Remove or replace console.log with proper logging');
    }

    if (/debugger;/.test(input)) {
      findings.push('debugger statement found');
      suggestions.push('Remove debugger statement before committing');
    }

    // Check for TODO/FIXME
    const todos = input.match(/TODO|FIXME|HACK|XXX/gi);
    if (todos && todos.length > 0) {
      findings.push(`Found ${todos.length} TODO/FIXME comments`);
    }

    return {
      agent: this.name,
      score: findings.length > 0 ? 0.8 : 1.0,
      findings,
      suggestions
    };
  }
}
