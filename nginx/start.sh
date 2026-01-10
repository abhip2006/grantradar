#!/bin/sh
# Railway Frontend Startup Script
# Substitutes PORT environment variable and starts nginx

set -e

# Default to port 80 if PORT is not set
export PORT=${PORT:-80}

echo "Starting nginx on port $PORT"

# Substitute environment variables in the nginx config template
# Write to /tmp since /etc/nginx may be read-only in Railway
envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /tmp/nginx.conf

# Start nginx with the generated config
exec nginx -c /tmp/nginx.conf -g 'daemon off;'
