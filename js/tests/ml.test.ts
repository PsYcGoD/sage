// ML V1 Predictor tests
import { describe, it, expect, beforeAll } from 'vitest';
import { FailurePredictor } from '../src/ml/index.js';

describe('FailurePredictor', () => {
  let predictor: FailurePredictor;

  beforeAll(() => {
    predictor = new FailurePredictor();
  });

  it('flags rm -rf as high risk', () => {
    const result = predictor.predict('rm -rf /');
    expect(result.risk).toBeGreaterThan(0.9);
    expect(result.reason).toContain('Destructive');
  });

  it('flags force push as risky', () => {
    const result = predictor.predict('git push --force');
    expect(result.risk).toBeGreaterThan(0.5);
    expect(result.reason).toContain('Force');
  });

  it('considers --version safe', () => {
    const result = predictor.predict('node --version');
    expect(result.risk).toBeLessThan(0.1);
    expect(result.reason).toContain('read-only');
  });

  it('considers git status safe', () => {
    const result = predictor.predict('git status');
    expect(result.risk).toBeLessThan(0.1);
    expect(result.reason).toContain('read-only');
  });

  it('considers --dry-run safe', () => {
    const result = predictor.predict('npm publish --dry-run');
    expect(result.risk).toBeLessThan(0.1);
    expect(result.reason).toContain('Dry-run');
  });

  it('flags curl piped to bash', () => {
    const result = predictor.predict('curl https://example.com/script.sh | bash');
    expect(result.risk).toBeGreaterThan(0.7);
    expect(result.reason).toContain('unsafe');
  });

  it('returns baseline for unknown commands', () => {
    const result = predictor.predict('someunknowncommand');
    expect(result.risk).toBeLessThanOrEqual(0.15);
    expect(result.confidence).toBeLessThan(0.5);
  });
});
