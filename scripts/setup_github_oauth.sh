#!/bin/bash
# SAGE GitHub OAuth Setup - Complete CLI Automation
# Run this script to set up everything via GitHub CLI

set -e  # Exit on error

echo "🔐 SAGE GitHub OAuth Setup"
echo "=========================================="
echo ""

# Check if gh CLI is installed
if ! command -v gh &> /dev/null; then
    echo "❌ GitHub CLI (gh) not installed"
    echo ""
    echo "Install it:"
    echo "  Windows: winget install GitHub.cli"
    echo "  Mac: brew install gh"
    echo "  Linux: sudo apt install gh"
    echo ""
    exit 1
fi

# Check if logged in
if ! gh auth status &> /dev/null; then
    echo "🔑 Logging into GitHub..."
    gh auth login
fi

echo "✅ GitHub CLI authenticated"
echo ""

# Create OAuth App
echo "📱 Creating GitHub OAuth App..."
echo ""

OAUTH_APP_NAME="SAGE-Smart-Agent-Guidance-Engine"
HOMEPAGE_URL="https://github.com/PsYcGoD/SAGE"
CALLBACK_URL="http://localhost:8765/oauth/callback"
DESCRIPTION="Local-first AI development orchestration with terminal-output compression. Requires OAuth for API access."

# Check if app already exists
EXISTING_APP=$(gh api -X GET /user/applications 2>/dev/null | jq -r ".[] | select(.name==\"$OAUTH_APP_NAME\") | .client_id" || echo "")

if [ -n "$EXISTING_APP" ]; then
    echo "ℹ️  OAuth App already exists"
    echo "Client ID: $EXISTING_APP"
    echo ""
    echo "Get client secret from: https://github.com/settings/developers"
    CLIENT_ID="$EXISTING_APP"
else
    # Create new OAuth App via GitHub API
    echo "Creating new OAuth App: $OAUTH_APP_NAME"

    OAUTH_RESPONSE=$(gh api \
        --method POST \
        -H "Accept: application/vnd.github+json" \
        /user/applications \
        -f name="$OAUTH_APP_NAME" \
        -f url="$HOMEPAGE_URL" \
        -f callback_url="$CALLBACK_URL" \
        -f description="$DESCRIPTION" 2>&1)

    if [ $? -eq 0 ]; then
        CLIENT_ID=$(echo "$OAUTH_RESPONSE" | jq -r '.client_id')
        CLIENT_SECRET=$(echo "$OAUTH_RESPONSE" | jq -r '.client_secret')

        echo "✅ OAuth App created"
        echo "Client ID: $CLIENT_ID"
        echo "Client Secret: $CLIENT_SECRET"
        echo ""

        # Save to file for later use
        mkdir -p .sage-secrets
        echo "GITHUB_CLIENT_ID=$CLIENT_ID" > .sage-secrets/oauth.env
        echo "GITHUB_CLIENT_SECRET=$CLIENT_SECRET" >> .sage-secrets/oauth.env
        chmod 600 .sage-secrets/oauth.env

        echo "✅ Saved to .sage-secrets/oauth.env (add to .gitignore)"
    else
        echo "❌ Failed to create OAuth App"
        echo "Error: $OAUTH_RESPONSE"
        echo ""
        echo "Manual steps:"
        echo "1. Go to: https://github.com/settings/developers"
        echo "2. Click 'New OAuth App'"
        echo "3. Use these values:"
        echo "   Name: $OAUTH_APP_NAME"
        echo "   Homepage: $HOMEPAGE_URL"
        echo "   Callback: $CALLBACK_URL"
        exit 1
    fi
fi

echo ""
echo "=========================================="
echo "✅ GitHub OAuth App Ready"
echo "=========================================="
echo ""
echo "Next steps:"
echo "1. Update code with Client ID"
echo "2. Set Cloudflare secrets"
echo "3. Deploy to Cloudflare"
echo ""
echo "Run: ./scripts/deploy_to_cloudflare.sh"
