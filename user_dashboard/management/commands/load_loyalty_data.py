# user_dashboard/management/commands/load_loyalty_data.py
from django.core.management.base import BaseCommand
from user_dashboard.models import LoyaltyProgram

class Command(BaseCommand):
    help = 'Load initial loyalty program data'

    def handle(self, *args, **options):
        loyalty_levels = [
            {
                'level': 'explorer',
                'points_required': 0,
                'icon_class': 'fas fa-seedling',
                'benefits': 'Welcome bonus, Basic rewards'
            },
            {
                'level': 'lover',
                'points_required': 50,
                'icon_class': 'fas fa-heart',
                'benefits': '5% discount, Priority booking, Birthday gift'
            },
            {
                'level': 'enthusiast',
                'points_required': 100,
                'icon_class': 'fas fa-star',
                'benefits': '10% discount, Free product samples, Express service'
            },
            {
                'level': 'vip',
                'points_required': 200,
                'icon_class': 'fas fa-crown',
                'benefits': '15% discount, Exclusive events, Personal stylist, Free shipping'
            },
        ]
        
        for level_data in loyalty_levels:
            LoyaltyProgram.objects.update_or_create(
                level=level_data['level'],
                defaults=level_data
            )
        
        self.stdout.write(self.style.SUCCESS('Successfully loaded loyalty program data'))