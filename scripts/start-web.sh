#!/bin/bash
# Railway startup script for web service
# Runs database migrations before starting the application

set -e

echo "🔄 Running database migrations..."
alembic upgrade head

echo "✅ Migrations complete. Starting web server..."
exec uvicorn backend.main:socket_app --host 0.0.0.0 --port ${PORT:-8000} --workers 4 --loop uvloop --http httptools
