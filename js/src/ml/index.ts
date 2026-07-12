// SAGE ML V1 Predictor - Pattern-based failure prediction
import { Database } from '../db/index.js';
import { FAILURE_PATTERNS, RISKY_PATTERNS, SAFE_PATTERNS } from './patterns.js';

export interface Prediction {
  risk: number;      // 0.0 to 1.0
  confidence: number; // 0.0 to 1.0
  reason: string;
}

export class FailurePredictor {
  private db: Database;

  constructor() {
    this.db = Database.getInstance();
  }

  predict(command: string): Prediction {
    // 1. Check exact match in history
    const exactMatches = this.db.findExactCommand(command);
    if (exactMatches.length >= 3) {
      const failures = exactMatches.filter(r => r.exitCode !== 0).length;
      const risk = failures / exactMatches.length;
      return {
        risk,
        confidence: 0.95,
        reason: `Exact command history: ${failures}/${exactMatches.length} failures`
      };
    }

    // 2. Check similar commands (same base command)
    const similar = this.db.findSimilarCommands(command, 50);
    if (similar.length >= 5) {
      const failures = similar.filter(r => r.exitCode !== 0).length;
      const risk = failures / similar.length;
      const baseCmd = command.split(/\s+/)[0];
      return {
        risk,
        confidence: 0.75,
        reason: `Similar ${baseCmd} commands: ${failures}/${similar.length} failures`
      };
    }

    // 3. Pattern-based prediction
    const patternResult = this.checkPatterns(command);
    if (patternResult.risk > 0 || patternResult.confidence > 0.5) {
      return patternResult;
    }

    // 4. Default low-risk prediction
    return {
      risk: 0.1,
      confidence: 0.3,
      reason: 'No history, baseline risk'
    };
  }

  private checkPatterns(command: string): Prediction {
    const lower = command.toLowerCase();

    // Check high-risk patterns
    for (const { pattern, risk, reason } of RISKY_PATTERNS) {
      if (pattern.test(lower)) {
        return { risk, confidence: 0.85, reason };
      }
    }

    // Check failure-prone patterns
    for (const { pattern, risk, reason } of FAILURE_PATTERNS) {
      if (pattern.test(lower)) {
        return { risk, confidence: 0.7, reason };
      }
    }

    // Check safe patterns (reduce risk)
    for (const { pattern, reason } of SAFE_PATTERNS) {
      if (pattern.test(lower)) {
        return { risk: 0.05, confidence: 0.6, reason };
      }
    }

    return { risk: 0, confidence: 0, reason: '' };
  }

  // Learn from a completed command
  recordOutcome(command: string, succeeded: boolean): void {
    // This data is already in the database via runCommand
    // Future: could adjust pattern weights based on outcomes
  }
}
