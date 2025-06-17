#!/bin/bash
set -e

echo "Starting Django deployment..."

# Install dependencies if needed
if [ ! -d ".venv" ]; then
    echo "Installing dependencies..."
    python -m pip install --upgrade pip
    python -m pip install -r requirements.txt
fi

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Create superuser if environment variables are set
if [ "$DJANGO_SUPERUSER_USERNAME" ]; then
    echo "Creating superuser..."
    python manage.py createsuperuser --noinput --username "$DJANGO_SUPERUSER_USERNAME" --email "$DJANGO_SUPERUSER_EMAIL" || echo "Superuser already exists"
fi

# Start gunicorn
echo "Starting server on port $PORT..."
exec gunicorn project_settings.wsgi:application --bind 0.0.0.0:$PORT --workers 3 --timeout 120
