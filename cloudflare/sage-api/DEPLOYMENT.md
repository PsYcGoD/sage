# SAGE API Deployment Instructions

SAGE API uses SAGE machine authentication for public clients. No GitHub auth
app or browser login is required for CLI, GUI, npm, or PyPI installs.

## 1. Apply database migration

```bash
wrangler d1 execute sage_telemetry --file=schema/security_hardening.sql
```

The migration keeps rate limits, expiration fields, anomaly tracking, and
legacy identity columns needed for existing data.

## 2. Deploy Worker

```bash
wrangler deploy
```

The Worker exposes:

- `POST /v1/machine-login` for SAGE machine authentication.
- `POST /v1/telemetry` for safe aggregate telemetry.
- `GET /dashboard` and `GET /install` for public proof/install pages.
- Private admin endpoints guarded by API keys.

## 3. Test machine login

```bash
sage connect
sage api whoami
```

Expected result: SAGE stores a local API key, sets anonymous metrics mode, and
server verification passes.

## 4. Security checklist

- [ ] Database migration applied.
- [ ] Worker deployed.
- [ ] `/v1/machine-login` works from CLI.
- [ ] `/v1/telemetry` accepts valid SAGE API keys.
- [ ] Admin endpoints reject non-admin keys.
- [ ] CORS origins are intentional.
- [ ] No secrets are committed to the repository.

## 5. Monitoring

Check unresolved anomalies:

```sql
SELECT * FROM api_key_anomalies WHERE resolved_at = '';
```

Check expired keys:

```sql
SELECT key_id, expires_at
FROM api_keys
WHERE expires_at != '' AND expires_at < datetime('now');
```

Check high request volume:

```sql
SELECT key_id, COUNT(*) AS requests
FROM telemetry_events
WHERE received_at > datetime('now', '-1 hour')
GROUP BY key_id
HAVING requests > 1000;
```
