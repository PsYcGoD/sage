// SAGE Database Schema

export const SCHEMA = `
-- Schema version tracking
CREATE TABLE IF NOT EXISTS schema_version (
  version INTEGER PRIMARY KEY,
  applied_at TEXT DEFAULT (datetime('now'))
);

-- Command history
CREATE TABLE IF NOT EXISTS runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  command TEXT NOT NULL,
  exit_code INTEGER NOT NULL,
  stdout TEXT,
  stderr TEXT,
  compressed TEXT,
  original_tokens INTEGER DEFAULT 0,
  compressed_tokens INTEGER DEFAULT 0,
  duration_ms INTEGER DEFAULT 0,
  created_at TEXT DEFAULT (datetime('now'))
);

-- Agents table
CREATE TABLE IF NOT EXISTS agents (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  type TEXT NOT NULL,
  status TEXT DEFAULT 'idle',
  capabilities TEXT,
  created_at TEXT DEFAULT (datetime('now')),
  last_active TEXT
);

-- Setup state
CREATE TABLE IF NOT EXISTS setup (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TEXT DEFAULT (datetime('now'))
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_runs_command ON runs(command);
CREATE INDEX IF NOT EXISTS idx_runs_exit_code ON runs(exit_code);
CREATE INDEX IF NOT EXISTS idx_runs_created ON runs(created_at);
CREATE INDEX IF NOT EXISTS idx_agents_type ON agents(type);
`;

export interface Migration {
  version: number;
  sql: string;
}

export const MIGRATIONS: Migration[] = [
  {
    version: 1,
    sql: `
      -- Initial schema, nothing to migrate
      INSERT OR IGNORE INTO schema_version (version) VALUES (1);
    `
  },
  {
    version: 2,
    sql: `
      -- Add prediction columns
      ALTER TABLE runs ADD COLUMN predicted_risk REAL DEFAULT 0;
      ALTER TABLE runs ADD COLUMN prediction_correct INTEGER DEFAULT NULL;
      INSERT INTO schema_version (version) VALUES (2);
    `
  }
];
