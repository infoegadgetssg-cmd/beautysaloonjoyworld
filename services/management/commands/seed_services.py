# services/management/commands/seed_services.py
from django.core.management.base import BaseCommand
from services.models import ServiceCategory, Service, ServiceFAQ

class Command(BaseCommand):
    help = 'Seed the database with sample service data'

    def handle(self, *args, **kwargs):
        self.stdout.write('Seeding service data...')
        
        # Create categories
        categories = [
            {
                'name': 'Facials & Skincare',
                'slug': 'facials',
                'icon': 'fas fa-spa',
                'description': 'Rejuvenating facial treatments for radiant skin'
            },
            {
                'name': 'Makeup Artistry',
                'slug': 'makeup',
                'icon': 'fas fa-palette',
                'description': 'Professional makeup for all occasions'
            },
            {
                'name': 'Manicure & Pedicure',
                'slug': 'nails',
                'icon': 'fas fa-hand-sparkles',
                'description': 'Luxurious nail treatments and nail art'
            },
            {
                'name': 'Hair Styling',
                'slug': 'hair',
                'icon': 'fas fa-cut',
                'description': 'Haircuts, styling, and treatments'
            },
            {
                'name': 'Waxing',
                'slug': 'waxing',
                'icon': 'fas fa-seedling',
                'description': 'Professional waxing services'
            },
        ]

        for cat_data in categories:
            category, created = ServiceCategory.objects.get_or_create(
                slug=cat_data['slug'],
                defaults=cat_data
            )
            if created:
                self.stdout.write(f'Created category: {category.name}')

        # Get categories for service creation
        facials = ServiceCategory.objects.get(slug='facials')
        makeup = ServiceCategory.objects.get(slug='makeup')
        nails = ServiceCategory.objects.get(slug='nails')
        
        # Create sample services
        services = [
            {
                'category': facials,
                'name': 'Hydrating Facial',
                'slug': 'hydrating-facial',
                'short_description': 'Deeply moisturizing facial treatment',
                'full_description': 'A deeply moisturizing facial treatment that replenishes your skin\'s moisture levels, leaving it plump, hydrated, and radiant. Perfect for dry or dehydrated skin.',
                'price': 65.00,
                'duration': 60,
                'image_url': 'https://res.cloudinary.com/demo/image/upload/v1681234567/hydrating-facial.jpg',
                'features': ['Deep cleansing and exfoliation', 'Hydrating mask', 'Facial massage', 'Serum application'],
            },
            {
                'category': facials,
                'name': 'Anti-Aging Facial',
                'slug': 'anti-aging-facial',
                'short_description': 'Reduce fine lines and wrinkles',
                'full_description': 'Advanced facial treatment targeting fine lines, wrinkles, and loss of elasticity. Stimulates collagen production for firmer, younger-looking skin.',
                'price': 85.00,
                'duration': 75,
                'image_url': 'https://res.cloudinary.com/demo/image/upload/v1681234567/anti-aging-facial.jpg',
                'features': ['Collagen-boosting treatment', 'LED light therapy', 'Anti-aging serum', 'Eye contour treatment'],
                'is_on_special': True,
                'special_price': 72.00,
            },
            {
                'category': makeup,
                'name': 'Bridal Makeup',
                'slug': 'bridal-makeup',
                'short_description': 'Special occasion bridal makeup',
                'full_description': 'Perfect for your special day! Our bridal makeup artists create a look that enhances your natural beauty and lasts all day.',
                'price': 120.00,
                'duration': 90,
                'image_url': 'https://res.cloudinary.com/demo/image/upload/v1681234567/bridal-makeup.jpg',
                'features': ['Consultation included', 'Makeup trial available', 'Long-lasting products', 'Lashes included'],
            },
            {
                'category': nails,
                'name': 'Deluxe Manicure',
                'slug': 'deluxe-manicure',
                'short_description': 'Complete nail care treatment',
                'full_description': 'A luxurious manicure treatment including shaping, cuticle care, exfoliation, moisturizing, and polish of your choice.',
                'price': 45.00,
                'duration': 45,
                'image_url': 'https://res.cloudinary.com/demo/image/upload/v1681234567/deluxe-manicure.jpg',
                'features': ['Nail shaping', 'Cuticle care', 'Hand massage', 'Polish application'],
            },
        ]

        for service_data in services:
            service, created = Service.objects.get_or_create(
                slug=service_data['slug'],
                defaults=service_data
            )
            if created:
                self.stdout.write(f'Created service: {service.name}')

        # Create FAQs
        faqs = [
            {
                'question': 'How far in advance should I book my appointment?',
                'answer': 'We recommend booking at least 1-2 weeks in advance to secure your preferred date and time. For weekend appointments or during holiday seasons, we suggest booking 3-4 weeks ahead.',
            },
            {
                'question': 'What is your cancellation policy?',
                'answer': 'We require 24 hours notice for cancellations or rescheduling. Appointments cancelled with less than 24 hours notice may be subject to a 50% cancellation fee. No-shows will be charged the full service amount.',
            },
            {
                'question': 'Do you use cruelty-free products?',
                'answer': 'Yes! We are committed to using only cruelty-free, vegan-friendly products. All our brands are carefully selected for their ethical standards and high performance.',
            },
        ]

        for faq_data in faqs:
            faq, created = ServiceFAQ.objects.get_or_create(
                question=faq_data['question'],
                defaults=faq_data
            )
            if created:
                self.stdout.write(f'Created FAQ: {faq.question[:50]}...')

        self.stdout.write(self.style.SUCCESS('Successfully seeded service data!'))