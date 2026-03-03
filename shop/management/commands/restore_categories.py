# management/commands/restore_categories.py
from django.core.management.base import BaseCommand
from shop.models import ProductCategory

class Command(BaseCommand):
    help = 'Restore default product categories'
    
    def handle(self, *args, **options):
        categories = [
            {
                'name': 'Skincare',
                'slug': 'skincare',
                'description': 'Face creams, serums, and skincare products'
            },
            {
                'name': 'Makeup',
                'slug': 'makeup',
                'description': 'Cosmetics and makeup products'
            },
            {
                'name': 'Hair Care',
                'slug': 'hair-care',
                'description': 'Shampoos, conditioners, and hair treatments'
            },
            {
                'name': 'Nail Care',
                'slug': 'nail-care',
                'description': 'Nail polishes and treatments'
            },
            {
                'name': 'Body Care',
                'slug': 'body-care',
                'description': 'Body lotions and treatments'
            },
            {
                'name': 'Fragrances',
                'slug': 'fragrances',
                'description': 'Perfumes and body sprays'
            },
            {
                'name': 'Tools & Accessories',
                'slug': 'tools-accessories',
                'description': 'Beauty tools and accessories'
            },
        ]
        
        for cat_data in categories:
            category, created = ProductCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults={
                    'name': cat_data['name'],
                    'description': cat_data['description'],
                    'is_active': True
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Created category: {cat_data["name"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'Category already exists: {cat_data["name"]}'))
        
        self.stdout.write(self.style.SUCCESS('All categories have been restored!'))