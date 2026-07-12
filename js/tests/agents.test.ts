// Agent tests
import { describe, it, expect } from 'vitest';
import { selectAgents, agents } from '../src/agents/index.js';
import { SecurityAgent } from '../src/agents/security.js';

describe('selectAgents', () => {
  it('selects debug agent for error-related input', () => {
    const selected = selectAgents('traceback error failed');
    expect(selected.some(a => a.type === 'debug')).toBe(true);
  });

  it('selects test agent for test-related input', () => {
    const selected = selectAgents('pytest coverage failing test');
    expect(selected.some(a => a.type === 'test')).toBe(true);
  });

  it('selects security agent for security input', () => {
    const selected = selectAgents('api key password secret');
    expect(selected.some(a => a.type === 'security')).toBe(true);
  });

  it('selects code agent for code input', () => {
    const selected = selectAgents('implement function refactor');
    expect(selected.some(a => a.type === 'code')).toBe(true);
  });

  it('respects limit parameter', () => {
    const selected = selectAgents('code debug test security', 2);
    expect(selected.length).toBeLessThanOrEqual(2);
  });
});

describe('SecurityAgent', () => {
  const agent = new SecurityAgent();

  it('detects OpenAI API keys', () => {
    const result = agent.analyze('const key = "sk-abc123def456ghi789jkl012mno345"');
    expect(result.findings.some(f => f.includes('OpenAI'))).toBe(true);
  });

  it('detects GitHub tokens', () => {
    const result = agent.analyze('token = "ghp_abcdefghijklmnopqrstuvwxyz123456"');
    expect(result.findings.some(f => f.includes('GitHub'))).toBe(true);
  });

  it('detects eval usage', () => {
    const result = agent.analyze('eval(userInput)');
    expect(result.findings.some(f => f.includes('eval'))).toBe(true);
  });

  it('passes clean code', () => {
    const result = agent.analyze('const x = 1 + 2;');
    expect(result.findings.some(f => f.includes('No security issues'))).toBe(true);
  });
});
