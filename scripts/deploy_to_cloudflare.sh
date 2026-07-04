#!/bin/bash
# Deploy SAGE to Cloudflare with all secrets
# Requires: wrangler CLI, .sage-secrets/oauth.env

set -e

echo "🚀 SAGE Cloudflare Deployment"
echo "=========================================="
echo ""

# Check if wrangler is installed
if ! command -v wrangler &> /dev/null; then
    echo "❌ Wrangler CLI not installed"
    echo ""
    echo "Install it:"
    echo "  npm install -g wrangler"
    echo ""
    exit 1
fi

# Check if logged in to Cloudflare
if ! wrangler whoami &> /dev/null; then
    echo "🔑 Logging into Cloudflare..."
    wrangler login
fi

echo "✅ Wrangler authenticated"
echo ""

# Load OAuth secrets
if [ -f .sage-secrets/oauth.env ]; then
    source .sage-secrets/oauth.env
    echo "✅ Loaded OAuth credentials"
else
    echo "⚠️  No .sage-secrets/oauth.env found"
    echo "Run: ./scripts/setup_github_oauth.sh first"
    echo ""
    read -p "Enter GitHub Client ID: " GITHUB_CLIENT_ID
    read -sp "Enter GitHub Client Secret: " GITHUB_CLIENT_SECRET
    echo ""
fi

# Navigate to Cloudflare worker directory
cd cloudflare/sage-api

# Set secrets in Cloudflare
echo ""
echo "🔒 Setting Cloudflare secrets..."
echo ""

# GitHub OAuth credentials
if [ -n "$GITHUB_CLIENT_SECRET" ]; then
    echo "$GITHUB_CLIENT_SECRET" | wrangler secret put GITHUB_CLIENT_SECRET
    echo "✅ Set GITHUB_CLIENT_SECRET"
else
    echo "⚠️  GITHUB_CLIENT_SECRET not found"
    echo "Prompting for manual input..."
    wrangler secret put GITHUB_CLIENT_SECRET
fi

# Master key (for legacy login)
MASTER_KEY="${SAGE_MASTER_KEY_SECRET:-}"
if [ -n "$MASTER_KEY" ]; then
    echo "$MASTER_KEY" | wrangler secret put MASTER_KEY_SECRET
else
    echo "Skipping MASTER_KEY_SECRET; GitHub OAuth is the public key path"
fi

# Run database migration
echo ""
echo "📊 Running database migration..."
echo ""
wrangler d1 execute sage-telemetry-db --file=schema/security_hardening.sql
echo "✅ Database migration complete"

# Deploy worker
echo ""
echo "🚀 Deploying worker..."
echo ""
wrangler deploy
echo "✅ Worker deployed"

# Get deployment URL
WORKER_URL=$(wrangler deployments list --json 2>/dev/null | jq -r '.[0].url' || echo "https://sage-api.your-worker.dev")

echo ""
echo "=========================================="
echo "✅ Deployment Complete"
echo "=========================================="
echo ""
echo "Worker URL: $WORKER_URL"
echo "Dashboard: $WORKER_URL/dashboard"
echo ""
echo "Test connection:"
echo "  sage connect"
echo ""
echo "Check status:"
echo "  curl $WORKER_URL/health"
