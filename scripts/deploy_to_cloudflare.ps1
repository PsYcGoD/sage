# Deploy SAGE to Cloudflare with all secrets
# Requires: wrangler CLI, .sage-secrets/oauth.env

$ErrorActionPreference = "Stop"

Write-Host "🚀 SAGE Cloudflare Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if wrangler is installed
if (-not (Get-Command wrangler -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Wrangler CLI not installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install it:"
    Write-Host "  npm install -g wrangler"
    Write-Host ""
    exit 1
}

# Check if logged in to Cloudflare
try {
    wrangler whoami *>$null
    Write-Host "✅ Wrangler authenticated" -ForegroundColor Green
} catch {
    Write-Host "🔑 Logging into Cloudflare..." -ForegroundColor Yellow
    wrangler login
}

Write-Host ""

# Load OAuth secrets
$GITHUB_CLIENT_SECRET = $null
if (Test-Path .sage-secrets/oauth.env) {
    Get-Content .sage-secrets/oauth.env | ForEach-Object {
        if ($_ -match '^GITHUB_CLIENT_SECRET=(.+)$') {
            $GITHUB_CLIENT_SECRET = $matches[1]
        }
    }
    Write-Host "✅ Loaded OAuth credentials" -ForegroundColor Green
} else {
    Write-Host "⚠️  No .sage-secrets/oauth.env found" -ForegroundColor Yellow
    Write-Host "Run: .\scripts\setup_github_oauth.ps1 first"
    Write-Host ""
    $GITHUB_CLIENT_SECRET = Read-Host "Enter GitHub Client Secret" -AsSecureString
    $GITHUB_CLIENT_SECRET = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($GITHUB_CLIENT_SECRET))
}

# Navigate to Cloudflare worker directory
Push-Location cloudflare/sage-api

try {
    # Set secrets in Cloudflare
    Write-Host ""
    Write-Host "🔒 Setting Cloudflare secrets..." -ForegroundColor Cyan
    Write-Host ""

    # GitHub OAuth credentials
    if ($GITHUB_CLIENT_SECRET) {
        $GITHUB_CLIENT_SECRET | wrangler secret put GITHUB_CLIENT_SECRET
        Write-Host "✅ Set GITHUB_CLIENT_SECRET" -ForegroundColor Green
    } else {
        Write-Host "⚠️  GITHUB_CLIENT_SECRET not found" -ForegroundColor Yellow
        Write-Host "Prompting for manual input..."
        wrangler secret put GITHUB_CLIENT_SECRET
    }

    # Master key (for legacy login)
    $MASTER_KEY = "sage_master_2026_psycgod_ai_ml_secure_key_generation_v1"
    $MASTER_KEY | wrangler secret put MASTER_KEY_SECRET
    Write-Host "✅ Set MASTER_KEY_SECRET" -ForegroundColor Green

    # Run database migration
    Write-Host ""
    Write-Host "📊 Running database migration..." -ForegroundColor Cyan
    Write-Host ""
    wrangler d1 execute sage-telemetry-db --file=schema/security_hardening.sql
    Write-Host "✅ Database migration complete" -ForegroundColor Green

    # Deploy worker
    Write-Host ""
    Write-Host "🚀 Deploying worker..." -ForegroundColor Cyan
    Write-Host ""
    wrangler deploy
    Write-Host "✅ Worker deployed" -ForegroundColor Green

    # Get deployment URL (try to extract from wrangler output)
    $WORKER_URL = "https://sage-api.your-worker.dev"
    Write-Host ""
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host "✅ Deployment Complete" -ForegroundColor Green
    Write-Host "==========================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Worker URL: $WORKER_URL"
    Write-Host "Dashboard: $WORKER_URL/dashboard"
    Write-Host ""
    Write-Host "Test connection:"
    Write-Host "  sage connect"
    Write-Host ""
    Write-Host "Check status:"
    Write-Host "  curl $WORKER_URL/health"

} finally {
    Pop-Location
}
