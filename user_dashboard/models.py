# user_dashboard/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone
from services.models import Service  
from shop.models import Product

class UserFavorite(models.Model):
    """User's favorite services/products"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    service = models.ForeignKey(Service, on_delete=models.CASCADE, null=True, blank=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = [('user', 'service'), ('user', 'product')]
        verbose_name_plural = "User Favorites"
    
    def __str__(self):
        if self.service:
            return f"{self.user.email} - {self.service.name}"
        else:
            return f"{self.user.email} - {self.product.name}"

class UserNotification(models.Model):
    """User notifications"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=[
        ('booking_confirmation', 'Booking Confirmation'),
        ('booking_reminder', 'Booking Reminder'),
        ('booking_update', 'Booking Update'),
        ('promotion', 'Promotion'),
        ('newsletter', 'Newsletter'),
        ('system', 'System'),
    ])
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "User Notifications"
    
    def __str__(self):
        return f"{self.user.email} - {self.title}"

class LoyaltyProgram(models.Model):
    """Loyalty program levels and points"""
    LEVEL_CHOICES = [
        ('explorer', 'Beauty Explorer'),
        ('lover', 'Beauty Lover'),
        ('enthusiast', 'Beauty Enthusiast'),
        ('vip', 'Beauty VIP'),
    ]
    
    level = models.CharField(max_length=20, choices=LEVEL_CHOICES, unique=True)
    points_required = models.IntegerField()
    icon_class = models.CharField(max_length=50, default='fas fa-seedling')
    benefits = models.TextField()
    
    class Meta:
        verbose_name_plural = "Loyalty Programs"
    
    def __str__(self):
        return self.get_level_display()

class UserLoyalty(models.Model):
    """User's loyalty points and level"""
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    points = models.IntegerField(default=0)
    level = models.ForeignKey(LoyaltyProgram, on_delete=models.SET_NULL, null=True)
    total_spent = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name_plural = "User Loyalty"
    
    def __str__(self):
        return f"{self.user.email} - {self.points} points"
    
    def update_level(self):
        """Update user's loyalty level based on points"""
        levels = LoyaltyProgram.objects.order_by('points_required')
        new_level = None
        
        for level in levels:
            if self.points >= level.points_required:
                new_level = level
        
        if new_level and new_level != self.level:
            self.level = new_level
            self.save()
            return True
        return False