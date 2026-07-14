# SAGE activation funnel tracking

Goal: measure where people drop off between discovery and repeated usage.

## Funnel stages

| Stage | Event/source | Counts as converted when |
|---|---|---|
| View | GitHub traffic + public dashboard visitors | User views repo, README, dashboard, or landing page |
| Install/connect | `api_keys.created_at` + `installations.first_seen_at` | SAGE creates/connects a key for a machine |
| First command | `telemetry_events` | First `command_completed` event for an installation |
| Second command | `telemetry_events` | Second `command_completed` event for the same installation |
| Activated | `telemetry_events` | At least 5 commands or at least 1,000 saved tokens |
| Retained | `telemetry_events` | A command event on a later day |

## Recommended events

Use the existing telemetry tables where possible. Add explicit events only for gaps.

| Event | When to send | Privacy |
|---|---|---|
| `install_connected` | API key/machine first created | Machine hash, version, platform only |
| `demo_viewed` | User runs `sage demo` | No command text |
| `first_command_completed` | First command for an installation | Aggregate command family/kind only |
| `second_command_completed` | Second command for an installation | Aggregate command family/kind only |
| `activation_reached` | 5 commands or 1,000 saved tokens | Counts only |

## Dashboard cards

Show these in `sage api visitors` or an admin-only `sage api funnel` command:

| Metric | Meaning |
|---|---|
| Repo unique viewers | GitHub interest |
| Git clones | High-intent external interest |
| Connected installs | Install/connect conversion |
| First-command machines | People who actually used SAGE |
| Second-command machines | People who understood enough to retry |
| Activated machines | Real value reached |
| 24h retained machines | Recent returning users |

## SQL sketch

```sql
WITH install_first AS (
  SELECT installation_id, MIN(first_seen_at) AS installed_at
  FROM installations
  GROUP BY installation_id
),
event_counts AS (
  SELECT
    installation_id,
    COUNT(*) AS commands,
    SUM(saved_tokens) AS saved_tokens,
    MIN(received_at) AS first_command_at,
    MAX(received_at) AS last_command_at,
    COUNT(DISTINCT substr(received_at, 1, 10)) AS active_days
  FROM telemetry_events
  GROUP BY installation_id
)
SELECT
  COUNT(*) AS installs,
  SUM(CASE WHEN commands >= 1 THEN 1 ELSE 0 END) AS first_command,
  SUM(CASE WHEN commands >= 2 THEN 1 ELSE 0 END) AS second_command,
  SUM(CASE WHEN commands >= 5 OR saved_tokens >= 1000 THEN 1 ELSE 0 END) AS activated,
  SUM(CASE WHEN active_days >= 2 THEN 1 ELSE 0 END) AS retained
FROM install_first i
LEFT JOIN event_counts e ON e.installation_id = i.installation_id;
```

## Why this matters

GitHub clones are not active users. The core activation question is:

```text
Of people who install/connect SAGE, how many run command #1 and command #2?
```

If first command is low, onboarding/install is unclear.
If second command is low, first-run value is unclear.
If activation is low, the demo or default command suggestions are weak.
