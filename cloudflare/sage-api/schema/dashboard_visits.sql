CREATE TABLE IF NOT EXISTS dashboard_visitors (
  visitor_hash TEXT PRIMARY KEY,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  visit_count INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS dashboard_visit_days (
  day TEXT NOT NULL,
  visitor_hash TEXT NOT NULL,
  first_seen_at TEXT NOT NULL,
  last_seen_at TEXT NOT NULL,
  visit_count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, visitor_hash)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_visit_days_day ON dashboard_visit_days(day);

CREATE TABLE IF NOT EXISTS dashboard_clicks (
  id TEXT PRIMARY KEY,
  visitor_hash TEXT NOT NULL,
  action TEXT NOT NULL DEFAULT '',
  target TEXT NOT NULL DEFAULT '',
  path TEXT NOT NULL DEFAULT '',
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dashboard_click_days (
  day TEXT NOT NULL,
  action TEXT NOT NULL DEFAULT '',
  click_count INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (day, action)
);

CREATE INDEX IF NOT EXISTS idx_dashboard_clicks_created ON dashboard_clicks(created_at);
CREATE INDEX IF NOT EXISTS idx_dashboard_click_days_day ON dashboard_click_days(day);
