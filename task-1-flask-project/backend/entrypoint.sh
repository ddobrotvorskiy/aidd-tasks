#!/bin/sh
set -e

echo "Running database migrations..."

# Initialize migrations folder if it doesn't exist
if [ ! -d "migrations" ]; then
    flask db init
fi

# Generate migration if there are model changes
flask db migrate -m "auto" 2>/dev/null || true

# Apply migrations
flask db upgrade

echo "Starting gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 --workers 2 --timeout 120 "app:create_app()"
