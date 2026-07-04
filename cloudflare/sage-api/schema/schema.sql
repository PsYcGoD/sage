CREATE TABLE IF NOT EXISTS api_keys (
  key_id TEXT PRIMARY KEY,
  secret_hash TEXT NOT NULL UNIQUE,
  prefix TEXT NOT NULL,
  scope TEXT NOT NULL DEFAULT 'personal',
  display_name TEXT DEFAULT '',
  username TEXT DEFAULT '',
  public_profile INTEGER NOT NULL DEFAULT 0,
  privacy_max INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL,
  last_used_at TEXT DEFAULT '',
  revoked_at TEXT DEFAULT '',
  rate_limit_per_hour INTEGER NOT NULL DEFAULT 1000
);

CREATE TABLE IF NOT EXISTS installations (
  installation_id TEXT PRIMARY KEY,
  key_id TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  client_version TEXT DEFAULT '',
  platform TEXT DEFAULT '',
  FOREIGN KEY (key_id) REFERENCES api_keys(key_id)
);

CREATE TABLE IF NOT EXISTS telemetry_events (
  id TEXT PRIMARY KEY,
  key_id TEXT NOT NULL,
  installation_id TEXT DEFAULT '',
  workspace_hash TEXT DEFAULT '',
  run_hash TEXT DEFAULT '',
  idempotency_key TEXT NOT NULL UNIQUE,
  event_type TEXT NOT NULL DEFAULT 'command_completed',
  command_kind TEXT DEFAULT 'unknown',
  command_family TEXT DEFAULT 'unknown',
  original_tokens INTEGER NOT NULL DEFAULT 0,
  compressed_tokens INTEGER NOT NULL DEFAULT 0,
  saved_tokens INTEGER NOT NULL DEFAULT 0,
  compression_rate REAL NOT NULL DEFAULT 0,
  duration_ms INTEGER NOT NULL DEFAULT 0,
  exit_code INTEGER NOT NULL DEFAULT 0,
  success INTEGER NOT NULL DEFAULT 0,
  prediction_score REAL DEFAULT NULL,
  agent_count INTEGER NOT NULL DEFAULT 0,
  privacy_level INTEGER NOT NULL DEFAULT 1,
  client_created_at TEXT DEFAULT '',
  received_at TEXT NOT NULL,
  payload_json TEXT DEFAULT '{}',
  FOREIGN KEY (key_id) REFERENCES api_keys(key_id)
);

CREATE TABLE IF NOT EXISTS aggregate_daily (
  day TEXT NOT NULL,
  key_id TEXT NOT NULL,
  runs INTEGER NOT NULL DEFAULT 0,
  successful_runs INTEGER NOT NULL DEFAULT 0,
  failed_runs INTEGER NOT NULL DEFAULT 0,
  original_tokens INTEGER NOT NULL DEFAULT 0,
  compressed_tokens INTEGER NOT NULL DEFAULT 0,
  saved_tokens INTEGER NOT NULL DEFAULT 0,
  duration_ms INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, key_id),
  FOREIGN KEY (key_id) REFERENCES api_keys(key_id)
);

CREATE TABLE IF NOT EXISTS public_proof_snapshots (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_telemetry_key_received ON telemetry_events(key_id, received_at);
CREATE INDEX IF NOT EXISTS idx_telemetry_workspace ON telemetry_events(workspace_hash, received_at);
CREATE INDEX IF NOT EXISTS idx_telemetry_kind ON telemetry_events(command_kind, received_at);
CREATE INDEX IF NOT EXISTS idx_aggregate_daily_key ON aggregate_daily(key_id, day);

