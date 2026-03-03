from django.db import models
from django.conf import settings
from django.utils import timezone

class AdminDashboard(models.Model):
    """Main dashboard settings and configurations"""
    site_name = models.CharField(max_length=200, default="Joy World Beauty")
    site_logo = models.ImageField(upload_to='admin_dashboard/', null=True, blank=True)
    primary_color = models.CharField(max_length=20, default="#a86ba3")
    secondary_color = models.CharField(max_length=20, default="#d6a7c0")
    business_email = models.EmailField(default="admin@joyworldbeauty.com")
    business_phone = models.CharField(max_length=20, default="+44 161 123 4567")
    business_address = models.TextField(default="123 Beauty Street, Manchester")
    working_hours = models.TextField(default="Mon-Sat: 9am-7pm, Sun: 10am-5pm")
    booking_policy = models.TextField(default="Cancellations must be made 24 hours in advance.")
    
    class Meta:
        verbose_name_plural = "Dashboard Settings"
        app_label = 'admin_dashboard'
    
    def __str__(self):
        return "Dashboard Settings"

class DashboardNotification(models.Model):
    PRIORITY_CHOICES = [
        ('low', 'Low'),
        ('normal', 'Normal'),
        ('high', 'High'),
        ('urgent', 'Urgent'),
    ]
    
    TYPE_CHOICES = [
        ('new_booking', 'New Booking'),
        ('booking_update', 'Booking Update'),
        ('new_customer', 'New Customer'),
        ('low_stock', 'Low Stock'),
        ('message', 'Customer Message'),
        ('system', 'System Alert'),
    ]
    
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=50, choices=TYPE_CHOICES)
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='normal')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Dashboard Notifications"
        app_label = 'admin_dashboard' 
    
    def __str__(self):
        return f"{self.title} - {self.get_priority_display()}"

class RecentActivity(models.Model):
    ACTIVITY_TYPES = [
        ('booking_created', 'Booking Created'),
        ('booking_updated', 'Booking Updated'),
        ('booking_cancelled', 'Booking Cancelled'),
        ('customer_registered', 'Customer Registered'),
        ('service_added', 'Service Added'),
        ('service_updated', 'Service Updated'),
        ('product_added', 'Product Added'),
        ('product_updated', 'Product Updated'),
        ('payment_received', 'Payment Received'),
        ('message_received', 'Message Received'),
    ]
    
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    activity_type = models.CharField(max_length=50, choices=ACTIVITY_TYPES)
    description = models.TextField()
    related_id = models.CharField(max_length=100, blank=True)  # e.g., booking ID, customer ID
    related_model = models.CharField(max_length=100, blank=True)  # e.g., 'booking', 'customer'
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name_plural = "Recent Activities"
        app_label = 'admin_dashboard' 
    
    def __str__(self):
        return f"{self.get_activity_type_display()} - {self.created_at}"

    def get_icon(self):
        """Return appropriate icon for activity type"""
        icon_map = {
            'booking_created': 'calendar-plus',
            'booking_updated': 'calendar-check',
            'booking_cancelled': 'calendar-times',
            'customer_registered': 'user-plus',
            'service_added': 'spa',
            'service_updated': 'spa',
            'product_added': 'box',
            'product_updated': 'box',
            'payment_received': 'pound-sign',
            'message_received': 'envelope',
        }
        return icon_map.get(self.activity_type, 'bell')