#!/bin/bash
set -e

echo "Starting Django application..."

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create migrations if they don't exist
echo "Creating migrations for api1..."
python manage.py makemigrations api1

# Run migrations in proper order
echo "Running core Django migrations..."
python manage.py migrate auth
python manage.py migrate contenttypes
python manage.py migrate sessions
python manage.py migrate admin

echo "Running api1 migrations..."
python manage.py migrate api1

echo "Running remaining migrations..."
python manage.py migrate

# Create superuser if environment variables are set
if [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser..."
    python manage.py shell -c "
from api1.models import CustomUser
try:
    if not CustomUser.objects.filter(email='$DJANGO_SUPERUSER_EMAIL').exists():
        user = CustomUser.objects.create_superuser(
            email='$DJANGO_SUPERUSER_EMAIL',
            password='$DJANGO_SUPERUSER_PASSWORD',
            role='admin'
        )
        print('Superuser created successfully')
    else:
        print('Superuser already exists')
except Exception as e:
    print(f'Error creating superuser: {e}')
" || echo "Superuser creation failed"
fi

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
