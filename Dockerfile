# GrantRadar Backend Dockerfile
# Production-ready multi-stage build for optimized image size and security

# ==============================================================================
# Stage 1: Dependencies Builder
# ==============================================================================
FROM python:3.14-slim AS builder

WORKDIR /app

# Install build dependencies required for compiling Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better layer caching
COPY requirements.txt .

# Create virtual environment and install production dependencies only
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies with optimizations
RUN pip install --no-cache-dir --upgrade pip wheel setuptools && \
    pip install --no-cache-dir -r requirements.txt && \
    # Remove unnecessary files to reduce image size
    find /opt/venv -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyc" -delete 2>/dev/null || true && \
    find /opt/venv -type f -name "*.pyo" -delete 2>/dev/null || true

# ==============================================================================
# Stage 2: Production Runtime
# ==============================================================================
FROM python:3.14-slim AS production

# Labels for container identification
LABEL maintainer="GrantRadar Team"
LABEL description="GrantRadar Backend API Server"
LABEL version="1.0.0"

WORKDIR /app

# Install runtime dependencies only (no build tools)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY backend/ ./backend/
COPY agents/ ./agents/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Create non-root user for security (principle of least privilege)
RUN groupadd --gid 1000 appgroup && \
    useradd --uid 1000 --gid appgroup --shell /bin/bash --create-home appuser && \
    chown -R appuser:appgroup /app && \
    # Create directory for any runtime files
    mkdir -p /app/logs /app/tmp && \
    chown -R appuser:appgroup /app/logs /app/tmp

# Switch to non-root user
USER appuser

# Environment variables for production
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONHASHSEED=random \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PORT=8000

# Expose the application port
EXPOSE 8000

# Health check to verify application is running
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Default command for running the application
# Runs migrations before starting the server
# PYTHONPATH=/app is required for alembic to find the backend module
CMD ["sh", "-c", "PYTHONPATH=/app alembic upgrade head && uvicorn backend.main:socket_app --host 0.0.0.0 --port ${PORT} --workers 4 --loop uvloop --http httptools"]
