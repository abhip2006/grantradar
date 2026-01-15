#!/bin/bash
set -e

echo "=========================================="
echo "   GrantRadar Railway Deployment Script   "
echo "=========================================="

# Check if logged in
echo ""
echo "Checking Railway login status..."
if ! railway whoami &>/dev/null; then
    echo "Error: Not logged in to Railway. Run 'railway login' first."
    exit 1
fi

echo "Logged in as: $(railway whoami)"
echo ""

# Step 1: Initialize or link project
echo "Step 1: Setting up Railway project..."
if [ ! -f ".railway/config.json" ] && [ ! -f "railway.json" ]; then
    echo "No Railway project linked. Creating new project..."
    railway init --name grantradar
else
    echo "Railway project already configured."
fi

# Link to the project
railway link 2>/dev/null || true

echo ""
echo "Step 2: Please complete these steps in the Railway Dashboard (https://railway.app):"
echo ""
echo "  1. Add PostgreSQL database:"
echo "     - Click '+ New' -> 'Database' -> 'PostgreSQL'"
echo ""
echo "  2. Add Redis:"
echo "     - Click '+ New' -> 'Database' -> 'Redis'"
echo ""
echo "  3. Set environment variables for the 'api' service:"
echo "     DATABASE_URL=\${{Postgres.DATABASE_URL}}"
echo "     REDIS_URL=\${{Redis.REDIS_URL}}"
echo "     CELERY_BROKER_URL=\${{Redis.REDIS_URL}}"
echo "     SECRET_KEY=$(openssl rand -hex 32)"
echo "     ENVIRONMENT=production"
echo "     DEBUG=false"
echo ""
read -p "Press Enter once you've added PostgreSQL and Redis in the dashboard..."

echo ""
echo "Step 3: Deploying backend API..."
railway up --detach

echo ""
echo "=========================================="
echo "   Deployment initiated!"
echo "=========================================="
echo ""
echo "Next steps:"
echo "  1. Go to https://railway.app/dashboard to monitor deployment"
echo "  2. Add remaining environment variables (API keys, etc.)"
echo "  3. After deployment, run seed data:"
echo "     railway run python -m backend.scripts.seed_data"
echo ""
echo "Test user credentials will be:"
echo "  - test.user1@grantradar.com / TestUser1!2025"
echo "  - test.user2@grantradar.com / TestUser2!2025"
echo ""
