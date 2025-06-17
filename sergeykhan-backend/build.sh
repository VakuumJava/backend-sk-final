#!/bin/bash
set -e

echo "Setting up Python environment..."
python --version
python -m ensurepip --upgrade || true
python -m pip install --upgrade pip setuptools wheel

echo "Installing dependencies..."
python -m pip install -r requirements.txt

echo "Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "Build completed successfully!"
