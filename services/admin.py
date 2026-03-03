# services/admin.py
from django.contrib import admin
from django.utils.html import format_html
from .models import ServiceCategory, Service, ServiceReview, ServiceFAQ, Stylist

@admin.register(ServiceCategory)
class ServiceCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'display_order', 'is_active', 'service_count', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('display_order', 'name')

    def service_count(self, obj):
        return obj.services.count()
    service_count.short_description = 'Services'

@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'current_price', 'duration', 'is_active', 'is_on_special', 'created_at')
    list_filter = ('category', 'is_active', 'is_on_special')
    search_fields = ('name', 'short_description', 'full_description')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('package_services',)
    fieldsets = (
        ('Basic Information', {
            'fields': ('category', 'name', 'slug', 'short_description', 'full_description')
        }),
        ('Pricing & Duration', {
            'fields': ('price', 'duration', 'is_on_special', 'special_price', 'special_end_date')
        }),
        ('Media', {
            'fields': ('image', 'image_url'),
            'classes': ('collapse',)
        }),
        ('Features', {
            'fields': ('features',),
            'classes': ('collapse',)
        }),
        ('Package Settings', {
            'fields': ('is_package', 'package_services'),
            'classes': ('collapse',)
        }),
        ('Settings', {
            'fields': ('is_active', 'display_order')
        }),
    )

    def current_price(self, obj):
        if obj.is_on_special and obj.special_price:
            return f"£{obj.special_price} (Special)"
        return f"£{obj.price}"
    current_price.short_description = 'Price'

@admin.register(ServiceReview)
class ServiceReviewAdmin(admin.ModelAdmin):
    list_display = ('service', 'user', 'rating', 'is_approved', 'created_at')
    list_filter = ('rating', 'is_approved', 'created_at')
    search_fields = ('service__name', 'user__email', 'comment')
    actions = ['approve_reviews']

    def approve_reviews(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} reviews approved.")
    approve_reviews.short_description = "Approve selected reviews"

@admin.register(ServiceFAQ)
class ServiceFAQAdmin(admin.ModelAdmin):
    list_display = ('question', 'service', 'category', 'is_active', 'display_order')
    list_filter = ('is_active', 'category')
    search_fields = ('question', 'answer')
    list_editable = ('display_order', 'is_active')

@admin.register(Stylist)
class StylistAdmin(admin.ModelAdmin):
    list_display = ('name', 'title', 'experience_years', 'is_active', 'display_order')
    list_filter = ('is_active',)
    search_fields = ('name', 'title', 'bio')
    prepopulated_fields = {'slug': ('name',)}
    filter_horizontal = ('specialties',)