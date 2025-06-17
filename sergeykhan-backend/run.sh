#!/bin/bash
set -e

echo "Starting Django application..."

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create migrations if they don't exist
echo "Creating migrations for api1..."
python manage.py makemigrations api1

# Run all migrations
echo "Running Django migrations..."
python manage.py migrate

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
