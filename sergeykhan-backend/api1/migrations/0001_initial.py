# This is a placeholder migration file for Railway deployment
# The actual migration will be created during the build process

from django.db import migrations

class Migration(migrations.Migration):
    
    initial = True
    
    dependencies = [
        ('auth', '0012_alter_user_first_name_max_length'),
    ]
    
    operations = [
        # Migrations will be created by makemigrations during deployment
    ]
