# contact/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.mail import send_mail, EmailMessage
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse
from django.template.loader import render_to_string
import json

from .models import ContactMessage, FAQ, SalonLocation, BusinessHours, QuickContactOption, NewsletterSubscriber
from .forms import ContactForm, NewsletterSignupForm, QuickContactForm
from core.notifications import send_contact_notifications


def contact_view(request):
    """Main contact page view"""
    # Get salon location (active one)
    try:
        salon = SalonLocation.objects.filter(is_active=True).first()
    except SalonLocation.DoesNotExist:
        salon = None
    
    # Get business hours
    business_hours = BusinessHours.objects.all().order_by('order')
    
    # Get FAQs
    faqs = FAQ.objects.filter(is_active=True).order_by('order', 'category')
    
    # Get quick contact options
    quick_contact_options = QuickContactOption.objects.filter(is_active=True).order_by('order')
    
    # Handle contact form submission
    contact_form = ContactForm()
    newsletter_form = NewsletterSignupForm()
    
    if request.method == 'POST':
        if 'contact_submit' in request.POST:
            contact_form = ContactForm(request.POST)
            if contact_form.is_valid():
                # Save contact message
                contact_message = contact_form.save(commit=False)
                
                # If user is logged in, we could associate with user
                if request.user.is_authenticated:
                    # Optionally associate with user if you have user profiles
                    pass
                
                contact_message.save()
                send_contact_notifications(contact_message)
                
                # Handle newsletter subscription if selected
                if contact_form.cleaned_data.get('subscribe_newsletter'):
                    email = contact_form.cleaned_data['email']
                    name = contact_form.cleaned_data['name']
                    
                    # Check if already subscribed
                    subscriber, created = NewsletterSubscriber.objects.get_or_create(
                        email=email,
                        defaults={
                            'name': name,
                            'source': 'contact_form'
                        }
                    )
                    
                    if not created and not subscriber.is_active:
                        subscriber.is_active = True
                        subscriber.unsubscribed_at = None
                        subscriber.save()
                
                messages.success(request, 'Thank you for your message! We will get back to you within 24 hours.')
                return redirect('contact:contact')
        
        elif 'newsletter_submit' in request.POST:
            newsletter_form = NewsletterSignupForm(request.POST)
            if newsletter_form.is_valid():
                subscriber = newsletter_form.save(commit=False)
                subscriber.source = 'website_signup'
                subscriber.save()
                
                # Send welcome email to newsletter subscribers
                try:
                    subject = 'Welcome to Joy World Beauty Newsletter'
                    message = render_to_string('contact/emails/newsletter_welcome.html', {
                        'name': subscriber.name or 'Beauty Lover',
                    })
                    
                    email = EmailMessage(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [subscriber.email]
                    )
                    email.content_subtype = "html"
                    email.send(fail_silently=True)
                except Exception as e:
                    print(f"Error sending welcome email: {e}")
                
                messages.success(request, 'Thank you for subscribing to our newsletter!')
                return redirect('contact:contact')
    
    context = {
        'salon': salon,
        'business_hours': business_hours,
        'faqs': faqs,
        'quick_contact_options': quick_contact_options,
        'contact_form': contact_form,
        'newsletter_form': newsletter_form,
        'page_title': 'Contact Us | Joy World Home of Beauty',
        'meta_description': 'Get in touch with Joy World Beauty Salon. Contact us for appointments, questions, or feedback. We\'re here to help with all your beauty needs.',
    }
    
    return render(request, 'contact/contact.html', context)


def handle_quick_contact(request):
    """Handle quick contact AJAX requests"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            contact_method = data.get('method')

            response_data = {
                'success': True,
                'message': 'Thank you for your interest!',
            }

            # Try to get salon location data from the database
            salon = SalonLocation.objects.filter(is_active=True).first()

            # Defaults (fallback if no SalonLocation exists)
            phone = '+441611234567'
            address_query = '123+Beauty+Street+Manchester+M1+1AB'

            if salon:
                if salon.phone:
                    phone = salon.phone.replace(' ', '').replace('-', '')
                if salon.address:
                    address_query = salon.address.replace(' ', '+')

            # Handle different contact methods
            if contact_method == 'call':
                response_data['action'] = 'redirect'
                response_data['url'] = f'tel:{phone}'
            elif contact_method == 'whatsapp':
                response_data['action'] = 'redirect'
                response_data['url'] = f'https://wa.me/{phone.lstrip("+")}'
            elif contact_method == 'directions':
                response_data['action'] = 'redirect'
                response_data['url'] = f'https://www.google.com/maps/dir//{address_query}'

            return JsonResponse(response_data)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})

    return JsonResponse({'success': False, 'message': 'Invalid request'})


def faq_api(request):
    """API endpoint for FAQ data"""
    faqs = FAQ.objects.filter(is_active=True).order_by('order', 'category')
    
    faq_data = []
    for faq in faqs:
        faq_data.append({
            'question': faq.question,
            'answer': faq.answer,
            'category': faq.get_category_display(),
        })
    
    return JsonResponse({'faqs': faq_data})


def business_hours_api(request):
    """API endpoint for business hours"""
    hours = BusinessHours.objects.all().order_by('order')
    
    hours_data = []
    for hour in hours:
        hours_data.append({
            'day': hour.get_day_display(),
            'hours': hour.get_formatted_hours(),
            'is_closed': hour.is_closed,
            'notes': hour.notes,
        })
    
    return JsonResponse({'hours': hours_data})


def unsubscribe_newsletter(request, email):
    """Handle newsletter unsubscribe"""
    try:
        subscriber = NewsletterSubscriber.objects.get(email=email)
        subscriber.unsubscribe()
        messages.success(request, 'You have been unsubscribed from our newsletter.')
    except NewsletterSubscriber.DoesNotExist:
        messages.error(request, 'Email not found in our subscription list.')
    
    return redirect('index')


# contact/views.py - Add this at the end
def test_contact_view(request):
    """Test view to verify contact app is working"""
    return JsonResponse({
        'status': 'success',
        'message': 'Contact app is working!',
        'data': {
            'contact_form_fields': list(ContactForm().fields.keys()),
            'faqs_count': FAQ.objects.count(),
            'salon_exists': SalonLocation.objects.filter(is_active=True).exists(),
            'business_hours_count': BusinessHours.objects.count(),
        }
    })
