#!/bin/bash
set -e

echo "Starting Django application..."

# Wait a moment for any background processes
sleep 2

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

# Create and run migrations
echo "Making migrations..."
python manage.py makemigrations --noinput

echo "Running migrations..."
python manage.py migrate --noinput

# Create superuser if environment variables are set
if [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser..."
    python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
try:
    if not User.objects.filter(email='$DJANGO_SUPERUSER_EMAIL').exists():
        user = User.objects.create_superuser(
            email='$DJANGO_SUPERUSER_EMAIL',
            password='$DJANGO_SUPERUSER_PASSWORD'
        )
        print('Superuser created successfully.')
    else:
        print('Superuser already exists.')
except Exception as e:
    print(f'Error: {e}')
" || echo "Superuser creation failed"
fi

# Start gunicorn
echo "Starting gunicorn server..."
exec gunicorn project_settings.wsgi:application \
    --bind 0.0.0.0:$PORT \
    --workers 3 \
    --timeout 120 \
    --log-level info \
    --access-logfile - \
    --error-logfile -
