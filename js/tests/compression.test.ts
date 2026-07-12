// Compression tests
import { describe, it, expect } from 'vitest';
import { compress } from '../src/compression/index.js';

describe('compress', () => {
  it('passes through small output unchanged', () => {
    const result = compress('hello world', 0);
    expect(result.compressed).toBe('hello world');
    expect(result.compressionRatio).toBe('0%');
  });

  it('extracts errors from failed output', () => {
    const output = `
Running tests...
..........
Error: Cannot find module 'foo'
    at Function.Module._resolveFilename
    at Function.Module._load
More output here
    `.trim();
    
    const result = compress(output, 1);
    expect(result.compressed).toContain('Cannot find module');
    expect(result.strategy).toBe('error-extraction');
  });

  it('summarizes long successful output', () => {
    const lines = Array.from({ length: 100 }, (_, i) => `Line ${i + 1}`);
    const output = lines.join('\n');
    
    const result = compress(output, 0);
    expect(result.compressed).toContain('omitted');
    expect(result.strategy).toBe('summarization');
  });

  it('removes duplicate lines', () => {
    const output = Array(10).fill('Same line repeated').join('\n');
    const result = compress(output, 0);
    expect(result.compressed.split('\n').length).toBeLessThan(10);
  });

  it('removes ANSI escape codes', () => {
    const output = '\x1b[32mGreen text\x1b[0m';
    const result = compress(output + '\n'.repeat(50), 0);
    expect(result.compressed).not.toContain('\x1b');
  });
});
