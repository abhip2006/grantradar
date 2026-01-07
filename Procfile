# Railway Procfile - defines process types for the application
# Use railway.json to configure which process runs on which service

# Main FastAPI web server
web: uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}

# Celery worker for background tasks (grant discovery, matching, etc.)
worker: celery -A backend.tasks.celery_app worker --loglevel=info --concurrency=2

# Celery beat scheduler for periodic tasks (daily grant updates)
beat: celery -A backend.tasks.celery_app beat --loglevel=info
