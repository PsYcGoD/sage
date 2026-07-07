# 🚀 SAGE Deployment Scripts

**Complete CLI automation for GitHub OAuth + Cloudflare deployment.**

---

## 🎯 Quick Start (One Command)

### Windows (PowerShell):
```powershell
.\scripts\complete_setup.ps1
```

### Linux/Mac (Bash):
```bash
chmod +x scripts/complete_setup.sh
./scripts/complete_setup.sh
```

**What it does:**
1. ✅ Checks prerequisites (gh CLI, wrangler)
2. ✅ Authenticates with GitHub
3. ✅ Creates GitHub OAuth App
4. ✅ Updates code with Client ID
5. ✅ Authenticates with Cloudflare
6. ✅ Sets Cloudflare secrets
7. ✅ Runs database migration
8. ✅ Deploys worker
9. ✅ Shows test instructions

---

## 📋 Prerequisites

### 1. GitHub CLI
```bash
# Windows
winget install GitHub.cli

# Mac
brew install gh

# Linux
sudo apt install gh
```

### 2. Wrangler CLI
```bash
npm install -g wrangler
```

---

## 🔧 Individual Scripts

### Setup GitHub OAuth App
```powershell
# Windows
.\scripts\setup_github_oauth.ps1

# Linux/Mac
./scripts/setup_github_oauth.sh
```

**What it does:**
- Creates GitHub OAuth App via `gh` CLI
- Saves credentials to `.sage-secrets/oauth.env`

---

### Deploy to Cloudflare
```powershell
# Windows
.\scripts\deploy_to_cloudflare.ps1

# Linux/Mac
./scripts/deploy_to_cloudflare.sh
```

**What it does:**
- Loads OAuth credentials from `.sage-secrets/oauth.env`
- Sets Cloudflare secrets (`GITHUB_CLIENT_SECRET`; optional admin `MASTER_KEY_SECRET` only if provided)
- Runs database migration
- Deploys worker

---

## 🧪 Testing After Deployment

### Test GitHub OAuth Flow:
```bash
sage connect

# Expected:
# 🔐 SAGE Connection - GitHub Authentication
# 🌐 Opening browser for GitHub login...
# ✅ GitHub authentication successful
# ✅ SAGE API connected
# GitHub: @YourUsername
# 🚀 Installing SAGE agent configs system-wide...
# ✅ All AI agents on this PC will now use SAGE
```

### Test Command Gating:
```bash
sage run -- pytest

# Before connection:
# ❌ SAGE requires API connection to use this command.
# Run: sage connect

# After connection:
# ✅ Executes with compression
```

---

## 🔐 Security Notes

### What Gets Stored:
- `.sage-secrets/oauth.env` - GitHub OAuth credentials (local only)
- Never committed to git (in .gitignore)

### What Goes to Cloudflare:
- `GITHUB_CLIENT_SECRET` - OAuth secret (environment variable)
- `MASTER_KEY_SECRET` - Optional admin-only key for private `/v1/keys` maintenance calls

### What Goes in Code:
- `GITHUB_CLIENT_ID` - Public OAuth client ID (not secret)
- Updated automatically by setup scripts

---

## 🔄 Rotating Secrets

### Regenerate GitHub OAuth App:
```bash
# Go to: https://github.com/settings/developers
# Click your app → "Regenerate client secret"
# Copy new secret

# Then update Cloudflare:
wrangler secret put GITHUB_CLIENT_SECRET
# Paste new secret
```

### Optional Admin Master Key:
```bash
# Generate new key:
openssl rand -hex 32

# Update Cloudflare:
wrangler secret put MASTER_KEY_SECRET

# Do not put this value in client code or public docs.
```

---

## 🐛 Troubleshooting

### "gh: command not found"
Install GitHub CLI:
- Windows: `winget install GitHub.cli`
- Mac: `brew install gh`
- Linux: `sudo apt install gh`

### "wrangler: command not found"
Install Wrangler:
```bash
npm install -g wrangler
```

### "gh auth status" fails
Authenticate with GitHub:
```bash
gh auth login
```

### "wrangler whoami" fails
Authenticate with Cloudflare:
```bash
wrangler login
```

### OAuth app creation fails
Create manually:
1. Go to: https://github.com/settings/developers
2. Click "New OAuth App"
3. Name: `SAGE-Smart-Agent-Guidance-Engine`
4. Homepage: `https://github.com/PsYcGoD/SAGE`
5. Callback: `http://localhost:8765/oauth/callback`
6. Copy Client ID and Secret
7. Run deploy script with manual input

---

## 📊 Monitoring Deployment

### Check Worker Status:
```bash
wrangler deployments list
```

### Check Secrets:
```bash
wrangler secret list
```

### Check Database:
```bash
wrangler d1 execute sage-telemetry-db --command "SELECT COUNT(*) FROM api_keys"
```

### View Logs:
```bash
wrangler tail
```

---

## 🎯 Next Steps After Deployment

1. ✅ Test connection: `sage connect`
2. ✅ Test command: `sage run -- pytest`
3. ✅ Check dashboard: `https://sage.api.marketingstudios.in/dashboard`
4. ✅ Monitor anomalies: Check Cloudflare D1 console

---

## 📚 Documentation

- `README.md` - User install and usage guide
- `AGENTS.md` - Repository command-routing and commit checklist
- `cloudflare/sage-api/DEPLOYMENT.md` - Cloudflare deployment guide

---

The scripts cover the normal deployment path. Review generated secrets and Cloudflare settings before publishing.
