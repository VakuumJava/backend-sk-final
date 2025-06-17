# Django Backend for Railway Deployment

## Deployment Instructions

### Railway Deployment

1. **Connect your repository to Railway**
   - Go to [Railway](https://railway.app)
   - Create a new project from GitHub repository

2. **Set Environment Variables in Railway**
   ```
   SECRET_KEY=your-very-secret-key-here
   DEBUG=False
   ```

3. **Railway will automatically:**
   - Detect this as a Django project
   - Install dependencies from requirements.txt
   - Run collectstatic
   - Start the server with gunicorn

### Local Development

1. Install dependencies:
   ```bash
   pip install -r requirements-dev.txt
   ```

2. Run migrations:
   ```bash
   python manage.py migrate
   ```

3. Create superuser:
   ```bash
   python manage.py createsuperuser
   ```

4. Run development server:
   ```bash
   python manage.py runserver
   ```

## Project Structure

- `project_settings/` - Django settings and configuration
- `api1/` - Main API application
- `media/` - User uploaded files
- `manage.py` - Django management script
- `requirements.txt` - Production dependencies
- `Procfile` - Railway deployment configuration
- `nixpacks.toml` - Nixpacks build configuration

## API Endpoints

The API is available at the root URL. Check `api1/urls.py` for available endpoints.
