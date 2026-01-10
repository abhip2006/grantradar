#!/bin/sh
# Railway Frontend Startup Script
# Substitutes PORT environment variable and starts nginx

set -e

# Default to port 80 if PORT is not set
export PORT=${PORT:-80}

echo "Starting nginx on port $PORT"

# Substitute environment variables in the nginx config template
envsubst '${PORT}' < /etc/nginx/nginx.conf.template > /etc/nginx/nginx.conf

# Start nginx
exec nginx -g 'daemon off;'
