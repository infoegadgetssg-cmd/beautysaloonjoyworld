# contact/management/commands/load_initial_data.py
from django.core.management.base import BaseCommand
from django.utils import timezone
from contact.models import (
    SalonLocation, BusinessHours, FAQ, QuickContactOption
)


class Command(BaseCommand):
    help = 'Load initial contact data'

    def handle(self, *args, **options):
        # Create salon location
        salon, created = SalonLocation.objects.get_or_create(
            name="Joy World Home of Beauty",
            defaults={
                'address': '123 Beauty Street\nManchester M1 1AB\nUnited Kingdom',
                'phone': '+44 161 123 4567',
                'email': 'info@joyworldbeauty.com',
                'facebook_url': 'https://facebook.com/joyworldbeauty',
                'instagram_url': 'https://instagram.com/joyworldbeauty',
                'twitter_url': 'https://twitter.com/joyworldbeauty',
                'pinterest_url': 'https://pinterest.com/joyworldbeauty',
                'latitude': 53.480372,
                'longitude': -2.242722,
                'google_maps_embed_url': 'https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2374.437839120938!2d-2.242722123025946!3d53.48037207232278!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x487bb1c16ecb7dd7%3A0x3f10e98ed6358d2e!2sManchester%2C%20UK!5e0!3m2!1sen!2sus!4v1681234567890!5m2!1sen!2sus',
                'is_active': True,
            }
        )
        
        if created:
            self.stdout.write(self.style.SUCCESS('Created salon location'))
        
        # Create business hours
        business_hours_data = [
            ('monday', '09:00', '19:00', False, 0),
            ('tuesday', '09:00', '19:00', False, 1),
            ('wednesday', '09:00', '19:00', False, 2),
            ('thursday', '09:00', '19:00', False, 3),
            ('friday', '09:00', '19:00', False, 4),
            ('saturday', '09:00', '19:00', False, 5),
            ('sunday', '10:00', '17:00', False, 6),
        ]
        
        for day, open_time, close_time, is_closed, order in business_hours_data:
            hour, created = BusinessHours.objects.get_or_create(
                day=day,
                defaults={
                    'opening_time': open_time,
                    'closing_time': close_time,
                    'is_closed': is_closed,
                    'order': order,
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Created business hours'))
        
        # Create FAQs
        faqs_data = [
            ('How do I book an appointment?',
             'You can book an appointment through our online booking system, by calling us at +44 161 123 4567, or by visiting our salon in person. We recommend booking at least 1-2 weeks in advance for weekend appointments.',
             'booking', 0),
            
            ('What is your cancellation policy?',
             'We require 24 hours notice for cancellations or rescheduling. Appointments cancelled with less than 24 hours notice may be subject to a 50% cancellation fee. No-shows will be charged the full service amount.',
             'policies', 1),
            
            ('Do you offer gift cards?',
             'Yes! We offer physical and digital gift cards that can be used for any of our services or products. Gift cards can be purchased in-store or over the phone.',
             'general', 2),
            
            ('Is there parking available?',
             'We have limited parking available behind the salon. There is also street parking and several public parking lots within a 5-minute walk from our location.',
             'general', 3),
            
            ('Do you accommodate group bookings?',
             'Absolutely! We love hosting groups for special occasions like bridal parties, birthdays, and corporate events. Please contact us in advance to discuss your needs and we\'ll create a customized experience for your group.',
             'booking', 4),
        ]
        
        for question, answer, category, order in faqs_data:
            faq, created = FAQ.objects.get_or_create(
                question=question,
                defaults={
                    'answer': answer,
                    'category': category,
                    'order': order,
                    'is_active': True,
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Created FAQs'))
        
        # Create quick contact options
        quick_contact_data = [
            ('Call', 'phone', 'Call Us', 'tel:+441611234567', 0),
            ('WhatsApp', 'whatsapp', 'WhatsApp', 'https://wa.me/441611234567', 1),
            ('Directions', 'directions', 'Get Directions', 'https://www.google.com/maps/dir//123+Beauty+Street+Manchester+M1+1AB', 2),
        ]
        
        for name, icon, label, url, order in quick_contact_data:
            option, created = QuickContactOption.objects.get_or_create(
                name=name,
                defaults={
                    'icon': icon,
                    'label': label,
                    'url': url,
                    'order': order,
                    'is_active': True,
                }
            )
        
        self.stdout.write(self.style.SUCCESS('Created quick contact options'))
        self.stdout.write(self.style.SUCCESS('Successfully loaded all initial contact data!'))