-- 🔒 Security Hardening: Add key expiration, rate limiting, and GitHub OAuth
-- Run this migration to add new security columns to api_keys table

-- Add expires_at column (ISO 8601 timestamp when key expires)
ALTER TABLE api_keys ADD COLUMN expires_at TEXT DEFAULT '';

-- Add GitHub OAuth columns
ALTER TABLE api_keys ADD COLUMN github_id TEXT DEFAULT '';
ALTER TABLE api_keys ADD COLUMN github_username TEXT DEFAULT '';

-- Note: rate_limit_per_hour already exists in schema.sql with DEFAULT 1000
-- If you need to update existing keys, run:
-- UPDATE api_keys SET rate_limit_per_hour = 1000 WHERE rate_limit_per_hour IS NULL;

-- Add anomaly detection tracking table
CREATE TABLE IF NOT EXISTS api_key_anomalies (
  id TEXT PRIMARY KEY,
  key_id TEXT NOT NULL,
  detected_at TEXT NOT NULL,
  anomaly_type TEXT NOT NULL, -- 'rate_spike', 'unusual_pattern', 'multiple_ips'
  description TEXT DEFAULT '',
  severity TEXT NOT NULL DEFAULT 'medium', -- 'low', 'medium', 'high'
  auto_action TEXT DEFAULT '', -- 'none', 'throttle', 'suspend'
  resolved_at TEXT DEFAULT '',
  FOREIGN KEY (key_id) REFERENCES api_keys(key_id)
);

CREATE INDEX IF NOT EXISTS idx_anomalies_key_detected ON api_key_anomalies(key_id, detected_at);
CREATE INDEX IF NOT EXISTS idx_anomalies_unresolved ON api_key_anomalies(resolved_at) WHERE resolved_at = '';

-- Set default expiration for existing keys (30 days from now)
-- UPDATE api_keys SET expires_at = datetime('now', '+30 days') WHERE expires_at = '' OR expires_at IS NULL;
