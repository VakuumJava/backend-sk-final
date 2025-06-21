# Railway Deployment Guide

## Project Structure
```
sergeykhan-backend/
├── api1/                   # Django app with models, views, serializers
├── project_settings/       # Django project settings
├── media/                 # Uploaded files
├── manage.py             # Django management script
├── db.sqlite3            # Local database (not used in production)
├── requirements.txt      # Production dependencies
├── Procfile             # Railway process configuration
├── runtime.txt          # Python version specification
├── startup.sh           # Database migrations and setup script
├── nixpacks.toml        # Railway build configuration
├── .env.example         # Environment variables template
└── .gitignore           # Git ignore rules
```

## Fixed Issues
✅ **Removed duplicate Balance model** - Fixed RuntimeWarning about model registration  
✅ **Fixed WSGI/ASGI configuration** - Updated `project_settings.settings` path  
✅ **Clean project structure** - Removed all test, debug, and temporary files  
✅ **Production-ready settings** - Configured for Railway deployment  

## Prerequisites
1. Railway CLI installed
2. Railway account connected
3. Project deployed to Railway

## Environment Variables
Set these in Railway dashboard or via CLI:

```bash
# Required for production
SECRET_KEY=your-django-secret-key
DEBUG=False

# Database (automatically provided by Railway PostgreSQL)
DATABASE_URL=postgresql://...

# Superuser creation (optional)
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=secure-password
DJANGO_SUPERUSER_USERNAME=admin
```

## Deployment Steps

1. **Set environment variables:**
```bash
railway variables set SECRET_KEY="your-secret-key-here"
railway variables set DEBUG=False
railway variables set DJANGO_SUPERUSER_EMAIL="admin@example.com" 
railway variables set DJANGO_SUPERUSER_PASSWORD="your-password"
railway variables set DJANGO_SUPERUSER_USERNAME="admin"
```

2. **Add PostgreSQL database:**
```bash
railway add postgresql
```

3. **Deploy:**
```bash
railway up
```

## What happens during deployment:
1. Railway detects Python project and installs dependencies
2. `startup.sh` runs automatically:
   - Database migrations
   - Static files collection
   - Superuser creation (if env vars are set)
3. Gunicorn starts the Django application

## Post-deployment:
- Admin panel: `https://your-app.railway.app/admin/`
- API endpoints: `https://your-app.railway.app/api/...`

## Key Features:
- ✅ Production-ready Django settings
- ✅ PostgreSQL database support
- ✅ Static files handling with WhiteNoise
- ✅ Automatic migrations
- ✅ Automatic superuser creation
- ✅ CORS configured for frontend
- ✅ Clean project structure
- ✅ Security settings enabled
