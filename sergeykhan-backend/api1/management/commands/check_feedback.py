from django.core.management.base import BaseCommand
from api1.models import FeedbackRequest

class Command(BaseCommand):
    help = 'Проверить заявки в базе данных'

    def handle(self, *args, **options):
        total = FeedbackRequest.objects.count()
        self.stdout.write(f'Всего заявок в БД: {total}')
        
        for feedback in FeedbackRequest.objects.all():
            self.stdout.write(f'ID: {feedback.id}, Name: {feedback.name}, Phone: {feedback.phone}, Called: {feedback.is_called}, Created: {feedback.created_at}')
