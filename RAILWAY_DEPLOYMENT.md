# GrantRadar Railway Deployment Guide

This guide walks you through deploying GrantRadar to Railway with all required services.

## Architecture Overview

GrantRadar requires the following services on Railway:

| Service | Description | Type |
|---------|-------------|------|
| **PostgreSQL** | Primary database | Railway Plugin |
| **Redis** | Cache & message broker | Railway Plugin |
| **API** | FastAPI backend | Custom Service |
| **Worker** | Celery background tasks | Custom Service |
| **Beat** | Celery scheduler | Custom Service |
| **Frontend** | React web application | Custom Service |

---

## Prerequisites

1. Railway CLI installed (`brew install railway` or `npm i -g @railway/cli`)
2. Railway account (https://railway.app)
3. GitHub repository with your code pushed

---

## Step-by-Step Deployment

### Step 1: Login to Railway

```bash
railway login
```

This opens a browser window for authentication.

### Step 2: Create New Project

```bash
railway init
```

Select "Empty Project" when prompted.

### Step 3: Add Database Plugins

From the Railway dashboard (https://railway.app):

1. Open your project
2. Click **"+ New"** → **"Database"** → **"PostgreSQL"**
3. Click **"+ New"** → **"Database"** → **"Redis"**

Railway will automatically provision these and provide connection URLs.

### Step 4: Deploy Backend API

```bash
# Link to your project
railway link

# Create the API service
railway service create api

# Set the service to use your Dockerfile
railway service update --name api

# Deploy
railway up --service api
```

**Required Environment Variables for API:**
Set these in Railway Dashboard → API Service → Variables:

```
DATABASE_URL=${{Postgres.DATABASE_URL}}
ASYNC_DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
CELERY_BROKER_URL=${{Redis.REDIS_URL}}
CELERY_RESULT_BACKEND=${{Redis.REDIS_URL}}

SECRET_KEY=<generate-a-secure-random-string>
ENVIRONMENT=production
DEBUG=false

# API Keys (add your actual keys)
ANTHROPIC_API_KEY=<your-anthropic-key>
OPENAI_API_KEY=<your-openai-key>
SENDGRID_API_KEY=<your-sendgrid-key>

# URLs (update after frontend is deployed)
BACKEND_URL=https://<your-api-service>.railway.app
FRONTEND_URL=https://<your-frontend-service>.railway.app
CORS_ORIGINS=https://<your-frontend-service>.railway.app
```

### Step 5: Deploy Celery Worker

```bash
railway service create worker
```

**Environment Variables:** Same as API service, plus:
```
# Set in Railway Dashboard
```

**Start Command:** Set in Railway Dashboard → Worker → Settings:
```
celery -A backend.tasks.celery_app worker --loglevel=info --concurrency=2
```

### Step 6: Deploy Celery Beat

```bash
railway service create beat
```

**Environment Variables:** Same as API service

**Start Command:**
```
celery -A backend.tasks.celery_app beat --loglevel=info
```

### Step 7: Deploy Frontend

The frontend needs a separate Dockerfile reference. Create this service:

```bash
railway service create frontend
```

**Build Settings in Railway Dashboard:**
- Dockerfile Path: `Dockerfile.frontend`
- Build Args:
  - `VITE_API_URL=https://<your-api-service>.railway.app`
  - `VITE_WS_URL=wss://<your-api-service>.railway.app`

### Step 8: Database Migrations (Automatic)

Database migrations now run automatically when the web/API service starts. The Procfile and Dockerfile include `alembic upgrade head` in the startup command.

If you need to run migrations manually:
```bash
railway run --service api alembic upgrade head
```

---

## Quick Deploy Script

Save this as `deploy-railway.sh` and run it:

```bash
#!/bin/bash
set -e

echo "🚂 Deploying GrantRadar to Railway..."

# Ensure we're linked to the project
railway link

# Deploy API (main backend)
echo "📦 Deploying API..."
railway up --service api --detach

# Deploy Worker
echo "⚙️ Deploying Worker..."
railway up --service worker --detach

# Deploy Beat
echo "⏰ Deploying Beat..."
railway up --service beat --detach

# Deploy Frontend
echo "🎨 Deploying Frontend..."
railway up --service frontend --detach

echo "✅ Deployment initiated! Check Railway dashboard for status."
echo "🔗 https://railway.app/dashboard"
```

---

## Environment Variables Reference

### Required for All Services

| Variable | Description |
|----------|-------------|
| `DATABASE_URL` | PostgreSQL connection string (use Railway reference) |
| `REDIS_URL` | Redis connection string (use Railway reference) |
| `SECRET_KEY` | JWT signing key (generate secure random string) |
| `ENVIRONMENT` | Set to `production` |

### API-Specific

| Variable | Description |
|----------|-------------|
| `BACKEND_URL` | Public URL of the API service |
| `FRONTEND_URL` | Public URL of the frontend |
| `CORS_ORIGINS` | Comma-separated allowed origins |
| `ANTHROPIC_API_KEY` | For AI features |
| `OPENAI_API_KEY` | For embeddings |
| `SENDGRID_API_KEY` | For email notifications |

### Frontend Build Args

| Variable | Description |
|----------|-------------|
| `VITE_API_URL` | Backend API URL |
| `VITE_WS_URL` | WebSocket URL (wss://...) |

---

## Generating a Secure Secret Key

```bash
openssl rand -hex 32
```

Or in Python:
```python
import secrets
print(secrets.token_hex(32))
```

---

## Post-Deployment Checklist

- [ ] Database migrations ran automatically (check API logs for "Running database migrations")
- [ ] API health check passes (`/health` endpoint)
- [ ] Frontend loads and connects to API
- [ ] User registration/login works
- [ ] Grant matching is functional
- [ ] Background tasks (Celery) are processing
- [ ] Email notifications configured (if using)

---

## Monitoring & Logs

View logs for any service:
```bash
railway logs --service api
railway logs --service worker
railway logs --service frontend
```

Or use the Railway dashboard for real-time log streaming.

---

## Scaling

Railway allows easy scaling through the dashboard:

1. **API**: Increase replicas for higher traffic
2. **Worker**: Increase concurrency or replicas for more background tasks
3. **PostgreSQL/Redis**: Upgrade to larger instances if needed

---

## Costs Estimate

Railway pricing (as of 2024):

| Service | Estimated Monthly Cost |
|---------|----------------------|
| PostgreSQL | ~$5-20 (depends on usage) |
| Redis | ~$5-10 |
| API | ~$5-20 |
| Worker | ~$5-15 |
| Beat | ~$3-5 |
| Frontend | ~$3-10 |
| **Total** | **~$25-80/month** |

Actual costs depend on usage. Railway offers a free tier with limited resources.

---

## Troubleshooting

### Database Connection Issues
- Ensure `DATABASE_URL` uses the Railway reference syntax: `${{Postgres.DATABASE_URL}}`
- Check that PostgreSQL plugin is fully provisioned

### Frontend Can't Connect to API
- Verify CORS_ORIGINS includes the frontend URL
- Check VITE_API_URL build arg is correct
- Ensure API service is healthy

### Celery Tasks Not Running
- Check Worker service logs for errors
- Verify Redis connection
- Ensure CELERY_BROKER_URL is set correctly

### Build Failures
- Check Dockerfile syntax
- Ensure all required files are committed to git
- Review build logs in Railway dashboard

---

## Support

- Railway Docs: https://docs.railway.app
- Railway Discord: https://discord.gg/railway
- GrantRadar Issues: [Your GitHub Issues URL]
