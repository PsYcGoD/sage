# SAGE Complete Setup - One Command Does Everything
# Automates: GitHub OAuth App creation + Cloudflare deployment

$ErrorActionPreference = "Stop"

Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║                                                           ║" -ForegroundColor Cyan
Write-Host "║        🚀 SAGE Complete Deployment Automation 🚀          ║" -ForegroundColor Cyan
Write-Host "║                                                           ║" -ForegroundColor Cyan
Write-Host "║  • GitHub OAuth App Creation (gh CLI)                    ║" -ForegroundColor Cyan
Write-Host "║  • Cloudflare Secrets Configuration                      ║" -ForegroundColor Cyan
Write-Host "║  • Database Migration                                    ║" -ForegroundColor Cyan
Write-Host "║  • Worker Deployment                                     ║" -ForegroundColor Cyan
Write-Host "║                                                           ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# ============================================================
# STEP 1: Check Prerequisites
# ============================================================
Write-Host "📋 Step 1: Checking prerequisites..." -ForegroundColor Yellow
Write-Host ""

$missing = @()

if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    $missing += "GitHub CLI (gh) - Install: winget install GitHub.cli"
}

if (-not (Get-Command wrangler -ErrorAction SilentlyContinue)) {
    $missing += "Wrangler CLI - Install: npm install -g wrangler"
}

if ($missing.Count -gt 0) {
    Write-Host "❌ Missing required tools:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "   • $_" -ForegroundColor Red }
    Write-Host ""
    exit 1
}

Write-Host "✅ All prerequisites installed" -ForegroundColor Green
Write-Host ""

# ============================================================
# STEP 2: Authenticate with GitHub
# ============================================================
Write-Host "📋 Step 2: Authenticating with GitHub..." -ForegroundColor Yellow
Write-Host ""

try {
    gh auth status *>$null
    Write-Host "✅ Already logged into GitHub" -ForegroundColor Green
} catch {
    Write-Host "🔑 Please log into GitHub..." -ForegroundColor Yellow
    gh auth login
    Write-Host "✅ GitHub authentication complete" -ForegroundColor Green
}

Write-Host ""

# ============================================================
# STEP 3: Create GitHub OAuth App
# ============================================================
Write-Host "📋 Step 3: Creating GitHub OAuth App..." -ForegroundColor Yellow
Write-Host ""

$OAUTH_APP_NAME = "SAGE-Smart-Agent-Guidance-Engine"
$HOMEPAGE_URL = "https://github.com/PsYcGoD/SAGE"
$CALLBACK_URL = "http://localhost:8765/oauth/callback"

# Check if app already exists
$existingApps = gh api -X GET /user/applications 2>$null | ConvertFrom-Json
$existingApp = $existingApps | Where-Object { $_.name -eq $OAUTH_APP_NAME }

if ($existingApp) {
    Write-Host "ℹ️  OAuth App already exists" -ForegroundColor Yellow
    Write-Host "   Client ID: $($existingApp.client_id)" -ForegroundColor Gray
    $CLIENT_ID = $existingApp.client_id

    Write-Host ""
    Write-Host "⚠️  Cannot retrieve existing client secret via API" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Please get it from: https://github.com/settings/developers" -ForegroundColor Yellow
    Write-Host "Then regenerate it if needed, and enter below."
    Write-Host ""

    $secureSecret = Read-Host "Enter GitHub Client Secret" -AsSecureString
    $CLIENT_SECRET = [Runtime.InteropServices.Marshal]::PtrToStringAuto(
        [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secureSecret))
} else {
    Write-Host "Creating new OAuth App: $OAUTH_APP_NAME" -ForegroundColor Cyan

    $payload = @{
        name = $OAUTH_APP_NAME
        url = $HOMEPAGE_URL
        callback_url = $CALLBACK_URL
        description = "AI development orchestration with 99.3% token compression"
    } | ConvertTo-Json -Compress

    try {
        $tempFile = New-TemporaryFile
        Set-Content -Path $tempFile -Value $payload -NoNewline

        $response = gh api `
            --method POST `
            -H "Accept: application/vnd.github+json" `
            /user/applications `
            --input $tempFile 2>&1 | ConvertFrom-Json

        Remove-Item $tempFile

        $CLIENT_ID = $response.client_id
        $CLIENT_SECRET = $response.client_secret

        Write-Host "✅ OAuth App created successfully" -ForegroundColor Green
        Write-Host "   Client ID: $CLIENT_ID" -ForegroundColor Gray
        Write-Host "   Client Secret: $CLIENT_SECRET" -ForegroundColor Gray
    } catch {
        Write-Host "❌ Failed to create OAuth App" -ForegroundColor Red
        Write-Host "Error: $_" -ForegroundColor Red
        Write-Host ""
        Write-Host "Please create manually:"
        Write-Host "1. Go to: https://github.com/settings/developers"
        Write-Host "2. Click 'New OAuth App'"
        Write-Host "3. Name: $OAUTH_APP_NAME"
        Write-Host "4. Homepage: $HOMEPAGE_URL"
        Write-Host "5. Callback: $CALLBACK_URL"
        exit 1
    }
}

# Save credentials
New-Item -ItemType Directory -Force -Path .sage-secrets | Out-Null
Set-Content -Path .sage-secrets/oauth.env -Value @"
GITHUB_CLIENT_ID=$CLIENT_ID
GITHUB_CLIENT_SECRET=$CLIENT_SECRET
"@

# Update code files with Client ID
Write-Host ""
Write-Host "🔧 Updating code with Client ID..." -ForegroundColor Cyan

# Update src/sage/github_oauth.py
$oauthFile = "src/sage/github_oauth.py"
if (Test-Path $oauthFile) {
    $content = Get-Content $oauthFile -Raw
    $content = $content -replace 'GITHUB_CLIENT_ID = ".*?"', "GITHUB_CLIENT_ID = `"$CLIENT_ID`""
    Set-Content $oauthFile -Value $content -NoNewline
    Write-Host "✅ Updated $oauthFile" -ForegroundColor Green
}

# Update cloudflare/sage-api/src/worker.js
$workerFile = "cloudflare/sage-api/src/worker.js"
if (Test-Path $workerFile) {
    $content = Get-Content $workerFile -Raw
    $content = $content -replace 'client_id: ".*?"', "client_id: `"$CLIENT_ID`""
    Set-Content $workerFile -Value $content -NoNewline
    Write-Host "✅ Updated $workerFile" -ForegroundColor Green
}

Write-Host ""

# ============================================================
# STEP 4: Authenticate with Cloudflare
# ============================================================
Write-Host "📋 Step 4: Authenticating with Cloudflare..." -ForegroundColor Yellow
Write-Host ""

try {
    wrangler whoami *>$null
    Write-Host "✅ Already logged into Cloudflare" -ForegroundColor Green
} catch {
    Write-Host "🔑 Please log into Cloudflare..." -ForegroundColor Yellow
    wrangler login
    Write-Host "✅ Cloudflare authentication complete" -ForegroundColor Green
}

Write-Host ""

# ============================================================
# STEP 5: Deploy to Cloudflare
# ============================================================
Write-Host "📋 Step 5: Deploying to Cloudflare..." -ForegroundColor Yellow
Write-Host ""

Push-Location cloudflare/sage-api

try {
    # Set GitHub Client Secret
    Write-Host "🔒 Setting GITHUB_CLIENT_SECRET..." -ForegroundColor Cyan
    $CLIENT_SECRET | wrangler secret put GITHUB_CLIENT_SECRET
    Write-Host "✅ GITHUB_CLIENT_SECRET set" -ForegroundColor Green

    # Set Master Key
    Write-Host "🔒 Setting MASTER_KEY_SECRET..." -ForegroundColor Cyan
    $MASTER_KEY = $env:SAGE_MASTER_KEY_SECRET
    if ($MASTER_KEY) {
        $MASTER_KEY | wrangler secret put MASTER_KEY_SECRET
    } else {
        Write-Host "Skipping MASTER_KEY_SECRET; GitHub OAuth is the public key path" -ForegroundColor Yellow
    }

    # Run database migration
    Write-Host ""
    Write-Host "📊 Running database migration..." -ForegroundColor Cyan
    wrangler d1 execute sage-telemetry-db --file=schema/security_hardening.sql
    Write-Host "✅ Database migration complete" -ForegroundColor Green

    # Deploy worker
    Write-Host ""
    Write-Host "🚀 Deploying worker..." -ForegroundColor Cyan
    wrangler deploy
    Write-Host "✅ Worker deployed" -ForegroundColor Green

} finally {
    Pop-Location
}

# ============================================================
# DEPLOYMENT COMPLETE
# ============================================================
Write-Host ""
Write-Host "╔═══════════════════════════════════════════════════════════╗" -ForegroundColor Green
Write-Host "║                                                           ║" -ForegroundColor Green
Write-Host "║            ✅ DEPLOYMENT COMPLETE! ✅                     ║" -ForegroundColor Green
Write-Host "║                                                           ║" -ForegroundColor Green
Write-Host "╚═══════════════════════════════════════════════════════════╝" -ForegroundColor Green
Write-Host ""
Write-Host "📋 What was deployed:" -ForegroundColor Cyan
Write-Host "   • GitHub OAuth App: $OAUTH_APP_NAME" -ForegroundColor Gray
Write-Host "   • Client ID: $CLIENT_ID" -ForegroundColor Gray
Write-Host "   • Cloudflare Worker: sage-api" -ForegroundColor Gray
Write-Host "   • Database: sage-telemetry-db" -ForegroundColor Gray
Write-Host ""
Write-Host "🧪 Test your deployment:" -ForegroundColor Cyan
Write-Host "   sage connect" -ForegroundColor Yellow
Write-Host ""
Write-Host "📚 Documentation:" -ForegroundColor Cyan
Write-Host "   • README.md" -ForegroundColor Gray
Write-Host "   • AGENTS.md" -ForegroundColor Gray
Write-Host ""
Write-Host "🎉 Users can now authenticate with GitHub!" -ForegroundColor Green
Write-Host ""
