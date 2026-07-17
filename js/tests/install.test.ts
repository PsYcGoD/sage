import { describe, expect, it } from 'vitest';
import { SAGE_INSTRUCTION, SAGE_INSTRUCTION_SHORT, SAGE_RUN_PREFIX } from '../src/install/targets.js';

describe('npm agent injection instructions', () => {
  it('uses the npm wrapper with sage run as backup without requiring MCP', () => {
    expect(SAGE_RUN_PREFIX).toBe('npx -y psycgod-sage run --');
    expect(SAGE_INSTRUCTION).toContain('npx -y psycgod-sage run -- <command>');
    expect(SAGE_INSTRUCTION_SHORT).toContain('npx -y psycgod-sage run -- <command>');
    expect(SAGE_INSTRUCTION).toContain('Backup when npm/npx is unavailable: `sage run -- <command>`');
    expect(SAGE_INSTRUCTION_SHORT).toContain('Backup when npm/npx is unavailable: sage run -- <command>');
    expect(SAGE_INSTRUCTION).toContain('Use native file/search/edit tools normally.');
    expect(SAGE_INSTRUCTION).not.toContain('PyPI');
    expect(SAGE_INSTRUCTION).not.toContain('mcp__sage__');
    expect(SAGE_INSTRUCTION).not.toContain('SAGE MCP');
    expect(SAGE_INSTRUCTION_SHORT).not.toContain('mcp__sage__');
  });
});
