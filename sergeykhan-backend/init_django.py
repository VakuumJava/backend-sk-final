#!/usr/bin/env python
"""
Simple initialization script for Railway deployment
"""
import os
import sys
import django

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project_settings.settings')
django.setup()

from django.core.management import execute_from_command_line

if __name__ == "__main__":
    print("=== Django Initialization ===")
    
    # Run migrations
    print("Running migrations...")
    execute_from_command_line(['manage.py', 'migrate', '--noinput'])
    
    # Create superuser if environment variables are set
    if all([
        os.environ.get('DJANGO_SUPERUSER_USERNAME'),
        os.environ.get('DJANGO_SUPERUSER_EMAIL'),
        os.environ.get('DJANGO_SUPERUSER_PASSWORD')
    ]):
        print("Creating superuser...")
        try:
            execute_from_command_line(['manage.py', 'createsuperuser', '--noinput'])
            print("Superuser created successfully.")
        except Exception as e:
            print(f"Superuser creation skipped: {e}")
    
    # Collect static files
    print("Collecting static files...")
    execute_from_command_line(['manage.py', 'collectstatic', '--noinput'])
    
    print("=== Initialization completed ===")
