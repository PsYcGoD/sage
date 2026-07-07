# SAGE GitHub OAuth Setup - Complete PowerShell CLI Automation
# Run this script to set up everything via GitHub CLI

$ErrorActionPreference = "Stop"

Write-Host "🔐 SAGE GitHub OAuth Setup" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# Check if gh CLI is installed
if (-not (Get-Command gh -ErrorAction SilentlyContinue)) {
    Write-Host "❌ GitHub CLI (gh) not installed" -ForegroundColor Red
    Write-Host ""
    Write-Host "Install it:"
    Write-Host "  Windows: winget install GitHub.cli"
    Write-Host "  Or download: https://cli.github.com/"
    Write-Host ""
    exit 1
}

# Check if logged in
try {
    gh auth status *>$null
    Write-Host "✅ GitHub CLI authenticated" -ForegroundColor Green
} catch {
    Write-Host "🔑 Logging into GitHub..." -ForegroundColor Yellow
    gh auth login
}

Write-Host ""

# OAuth App details
$OAUTH_APP_NAME = "SAGE-Smart-Agent-Guidance-Engine"
$HOMEPAGE_URL = "https://github.com/PsYcGoD/SAGE"
$CALLBACK_URL = "http://localhost:8765/oauth/callback"
$DESCRIPTION = "Local-first AI development orchestration with terminal-output compression. Requires OAuth for API access."

Write-Host "📱 Creating GitHub OAuth App..." -ForegroundColor Cyan
Write-Host ""

# Check if app already exists
$existingApps = gh api -X GET /user/applications 2>$null | ConvertFrom-Json
$existingApp = $existingApps | Where-Object { $_.name -eq $OAUTH_APP_NAME }

if ($existingApp) {
    Write-Host "ℹ️  OAuth App already exists" -ForegroundColor Yellow
    Write-Host "Client ID: $($existingApp.client_id)"
    Write-Host ""
    Write-Host "Get client secret from: https://github.com/settings/developers"
    $CLIENT_ID = $existingApp.client_id
} else {
    Write-Host "Creating new OAuth App: $OAUTH_APP_NAME" -ForegroundColor Yellow

    # Create new OAuth App via GitHub API
    $body = @{
        name = $OAUTH_APP_NAME
        url = $HOMEPAGE_URL
        callback_url = $CALLBACK_URL
        description = $DESCRIPTION
    } | ConvertTo-Json

    try {
        $response = gh api `
            --method POST `
            -H "Accept: application/vnd.github+json" `
            /user/applications `
            --input - `
            2>&1 << $body | ConvertFrom-Json

        $CLIENT_ID = $response.client_id
        $CLIENT_SECRET = $response.client_secret

        Write-Host "✅ OAuth App created" -ForegroundColor Green
        Write-Host "Client ID: $CLIENT_ID"
        Write-Host "Client Secret: $CLIENT_SECRET"
        Write-Host ""

        # Save to file for later use
        New-Item -ItemType Directory -Force -Path .sage-secrets | Out-Null
        Set-Content -Path .sage-secrets/oauth.env -Value @"
GITHUB_CLIENT_ID=$CLIENT_ID
GITHUB_CLIENT_SECRET=$CLIENT_SECRET
"@

        Write-Host "✅ Saved to .sage-secrets/oauth.env (add to .gitignore)" -ForegroundColor Green
    } catch {
        Write-Host "❌ Failed to create OAuth App" -ForegroundColor Red
        Write-Host "Error: $_"
        Write-Host ""
        Write-Host "Manual steps:"
        Write-Host "1. Go to: https://github.com/settings/developers"
        Write-Host "2. Click 'New OAuth App'"
        Write-Host "3. Use these values:"
        Write-Host "   Name: $OAUTH_APP_NAME"
        Write-Host "   Homepage: $HOMEPAGE_URL"
        Write-Host "   Callback: $CALLBACK_URL"
        exit 1
    }
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "✅ GitHub OAuth App Ready" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:"
Write-Host "1. Update code with Client ID"
Write-Host "2. Set Cloudflare secrets"
Write-Host "3. Deploy to Cloudflare"
Write-Host ""
Write-Host "Run: .\scripts\deploy_to_cloudflare.ps1"
