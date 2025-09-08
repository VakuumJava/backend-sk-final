#!/bin/bash
set -e

echo "Starting Django application..."

# Run migrations
echo "Running migrations..."
python manage.py migrate --noinput

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

# Create superuser if environment variables are set
if [ "$DJANGO_SUPERUSER_EMAIL" ] && [ "$DJANGO_SUPERUSER_PASSWORD" ]; then
    echo "Creating superuser with environment variables..."
    python manage.py shell << EOF
import os
from django.contrib.auth import get_user_model
User = get_user_model()
email = os.environ.get('DJANGO_SUPERUSER_EMAIL')
password = os.environ.get('DJANGO_SUPERUSER_PASSWORD')

if not User.objects.filter(email=email).exists():
    try:
        user = User.objects.create_superuser(
            email=email,
            password=password,
            first_name='Admin',
            last_name='User',
            role='super-admin'
        )
        print(f'✅ Superuser created successfully: {email}')
    except Exception as e:
        print(f'❌ Error creating superuser: {e}')
else:
    print(f'⚠️ Superuser already exists: {email}')
EOF
else
    echo "Environment variables not set, creating default admin..."
    python manage.py create_admin --email="admin@sergeykhan.kz" --password="admin123"
fi

echo "Django setup completed successfully!"
