# Generated by Django 5.2 on 2025-06-17 14:32

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api1', '0010_merge_20250617_1314'),
    ]

    operations = [
        migrations.AlterField(
            model_name='financialtransaction',
            name='transaction_type',
            field=models.CharField(choices=[('order_completion', 'Завершение заказа'), ('master_payment', 'Выплата мастеру'), ('curator_payment', 'Выплата куратору'), ('company_income', 'Доход компании'), ('master_deferred', 'Отложенная выплата мастеру'), ('master_balance_total', 'К балансу мастера (общая сумма)')], max_length=25),
        ),
    ]
