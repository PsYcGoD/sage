# 🔐 GitHub OAuth Setup for SAGE

Sensei, here's how to create the GitHub OAuth App.

---

## Step 1: Create GitHub OAuth App

1. Go to: https://github.com/settings/developers
2. Click **"New OAuth App"**
3. Fill in:

```
Application name: SAGE - Smart Agent Guidance Engine
Homepage URL: https://github.com/PsYcGoD/SAGE
Authorization callback URL: http://localhost:8765/oauth/callback
Application description: AI development orchestration with 99.3% token compression
```

4. Click **"Register application"**
5. You'll get:
   - **Client ID**: `Ov23liZfR9tJyKzN8xYZ` (public - goes in code)
   - **Client Secret**: `<click Generate>` (private - goes in Cloudflare)

---

## Step 2: Update Code with Client ID

Already done in `src/sage/github_oauth.py`:

```python
GITHUB_CLIENT_ID = "Ov23liZfR9tJyKzN8xYZ"  # Replace with YOUR client ID
```

And in `cloudflare/sage-api/src/worker.js`:

```javascript
client_id: "Ov23liZfR9tJyKzN8xYZ",  // Replace with YOUR client ID
```

---

## Step 3: Set Client Secret in Cloudflare

```bash
cd cloudflare/sage-api

# Set GitHub client secret
wrangler secret put GITHUB_CLIENT_SECRET
# When prompted, paste the secret from GitHub

# Also set master key (for legacy login)
wrangler secret put MASTER_KEY_SECRET
# When prompted, paste: sage_master_2026_psycgod_ai_ml_secure_key_generation_v1
```

---

## Step 4: Run Database Migration

```bash
# Add GitHub columns to api_keys table
wrangler d1 execute sage-telemetry-db --file=schema/security_hardening.sql
```

**What this adds:**
- `github_id` column
- `github_username` column
- `expires_at` column
- `api_key_anomalies` table

---

## Step 5: Deploy

```bash
wrangler deploy
```

---

## Step 6: Test

### Test GitHub OAuth Flow:

```bash
sage connect

# Expected flow:
# 1. Opens browser to GitHub
# 2. You click "Authorize"
# 3. Browser redirects to localhost:8765
# 4. ✅ SAGE API connected
# 5. GitHub: @YourUsername
# 6. ✅ Agent configs installed
```

### Test CLI Commands (Should Be Blocked):

```bash
sage run -- pytest

# Expected:
# ❌ SAGE requires API connection to use this command.
# Run: sage connect
```

---

## Security Model

### GitHub OAuth Flow:

```
User runs: sage connect
  ↓
1. SAGE CLI generates state token
2. Opens browser: github.com/login/oauth/authorize?client_id=...
3. User clicks "Authorize"
4. GitHub redirects: localhost:8765/oauth/callback?code=abc123
5. SAGE CLI captures auth code
6. Sends to Cloudflare: POST /v1/github-login {github_auth_code: "abc123"}
7. Cloudflare exchanges code for access token (using client secret)
8. Cloudflare fetches GitHub user info
9. Cloudflare checks: Does this GitHub ID already have a key?
   - YES → Return existing key info
   - NO → Generate new API key
10. Cloudflare stores: github_id, github_username in api_keys table
11. Returns API key to CLI
12. CLI stores key locally
13. CLI installs agent configs system-wide
```

### 1 Account = 1 API Key:

```sql
-- Database constraint
SELECT * FROM api_keys WHERE github_id = '12345' AND revoked_at = '';

-- If found: User already has key
-- If not found: Generate new key
```

### Key Rotation:

```bash
sage api rotate

# What happens:
# 1. Revokes old key (sets revoked_at = NOW())
# 2. Generates new key with same GitHub ID
# 3. Same github_id, different key_id
```

---

## What Public Repo Users Get

### Without GitHub Auth:

```bash
git clone https://github.com/PsYcGoD/SAGE
pip install -e .
sage run -- pytest

# ❌ SAGE requires API connection to use this command.
# Run: sage connect
```

### After `sage connect`:

```bash
sage connect
# Opens browser → GitHub login
# ✅ Authenticated with YOUR GitHub account
# ✅ API key generated (tied to YOUR GitHub ID)
# ✅ Agent configs installed

sage run -- pytest
# ✅ Works with compression
```

---

## Rate Limiting per GitHub Account

```javascript
// In handleGitHubLogin()
const existingKey = await env.DB.prepare(
  "SELECT * FROM api_keys WHERE github_id = ? AND revoked_at = ''"
).bind(githubId).first();

if (existingKey) {
  // User already has a key - cannot generate multiple
  return json({
    ok: true,
    message: "GitHub account already connected. Use 'sage api rotate' to generate new key."
  });
}
```

**Benefits:**
- ✅ 1 GitHub account = 1 API key
- ✅ Cannot generate unlimited keys
- ✅ Easy to ban abusive users (revoke by github_id)
- ✅ Easy to track who's using SAGE (github_username)

---

## Monitoring

### Check GitHub users:

```sql
SELECT github_username, key_id, created_at, expires_at
FROM api_keys
WHERE github_id != ''
ORDER BY created_at DESC;
```

### Check duplicate attempts:

```sql
SELECT github_id, COUNT(*) as key_count
FROM api_keys
WHERE github_id != ''
GROUP BY github_id
HAVING key_count > 1;
```

---

## FAQ

**Q: Can users fake the GitHub OAuth?**
**A:** No. The client secret is in Cloudflare (not in repo). Without it, they can't exchange auth code for access token.

**Q: Can users generate multiple keys with different GitHub accounts?**
**A:** Yes, but you can ban by email domain or require org membership.

**Q: What if I want to limit to specific GitHub orgs?**
**A:** Add this check in `handleGitHubLogin()`:

```javascript
// Check org membership
const orgsResponse = await fetch("https://api.github.com/user/orgs", {
  headers: { "Authorization": `Bearer ${githubToken}` }
});
const orgs = await orgsResponse.json();

const allowedOrg = "YourOrgName";
if (!orgs.some(org => org.login === allowedOrg)) {
  return error("GitHub account must be member of " + allowedOrg, 403);
}
```

---

## ✅ Final Checklist

- [ ] GitHub OAuth App created
- [ ] Client ID updated in code
- [ ] Client Secret set in Cloudflare (`GITHUB_CLIENT_SECRET`)
- [ ] Master Key set in Cloudflare (`MASTER_KEY_SECRET`)
- [ ] Database migration applied
- [ ] Worker deployed
- [ ] Test: `sage connect` works
- [ ] Test: `sage run` blocked without connection
- [ ] Test: Agent configs installed after connection

---

**Deploy now, Sensei?** 🚀

Commands to run:
```bash
cd cloudflare/sage-api
wrangler secret put GITHUB_CLIENT_SECRET
wrangler secret put MASTER_KEY_SECRET
wrangler d1 execute sage-telemetry-db --file=schema/security_hardening.sql
wrangler deploy
```
