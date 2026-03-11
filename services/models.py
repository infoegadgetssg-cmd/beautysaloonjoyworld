# services/models.py
from django.db import models
from django.conf import settings
from django.utils.text import slugify

class ServiceCategory(models.Model):
    """Categories for beauty services"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Font Awesome icon class")
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Service Categories"
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

class Service(models.Model):
    """Beauty services offered by the salon"""
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='services')
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    short_description = models.TextField(max_length=200)
    full_description = models.TextField()
    price = models.DecimalField(max_digits=8, decimal_places=2)
    duration = models.IntegerField(help_text="Duration in minutes")
    image = models.ImageField(upload_to='services/', blank=True, null=True)
    image_url = models.URLField(blank=True, help_text="External image URL if not uploading")
    features = models.JSONField(default=list, help_text="List of features as JSON array")
    is_active = models.BooleanField(default=True)
    display_order = models.IntegerField(default=0)
    SERVICE_COLORS = [
        ('#3b82f6', 'Blue'),
        ('#9333ea', 'Purple'),
        ('#10b981', 'Green'),
        ('#f59e0b', 'Orange'),
        ('#ef4444', 'Red'),
        ('#06b6d4', 'Cyan'),
        ('#ec4899', 'Pink'),
        ('#84cc16', 'Lime'),
        ('#6366f1', 'Indigo'),
        ('#64748b', 'Gray'),
    ]
    service_color = models.CharField(max_length=7, choices=SERVICE_COLORS, default='#3b82f6')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Add this field for booking compatibility
    is_available = models.BooleanField(default=True, verbose_name="Available for booking") 

    # If you need a category field that works with booking, add:
    CATEGORY_CHOICES = [
        ('facial', 'Facials & Skincare'),
        ('makeup', 'Makeup Artistry'),
        ('nails', 'Manicure & Pedicure'),
        ('hair', 'Hair Styling'),
        ('waxing', 'Waxing'),
    ]
    booking_category = models.CharField(
        max_length=50, 
        choices=CATEGORY_CHOICES, 
        default='hair',
        blank=True,
        null=True,
        verbose_name="Booking Category"
    )

    # For package services
    is_package = models.BooleanField(default=False)
    package_services = models.ManyToManyField('self', blank=True, symmetrical=False)
    
    # For promotional offers
    is_on_special = models.BooleanField(default=False)
    special_price = models.DecimalField(max_digits=8, decimal_places=2, blank=True, null=True)
    special_end_date = models.DateField(blank=True, null=True)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            base_slug = slugify(self.name) or 'service'
            slug = base_slug
            counter = 1
            while Service.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            self.slug = slug
        super().save(*args, **kwargs)

    @property
    def current_price(self):
        """Return special price if available, otherwise regular price"""
        return self.special_price if self.is_on_special and self.special_price else self.price

    @property
    def formatted_duration(self):
        """Format duration in hours and minutes"""
        hours = self.duration // 60
        minutes = self.duration % 60
        
        if hours > 0 and minutes > 0:
            return f"{hours}h {minutes}min"
        elif hours > 0:
            return f"{hours}h"
        else:
            return f"{minutes}min"

class ServiceReview(models.Model):
    """Customer reviews for services"""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)])
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_approved = models.BooleanField(default=False)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['service', 'user']

    def __str__(self):
        return f"{self.user.email} - {self.service.name} ({self.rating}/5)"

class ServiceFAQ(models.Model):
    """Frequently Asked Questions for services"""
    service = models.ForeignKey(Service, on_delete=models.CASCADE, related_name='faqs', blank=True, null=True)
    category = models.ForeignKey(ServiceCategory, on_delete=models.CASCADE, related_name='faqs', blank=True, null=True)
    question = models.CharField(max_length=500)
    answer = models.TextField()
    display_order = models.IntegerField(default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['display_order', '-created_at']
        verbose_name = "Service FAQ"
        verbose_name_plural = "Service FAQs"

    def __str__(self):
        return self.question[:100]

class Stylist(models.Model):
    """Beauty salon stylists/therapists"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    title = models.CharField(max_length=100, blank=True)
    bio = models.TextField()
    image = models.ImageField(upload_to='stylists/', blank=True, null=True)
    experience_years = models.IntegerField(default=0)
    specialties = models.ManyToManyField(Service, blank=True, related_name='specialists')
    is_active = models.BooleanField(default=True)
    is_available = models.BooleanField(default=True)
    work_days = models.CharField(max_length=255, blank=True, default="", help_text="Example: Monday, Tuesday, Wednesday")
    shift_start = models.TimeField(blank=True, null=True)
    shift_end = models.TimeField(blank=True, null=True)
    rating = models.DecimalField(max_digits=3, decimal_places=2, default=5.0)
    display_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Social media and contact
    instagram = models.URLField(blank=True)
    facebook = models.URLField(blank=True)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=20, blank=True)

    class Meta:
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    @property
    def full_title(self):
        """Return stylist's full title with experience"""
        if self.title and self.experience_years > 0:
            return f"{self.title} with {self.experience_years} years experience"
        elif self.title:
            return self.title
        elif self.experience_years > 0:
            return f"Beauty Specialist with {self.experience_years} years experience"
        return "Beauty Specialist"
