// Test Agent - Test framework detection, coverage analysis
import type { Agent, AgentAnalysis } from './index.js';

export class TestAgent implements Agent {
  type = 'test';
  name = 'Test Agent';
  capabilities = ['pytest', 'coverage', 'regression'];
  triggers = [
    'test', 'tests', 'testing', 'pytest', 'unittest',
    'jest', 'vitest', 'playwright', 'coverage', 'regression',
    'assert', 'assertion', 'fixture', 'mock', 'snapshot',
    'ci', 'failing test', 'passed', 'failed', 'rerun',
    'spec', 'e2e', 'unit', 'integration', 'benchmark'
  ];
  description = 'Runs and improves tests.';

  analyze(input: string): AgentAnalysis {
    const findings: string[] = [];
    const suggestions: string[] = [];
    const lower = input.toLowerCase();

    // Pytest output
    if (lower.includes('pytest') || lower.includes('===')) {
      findings.push('pytest output detected');
      
      // Extract pass/fail counts
      const resultMatch = input.match(/(\d+) passed/);
      const failMatch = input.match(/(\d+) failed/);
      const errorMatch = input.match(/(\d+) error/);
      
      if (resultMatch) findings.push(`✓ ${resultMatch[1]} tests passed`);
      if (failMatch) {
        findings.push(`✗ ${failMatch[1]} tests failed`);
        suggestions.push('Run pytest -v for verbose output');
        suggestions.push('Run pytest --lf to rerun only failed tests');
      }
      if (errorMatch) {
        findings.push(`⚠ ${errorMatch[1]} errors`);
        suggestions.push('Fix collection errors before running tests');
      }

      // Check for skipped
      const skipMatch = input.match(/(\d+) skipped/);
      if (skipMatch) {
        findings.push(`⏭ ${skipMatch[1]} tests skipped`);
      }
    }

    // Jest output
    if (lower.includes('jest') || lower.includes('test suites')) {
      findings.push('Jest output detected');
      
      const passMatch = input.match(/(\d+) passed/);
      const failMatch = input.match(/(\d+) failed/);
      
      if (passMatch) findings.push(`✓ ${passMatch[1]} tests passed`);
      if (failMatch) {
        findings.push(`✗ ${failMatch[1]} tests failed`);
        suggestions.push('Run jest --watch to rerun on changes');
        suggestions.push('Run jest --coverage for coverage report');
      }
    }

    // Vitest output
    if (lower.includes('vitest')) {
      findings.push('Vitest output detected');
    }

    // Coverage analysis
    if (lower.includes('coverage') || lower.includes('stmts') || lower.includes('branch')) {
      findings.push('Coverage report detected');
      
      // Extract coverage percentage
      const covMatch = input.match(/(\d+(?:\.\d+)?)\s*%/g);
      if (covMatch && covMatch.length > 0) {
        const percentages = covMatch.map(m => parseFloat(m));
        const avg = percentages.reduce((a, b) => a + b, 0) / percentages.length;
        
        if (avg < 50) {
          findings.push(`⚠ Low coverage: ~${avg.toFixed(0)}%`);
          suggestions.push('Add tests for uncovered code paths');
        } else if (avg < 80) {
          findings.push(`Coverage: ~${avg.toFixed(0)}%`);
          suggestions.push('Consider adding more edge case tests');
        } else {
          findings.push(`✓ Good coverage: ~${avg.toFixed(0)}%`);
        }
      }
    }

    // Assertion failures
    if (lower.includes('assertionerror') || lower.includes('assert')) {
      const assertMatch = input.match(/assert\s+(.+)/i);
      if (assertMatch) {
        findings.push(`Assertion failed: ${assertMatch[1].slice(0, 100)}`);
      }
      suggestions.push('Check expected vs actual values');
    }

    // No test output detected
    if (findings.length === 0) {
      findings.push('No specific test framework output detected');
      suggestions.push('Run tests with verbose output for more details');
    }

    return {
      agent: this.name,
      score: findings.length > 1 ? 0.85 : 0.5,
      findings,
      suggestions
    };
  }
}
