# 🚀 SAGE API Deployment Instructions

## Step 1: Set GitHub OAuth Secret (REQUIRED)

**This prevents random people from generating API keys.**

```bash
# Set the GitHub OAuth app client secret in Cloudflare
wrangler secret put GITHUB_CLIENT_SECRET
```

**What this does:**
- Only requests with this master key can generate new API keys
- Your SAGE GUI uses GitHub OAuth instead of a built-in secret
- Public repo users do NOT have this key → Cannot generate keys

---

## Step 2: Run Database Migration

```bash
# Add security columns (expires_at, rate_limit, anomalies table)
wrangler d1 execute sage-telemetry-db --file=schema/security_hardening.sql
```

**What this does:**
- Adds `expires_at` column to `api_keys`
- Adds `rate_limit_per_hour` column
- Creates `api_key_anomalies` table for spike detection

---

## Step 3: Deploy Worker

```bash
# Deploy the updated worker with all security hardening
wrangler deploy
```

**What this does:**
- Deploys worker with:
  - ✅ Master key validation
  - ✅ Rate limiting (1000/hour)
  - ✅ Timestamp validation (5 min window)
  - ✅ Key expiration checks
  - ✅ CORS whitelist
  - ✅ Anomaly detection

---

## Step 4: Test

```bash
# Try connecting from SAGE GUI
sage connect --display-name "Test User"

# Should succeed with: ✅ SAGE API connected

# Try connecting WITHOUT master key (simulate hacker):
curl -X POST https://psyc-god-sage-api.valan-dj.workers.dev/v1/keys \
  -H "Content-Type: application/json" \
  -d '{"display_name": "Hacker"}'

# Should fail with: ❌ 403 Unauthorized - Key generation requires master key
```

---

## 🔒 Security Checklist

- [ ] GitHub OAuth secret set in Cloudflare (`GITHUB_CLIENT_SECRET`)
- [ ] Database migration applied (`security_hardening.sql`)
- [ ] Worker deployed (`wrangler deploy`)
- [ ] CORS origins verified in `worker.js`
- [ ] Test: GUI connection succeeds
- [ ] Test: Direct API call (without master key) fails

---

## 🔑 Master Key Management

**Current Master Key**: not stored in the repository.

**If compromised**:
1. Generate new master key: `openssl rand -hex 32`
2. Update Cloudflare: `wrangler secret put MASTER_KEY_SECRET`
3. Keep it out of client code and public docs
4. Redeploy the Worker

**Distribution Strategy**:
- Public clients use GitHub OAuth through `/v1/github-login`.
- The optional master key must stay only in Cloudflare/private admin environments.
- Never put the master key in Python client code, docs, screenshots, or public scripts.
  - Even if leaked, old keys remain valid (only NEW key generation blocked)
  - Rate limiting + expiration still protect existing keys

---

## 📊 Monitoring

**Check for anomalies**:
```sql
-- In Cloudflare D1
SELECT * FROM api_key_anomalies WHERE resolved_at = '';
```

**Check expired keys**:
```sql
SELECT key_id, expires_at FROM api_keys 
WHERE expires_at != '' AND expires_at < datetime('now');
```

**Check rate limit hits**:
```sql
SELECT key_id, COUNT(*) as requests
FROM telemetry_events
WHERE received_at > datetime('now', '-1 hour')
GROUP BY key_id
HAVING requests > 1000;
```

---

## ✅ Post-Deployment

After deployment, users can:
- ✅ Connect via SAGE GUI (has master key)
- ✅ Connect via CLI `sage login` (uses same master key)
- ❌ Connect via direct API call (no master key)
- ❌ Fork repo and generate keys (no master key in repo)

**Public repo is SAFE** ✅
