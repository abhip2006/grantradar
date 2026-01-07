# GrantRadar Railway Deployment Guide

This guide walks you through deploying GrantRadar to Railway, a modern cloud platform with native support for PostgreSQL, Redis, and containerized applications.

## Prerequisites

- [Railway account](https://railway.app) (free tier available)
- [Railway CLI](https://docs.railway.app/develop/cli) (optional but recommended)
- GitHub account with the repository pushed

## Architecture Overview

GrantRadar consists of 5 services on Railway:

```
┌─────────────────────────────────────────────────────────────┐
│                     Railway Project                          │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Frontend │  │   API    │  │  Worker  │  │   Beat   │   │
│  │  (React) │  │(FastAPI) │  │ (Celery) │  │ (Celery) │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │             │          │
│       │        ┌────┴─────────────┴─────────────┴───┐     │
│       │        │                                     │     │
│  ┌────┴────┐  ┌┴──────────┐              ┌──────────┴┐    │
│  │   CDN   │  │ PostgreSQL│              │   Redis   │    │
│  └─────────┘  └───────────┘              └───────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Quick Start (Railway CLI)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Initialize new project
railway init

# Link to GitHub repo (or use dashboard)
railway link

# Deploy
railway up
```

## Step-by-Step Dashboard Deployment

### Step 1: Create Railway Project

1. Go to [Railway Dashboard](https://railway.app/dashboard)
2. Click **"New Project"**
3. Select **"Deploy from GitHub repo"**
4. Connect your GitHub account if not already connected
5. Select the `grantradar` repository

### Step 2: Add PostgreSQL

1. In your project, click **"+ New"**
2. Select **"Database" → "PostgreSQL"**
3. Railway automatically provisions a PostgreSQL instance
4. Note: The `DATABASE_URL` variable is automatically created

### Step 3: Add Redis

1. Click **"+ New"**
2. Select **"Database" → "Redis"**
3. Railway automatically provisions a Redis instance
4. Note: The `REDIS_URL` variable is automatically created

### Step 4: Configure API Service

1. Click on your main service (from GitHub)
2. Go to **"Settings"** tab
3. Set **Root Directory**: `/` (leave empty or root)
4. Set **Build Command**: (leave empty, uses Dockerfile)
5. Set **Start Command**: `uvicorn backend.main:app --host 0.0.0.0 --port $PORT`

Add these **Environment Variables**:
```
DATABASE_URL=${{Postgres.DATABASE_URL}}
REDIS_URL=${{Redis.REDIS_URL}}
JWT_SECRET_KEY=<generate-a-secure-key>
ENVIRONMENT=production
DEBUG=false
OPENAI_API_KEY=<your-openai-key>
SENDGRID_API_KEY=<your-sendgrid-key>
```

Generate a secure JWT key:
```bash
openssl rand -hex 32
```

### Step 5: Add Celery Worker Service

1. Click **"+ New" → "GitHub Repo"**
2. Select the same `grantradar` repository
3. Rename the service to `worker`
4. Go to **Settings**:
   - **Start Command**: `celery -A backend.tasks.celery_app worker --loglevel=info --concurrency=2`
5. Add the same environment variables as the API service

### Step 6: Add Celery Beat Service

1. Click **"+ New" → "GitHub Repo"**
2. Select the same `grantradar` repository
3. Rename the service to `beat`
4. Go to **Settings**:
   - **Start Command**: `celery -A backend.tasks.celery_app beat --loglevel=info`
5. Add the same environment variables as the API service

### Step 7: Deploy Frontend

1. Click **"+ New" → "GitHub Repo"**
2. Select the same `grantradar` repository
3. Rename the service to `frontend`
4. Go to **Settings**:
   - **Root Directory**: `frontend`
   - **Build Command**: `npm run build`
   - **Start Command**: Leave empty (uses static file serving)
5. Add environment variable:
   ```
   VITE_API_URL=https://<your-api-service>.railway.app
   ```

### Step 8: Configure Domains

1. For each service needing external access (API, Frontend):
   - Go to **Settings → Networking**
   - Click **"Generate Domain"**
   - Or add a custom domain

2. Update the `VITE_API_URL` on the frontend to match the API domain

### Step 9: Run Database Migrations

Option A: Via Railway CLI
```bash
railway run alembic upgrade head
```

Option B: Via Railway Shell
1. Click on the API service
2. Go to **"Deploy" → "View Logs"**
3. Click **"Shell"** button
4. Run: `alembic upgrade head`

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | `${{Postgres.DATABASE_URL}}` |
| `REDIS_URL` | Redis connection | `${{Redis.REDIS_URL}}` |
| `JWT_SECRET_KEY` | JWT signing secret | `<64-char-hex-string>` |
| `ENVIRONMENT` | App environment | `production` |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI for embeddings | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | - |
| `SENDGRID_API_KEY` | Email notifications | - |
| `TWILIO_ACCOUNT_SID` | SMS notifications | - |
| `TWILIO_AUTH_TOKEN` | SMS notifications | - |
| `TWILIO_PHONE_NUMBER` | SMS sender number | - |
| `DEBUG` | Enable debug mode | `false` |

### Using Railway Reference Variables

Railway allows services to reference each other's variables:
```
${{ServiceName.VARIABLE_NAME}}
```

Examples:
- `${{Postgres.DATABASE_URL}}` - PostgreSQL connection string
- `${{Redis.REDIS_URL}}` - Redis connection string
- `${{api.RAILWAY_PUBLIC_DOMAIN}}` - API service's public domain

## Cost Estimation

| Service | Memory | Estimated Cost |
|---------|--------|----------------|
| PostgreSQL | 1GB | $5/mo |
| Redis | 256MB | $3/mo |
| API | 512MB | $5/mo |
| Worker | 512MB | $5/mo |
| Beat | 256MB | $3/mo |
| Frontend | 256MB | $3/mo |
| **Total** | | **~$24/mo** |

*Costs vary based on usage. Railway offers a generous free tier ($5 credit/month).*

## Local Testing with Docker Compose

Test the production setup locally before deploying:

```bash
# Build and start all services
docker-compose -f docker-compose.railway.yml up --build

# Run in detached mode
docker-compose -f docker-compose.railway.yml up -d

# View logs
docker-compose -f docker-compose.railway.yml logs -f

# Stop all services
docker-compose -f docker-compose.railway.yml down
```

Access locally:
- Frontend: http://localhost:3000
- API: http://localhost:8000
- API Docs: http://localhost:8000/docs

## Monitoring & Logs

### Railway Dashboard
- View real-time logs for each service
- Monitor resource usage
- Set up log drains to external services

### Health Checks
The API service includes a health endpoint:
```
GET /health
```

Railway automatically performs health checks and restarts unhealthy containers.

## Scaling

### Horizontal Scaling
```bash
# Scale worker replicas via Railway CLI
railway service worker --replicas 3
```

Or in the dashboard:
1. Go to service settings
2. Adjust **"Replicas"** slider

### Vertical Scaling
Adjust memory/CPU limits in service settings.

## Troubleshooting

### Common Issues

**1. Database connection errors**
- Verify `DATABASE_URL` is using the Railway reference: `${{Postgres.DATABASE_URL}}`
- Check PostgreSQL service is running

**2. Redis connection errors**
- Verify `REDIS_URL` is using the Railway reference: `${{Redis.REDIS_URL}}`
- Check Redis service is running

**3. Celery workers not processing tasks**
- Check worker logs for errors
- Verify Redis connectivity
- Ensure `CELERY_BROKER_URL` matches `REDIS_URL`

**4. Frontend not connecting to API**
- Verify `VITE_API_URL` is set correctly
- Check CORS settings in backend
- Ensure API domain is accessible

**5. Build failures**
- Check Dockerfile syntax
- Verify all dependencies in requirements.txt
- Review build logs in Railway dashboard

### Useful Commands

```bash
# View logs
railway logs

# Open shell in service
railway shell

# View environment variables
railway variables

# Restart service
railway service restart

# View deployment status
railway status
```

## CI/CD Integration

Railway automatically deploys on push to the connected branch. For more control:

### GitHub Actions Example

```yaml
# .github/workflows/deploy.yml
name: Deploy to Railway

on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Install Railway CLI
        run: npm install -g @railway/cli

      - name: Deploy
        run: railway up
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
```

## Security Checklist

- [ ] Use strong JWT_SECRET_KEY (32+ characters)
- [ ] Set ENVIRONMENT=production
- [ ] Set DEBUG=false
- [ ] Use HTTPS for all public endpoints
- [ ] Enable Railway's DDoS protection
- [ ] Rotate API keys periodically
- [ ] Enable PostgreSQL SSL (Railway does this by default)
- [ ] Review CORS settings for production domains only

## Backup & Recovery

### Database Backups
Railway provides automatic daily backups for PostgreSQL. To create manual backups:

```bash
# Export database
railway run pg_dump -Fc > backup.dump

# Import database
railway run pg_restore -d $DATABASE_URL backup.dump
```

### Redis Persistence
Railway Redis includes RDB persistence. For additional backup:

```bash
railway run redis-cli BGSAVE
```

## Support Resources

- [Railway Documentation](https://docs.railway.app)
- [Railway Discord](https://discord.gg/railway)
- [GrantRadar Issues](https://github.com/abhip2006/grantradar/issues)
