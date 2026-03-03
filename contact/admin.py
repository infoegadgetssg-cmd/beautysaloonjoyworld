# contact/admin.py
from django.contrib import admin
from .models import ContactMessage, FAQ, SalonLocation, BusinessHours, QuickContactOption, NewsletterSubscriber, Testimonial

@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ['name', 'email', 'topic', 'status', 'created_at']
    list_filter = ['status', 'topic', 'created_at']
    search_fields = ['name', 'email', 'subject', 'message']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Contact Information', {
            'fields': ('name', 'email', 'phone')
        }),
        ('Message Details', {
            'fields': ('subject', 'topic', 'message', 'subscribe_newsletter')
        }),
        ('Status & Response', {
            'fields': ('status', 'is_read', 'admin_response', 'responded_by', 'responded_at')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def mark_as_read(self, request, queryset):
        queryset.update(is_read=True, status='read')
        self.message_user(request, f"{queryset.count()} messages marked as read.")
    
    def mark_as_replied(self, request, queryset):
        for message in queryset:
            message.mark_as_replied(request.user, "Replied via admin")
        self.message_user(request, f"{queryset.count()} messages marked as replied.")
    
    actions = [mark_as_read, mark_as_replied]

@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'order', 'is_active']
    list_filter = ['category', 'is_active']
    search_fields = ['question', 'answer']
    list_editable = ['order', 'is_active']

@admin.register(SalonLocation)
class SalonLocationAdmin(admin.ModelAdmin):
    list_display = ['name', 'phone', 'email', 'is_active']
    list_editable = ['is_active']

@admin.register(BusinessHours)
class BusinessHoursAdmin(admin.ModelAdmin):
    list_display = ['day', 'opening_time', 'closing_time', 'is_closed', 'order']
    list_editable = ['opening_time', 'closing_time', 'is_closed', 'order']
    ordering = ['order']

@admin.register(QuickContactOption)
class QuickContactOptionAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'label', 'order', 'is_active']
    list_editable = ['order', 'is_active']
    ordering = ['order']

@admin.register(NewsletterSubscriber)
class NewsletterSubscriberAdmin(admin.ModelAdmin):
    list_display = ['email', 'name', 'source', 'is_active', 'subscribed_at']
    list_filter = ['is_active', 'source', 'subscribed_at']
    search_fields = ['email', 'name']
    readonly_fields = ['subscribed_at', 'unsubscribed_at', 'last_updated']
    
    def unsubscribe_selected(self, request, queryset):
        for subscriber in queryset:
            subscriber.unsubscribe()
        self.message_user(request, f"{queryset.count()} subscribers unsubscribed.")
    
    actions = [unsubscribe_selected]

@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ['name', 'rating', 'is_active', 'created_at']
    list_filter = ['rating', 'is_active']
    search_fields = ['name', 'content']
    list_editable = ['is_active']