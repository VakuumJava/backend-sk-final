#!/bin/bash
set -e

echo "Starting Django application..."

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Start gunicorn
echo "Starting gunicorn server..."
exec gunicorn project_settings.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --worker-class sync \
    --worker-connections 1000 \
    --timeout 30 \
    --keep-alive 5 \
    --max-requests 1000 \
    --max-requests-jitter 100 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
