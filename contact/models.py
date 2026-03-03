# contact/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

class ContactMessage(models.Model):
    """Contact form messages"""
    STATUS_CHOICES = [
        ('new', 'New'),
        ('read', 'Read'),
        ('replied', 'Replied'),
        ('archived', 'Archived'),
    ]
    
    TOPIC_CHOICES = [
        ('general', 'General Inquiry'),
        ('booking', 'Booking Question'),
        ('service', 'Service Information'),
        ('product', 'Product Question'),
        ('complaint', 'Complaint'),
        ('other', 'Other'),
    ]
    
    # Contact information
    name = models.CharField(max_length=200)
    email = models.EmailField()
    phone = models.CharField(max_length=20, blank=True)
    
    # Message details
    subject = models.CharField(max_length=200)
    topic = models.CharField(max_length=20, choices=TOPIC_CHOICES, default='general')
    message = models.TextField()
    
    # Newsletter subscription from contact form
    subscribe_newsletter = models.BooleanField(default=False)
    
    # Status tracking
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    is_read = models.BooleanField(default=False)
    
    # Admin response
    admin_response = models.TextField(blank=True)
    responded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='responded_messages'
    )
    responded_at = models.DateTimeField(null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"
    
    def __str__(self):
        return f"{self.name} - {self.subject} ({self.status})"
    
    def mark_as_read(self):
        self.is_read = True
        self.save()
    
    def mark_as_replied(self, user, response):
        self.status = 'replied'
        self.admin_response = response
        self.responded_by = user
        self.responded_at = timezone.now()
        self.save()


class FAQ(models.Model):
    """Frequently Asked Questions - matches your design"""
    CATEGORY_CHOICES = [
        ('general', 'General'),
        ('booking', 'Booking'),
        ('services', 'Services'),
        ('products', 'Products'),
        ('pricing', 'Pricing'),
        ('policies', 'Policies'),
    ]
    
    question = models.TextField()
    answer = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='general')
    order = models.IntegerField(default=0, help_text="Display order (lower numbers first)")
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['order', 'category']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
    
    def __str__(self):
        return f"{self.question[:50]}..."


class NewsletterSubscriber(models.Model):
    """Newsletter subscribers from contact form and other sources"""
    email = models.EmailField(unique=True)
    name = models.CharField(max_length=100, blank=True)
    source = models.CharField(max_length=50, default='contact_form', choices=[
        ('contact_form', 'Contact Form'),
        ('website_signup', 'Website Signup'),
        ('in_store', 'In-Store Signup'),
        ('event', 'Event'),
    ])
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    subscribed_at = models.DateTimeField(auto_now_add=True)
    unsubscribed_at = models.DateTimeField(null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Newsletter Subscriber"
        verbose_name_plural = "Newsletter Subscribers"
    
    def __str__(self):
        return self.email
    
    def unsubscribe(self):
        self.is_active = False
        self.unsubscribed_at = timezone.now()
        self.save()


class SalonLocation(models.Model):
    """Salon location and contact info - matches your design"""
    name = models.CharField(max_length=200, default="Joy World Home of Beauty")
    address = models.TextField(default="123 Beauty Street\nManchester M1 1AB\nUnited Kingdom")
    phone = models.CharField(max_length=20, default="+44 161 123 4567")
    email = models.EmailField(default="info@joyworldbeauty.com")
    
    # Social media links
    facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True)
    twitter_url = models.URLField(blank=True)
    pinterest_url = models.URLField(blank=True)
    
    # Map coordinates
    latitude = models.DecimalField(max_digits=9, decimal_places=6, default=53.480372)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, default=-2.242722)
    google_maps_embed_url = models.TextField(default="https://www.google.com/maps/embed?pb=!1m18!1m12!1m3!1d2374.437839120938!2d-2.242722123025946!3d53.48037207232278!2m3!1f0!2f0!3f0!3m2!1i1024!2i768!4f13.1!3m3!1m2!1s0x487bb1c16ecb7dd7%3A0x3f10e98ed6358d2e!2sManchester%2C%20UK!5e0!3m2!1sen!2sus!4v1681234567890!5m2!1sen!2sus")
    
    # Active location flag
    is_active = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Salon Location"
        verbose_name_plural = "Salon Locations"
    
    def __str__(self):
        return self.name


class BusinessHours(models.Model):
    """Business hours - matches your design exactly"""
    DAY_CHOICES = [
        ('monday', 'Monday'),
        ('tuesday', 'Tuesday'),
        ('wednesday', 'Wednesday'),
        ('thursday', 'Thursday'),
        ('friday', 'Friday'),
        ('saturday', 'Saturday'),
        ('sunday', 'Sunday'),
    ]
    
    day = models.CharField(max_length=10, choices=DAY_CHOICES, unique=True)
    opening_time = models.TimeField()
    closing_time = models.TimeField()
    is_closed = models.BooleanField(default=False)
    notes = models.CharField(max_length=100, blank=True, help_text="e.g., 'By appointment only'")
    
    # Display order
    order = models.IntegerField(default=0)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Business Hour"
        verbose_name_plural = "Business Hours"
    
    def __str__(self):
        return self.get_day_display()
    
    def get_formatted_hours(self):
        if self.is_closed:
            return "Closed"
        return f"{self.opening_time.strftime('%I:%M %p')} - {self.closing_time.strftime('%I:%M %p')}"


class QuickContactOption(models.Model):
    """Quick contact options (Call, WhatsApp, Directions)"""
    ICON_CHOICES = [
        ('phone', 'fas fa-phone'),
        ('whatsapp', 'fab fa-whatsapp'),
        ('directions', 'fas fa-directions'),
        ('calendar', 'fas fa-calendar'),
        ('envelope', 'fas fa-envelope'),
    ]
    
    name = models.CharField(max_length=50)
    icon = models.CharField(max_length=20, choices=ICON_CHOICES)
    label = models.CharField(max_length=100)
    url = models.CharField(max_length=500, help_text="For phone: tel:+441611234567, For WhatsApp: https://wa.me/441611234567, For email: mailto:info@example.com")
    order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order']
        verbose_name = "Quick Contact Option"
        verbose_name_plural = "Quick Contact Options"
    
    def __str__(self):
        return self.name
    

class Testimonial(models.Model):
    name = models.CharField(max_length=100)
    content = models.TextField()
    rating = models.IntegerField(default=5)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Testimonial from {self.name}"