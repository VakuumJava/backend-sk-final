# SergeykhanBackend

Django REST API backend for master service management system.

## Features

- 🏠 **Master Management**: Profiles, schedules, workload tracking
- 📋 **Order System**: Order creation, assignment, completion
- 💰 **Profit Distribution**: Automated profit calculation and distribution
- 📊 **Analytics**: Capacity analysis and reporting
- 🔐 **Authentication**: Token-based API authentication
- 📱 **API**: RESTful API with Django REST Framework

## Tech Stack

- **Framework**: Django 5.1.6
- **API**: Django REST Framework 3.15.2
- **Database**: PostgreSQL (production), SQLite (development)
- **Server**: Gunicorn
- **Static Files**: WhiteNoise
- **Deployment**: Railway

## Quick Start

### Local Development

1. **Clone and install:**
```bash
git clone <repo-url>
cd sergeykhan-backend
pip install -r requirements.txt
```

2. **Run migrations:**
```bash
python manage.py migrate
```

3. **Create superuser:**
```bash
python manage.py createsuperuser
```

4. **Start server:**
```bash
python manage.py runserver
```

### Production Deployment

See [DEPLOYMENT.md](DEPLOYMENT.md) for Railway deployment instructions.

## API Endpoints

- `/admin/` - Django admin panel
- `/api/auth/` - Authentication endpoints  
- `/api/masters/` - Master management
- `/api/orders/` - Order management
- `/api/schedules/` - Schedule management
- `/api/analytics/` - Analytics and reporting

## Project Structure

```
sergeykhan-backend/
├── api1/                   # Main Django app
│   ├── models.py          # Database models
│   ├── views.py           # API views
│   ├── serializers.py     # DRF serializers
│   ├── urls.py            # API routes
│   └── migrations/        # Database migrations
├── project_settings/       # Django project configuration
│   ├── settings.py        # Django settings
│   ├── urls.py            # Main URL configuration
│   └── wsgi.py           # WSGI application
├── media/                 # User uploaded files
├── manage.py             # Django CLI
└── requirements.txt      # Python dependencies
```

## Environment Variables

Create `.env` file based on `.env.example`:

```bash
SECRET_KEY=your-django-secret-key
DEBUG=False
DATABASE_URL=postgresql://...
DJANGO_SUPERUSER_EMAIL=admin@example.com
DJANGO_SUPERUSER_PASSWORD=secure-password
```

## License

[Add your license information here]
