# contact/management/commands/setup_contact_data.py
from django.core.management.base import BaseCommand
from contact.models import SalonLocation, BusinessHours, FAQ, QuickContactOption
from django.utils import timezone

class Command(BaseCommand):
    help = 'Sets up initial contact data for the beauty salon'
    
    def handle(self, *args, **kwargs):
        self.stdout.write('Setting up initial contact data...')
        
        # Setup salon location
        salon, created = SalonLocation.objects.get_or_create(
            name="Joy World Home of Beauty",
            defaults={
                'address': "123 Beauty Street\nManchester M1 1AB\nUnited Kingdom",
                'phone': "+44 161 123 4567",
                'email': "info@joyworldbeauty.com",
                'latitude': 53.480372,
                'longitude': -2.242722,
                'google_maps_embed_url': "https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2374.437839120938!2d-2.242722123025946!3d53.48037207232278!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x487bb1c16ecb7dd7%3A0x3f10e98ed6358d2e!2sManchester%2C%20UK!5e0!3m2!1sen!2sus!4v1681234567890!5m2!1sen!2sus",
                'is_active': True
            }
        )
        if created:
            self.stdout.write(self.style.SUCCESS('Created salon location'))
        
        # Setup business hours
        hours_data = [
            {'day': 'monday', 'opening_time': '09:00', 'closing_time': '19:00', 'order': 0},
            {'day': 'tuesday', 'opening_time': '09:00', 'closing_time': '19:00', 'order': 1},
            {'day': 'wednesday', 'opening_time': '09:00', 'closing_time': '19:00', 'order': 2},
            {'day': 'thursday', 'opening_time': '09:00', 'closing_time': '19:00', 'order': 3},
            {'day': 'friday', 'opening_time': '09:00', 'closing_time': '19:00', 'order': 4},
            {'day': 'saturday', 'opening_time': '09:00', 'closing_time': '19:00', 'order': 5},
            {'day': 'sunday', 'opening_time': '10:00', 'closing_time': '17:00', 'order': 6},
        ]
        
        for hour_data in hours_data:
            hour, created = BusinessHours.objects.get_or_create(
                day=hour_data['day'],
                defaults=hour_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created business hours for {hour_data['day']}"))
        
        # Setup FAQs
        faqs = [
            {
                'question': 'How do I book an appointment?',
                'answer': 'You can book an appointment through our online booking system, by calling us at +44 161 123 4567, or by visiting our salon in person. We recommend booking at least 1-2 weeks in advance for weekend appointments.',
                'category': 'booking',
                'order': 0
            },
            {
                'question': 'What is your cancellation policy?',
                'answer': 'We require 24 hours notice for cancellations or rescheduling. Appointments cancelled with less than 24 hours notice may be subject to a 50% cancellation fee. No-shows will be charged the full service amount.',
                'category': 'policies',
                'order': 1
            },
            {
                'question': 'Do you offer gift cards?',
                'answer': 'Yes! We offer physical and digital gift cards that can be used for any of our services or products. Gift cards can be purchased in-store or over the phone.',
                'category': 'services',
                'order': 2
            },
            {
                'question': 'Is there parking available?',
                'answer': 'We have limited parking available behind the salon. There is also street parking and several public parking lots within a 5-minute walk from our location.',
                'category': 'general',
                'order': 3
            },
            {
                'question': 'Do you accommodate group bookings?',
                'answer': 'Absolutely! We love hosting groups for special occasions like bridal parties, birthdays, and corporate events. Please contact us in advance to discuss your needs and we\'ll create a customized experience for your group.',
                'category': 'booking',
                'order': 4
            },
        ]
        
        for faq_data in faqs:
            faq, created = FAQ.objects.get_or_create(
                question=faq_data['question'],
                defaults=faq_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created FAQ: {faq_data['question'][:50]}..."))
        
        # Setup quick contact options
        quick_contacts = [
            {
                'name': 'Call Us',
                'icon': 'phone',
                'label': 'Call Us',
                'url': 'tel:+441611234567',
                'order': 0
            },
            {
                'name': 'WhatsApp',
                'icon': 'whatsapp',
                'label': 'WhatsApp',
                'url': 'https://wa.me/441611234567',
                'order': 1
            },
            {
                'name': 'Get Directions',
                'icon': 'directions',
                'label': 'Get Directions',
                'url': 'https://www.google.com/maps/dir//123+Beauty+Street+Manchester+M1+1AB',
                'order': 2
            },
        ]
        
        for contact_data in quick_contacts:
            contact, created = QuickContactOption.objects.get_or_create(
                name=contact_data['name'],
                defaults=contact_data
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created quick contact: {contact_data['name']}"))
        
        self.stdout.write(self.style.SUCCESS('Contact data setup complete!'))