#!/bin/bash
set -e

echo "=== Django Build Script ==="

# Check Python version
echo "Python version:"
python --version

# Skip ensurepip since Nixpacks should provide pip
echo "Checking pip..."
which pip || echo "pip not found, trying python -m pip"

# Install requirements directly
echo "Installing Python dependencies..."
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --noinput

echo "=== Build completed successfully ==="
