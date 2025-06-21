#!/usr/bin/env python3
import os
import sys
import django

# Добавляем путь к проекту
sys.path.append('/Users/alymbekovsabyr/bg projects/SergeykhanWebSite/sergeykhan-backend/app1')

# Настраиваем Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'app1.settings')
django.setup()

from api1.models import SiteSettings, Service

def create_initial_data():
    """Создает начальные данные для сайта"""
    
    # Создаем настройки сайта, если их еще нет
    if not SiteSettings.objects.exists():
        settings = SiteSettings.objects.create(
            phone="+7 (777) 123-45-67",
            email="info@sergeykhan.kz", 
            address="г. Алматы",
            working_hours="24/7",
            facebook_url="https://facebook.com/sergeykhan",
            instagram_url="https://instagram.com/sergeykhan", 
            telegram_url="https://t.me/sergeykhan",
            whatsapp_url="https://wa.me/77771234567",
            hero_title="Профессиональный ремонт бытовой техники",
            hero_subtitle="Быстро, качественно, с гарантией 6 месяцев. Выезд мастера за 1 час в любой район Алматы.",
            about_title="Почему выбирают нас",
            about_description="Мы — команда профессионалов с многолетним опытом ремонта бытовой техники. Используем только оригинальные запчасти и современное оборудование."
        )
        print("✅ Настройки сайта созданы")
    else:
        print("ℹ️ Настройки сайта уже существуют")
    
    # Создаем базовые услуги
    services_data = [
        {
            "name": "Ремонт холодильников",
            "description": "Профессиональный ремонт холодильников всех марок: Samsung, LG, Bosch, Indesit, Ariston и др.",
            "price_from": 5000,
            "order": 1
        },
        {
            "name": "Ремонт стиральных машин", 
            "description": "Ремонт стиральных машин любой сложности. Замена подшипников, насосов, электроники.",
            "price_from": 4000,
            "order": 2
        },
        {
            "name": "Ремонт микроволновых печей",
            "description": "Диагностика и ремонт микроволновых печей. Замена магнетронов, блоков управления.",
            "price_from": 3000,
            "order": 3
        },
        {
            "name": "Ремонт посудомоечных машин",
            "description": "Ремонт посудомоечных машин: замена насосов, клапанов, электронных модулей.",
            "price_from": 4500,
            "order": 4
        },
        {
            "name": "Ремонт духовых шкафов",
            "description": "Ремонт электрических и газовых духовых шкафов, варочных панелей.",
            "price_from": 3500,
            "order": 5
        },
        {
            "name": "Диагностика неисправностей",
            "description": "Бесплатная диагностика при заказе ремонта. Определение причины поломки.",
            "price_from": 1000,
            "order": 6
        }
    ]
    
    created_count = 0
    for service_data in services_data:
        if not Service.objects.filter(name=service_data["name"]).exists():
            Service.objects.create(**service_data)
            created_count += 1
            print(f"✅ Создана услуга: {service_data['name']}")
    
    if created_count == 0:
        print("ℹ️ Все услуги уже существуют")
    else:
        print(f"✅ Создано {created_count} новых услуг")
    
    print("\n🎉 Инициализация завершена!")
    print(f"📊 Всего услуг в базе: {Service.objects.count()}")
    print(f"⚙️ Настройки сайта: {'настроены' if SiteSettings.objects.exists() else 'не настроены'}")

if __name__ == "__main__":
    create_initial_data()
