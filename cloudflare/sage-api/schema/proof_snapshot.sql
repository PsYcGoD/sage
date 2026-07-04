CREATE TABLE IF NOT EXISTS public_proof_snapshots (
  id TEXT PRIMARY KEY,
  created_at TEXT NOT NULL,
  payload_json TEXT NOT NULL
);
