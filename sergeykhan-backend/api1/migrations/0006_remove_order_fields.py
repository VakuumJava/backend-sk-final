# Generated by Django 5.1.6 on 2025-06-13 12:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('api1', '0005_order_age_order_due_date_order_equipment_type_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='order',
            name='age',
        ),
        migrations.RemoveField(
            model_name='order',
            name='payment_method',
        ),
        migrations.RemoveField(
            model_name='order',
            name='priority',
        ),
    ]
