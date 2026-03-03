from django.contrib import admin
from .models import Booking, AdditionalService, BookingAdditionalService


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ['user', 'service', 'stylist', 'date', 'time', 'status', 'total_price']
    list_filter = ['status', 'date', 'service']
    search_fields = ['user__email', 'service__name', 'stylist__name']
    date_hierarchy = 'date'


@admin.register(AdditionalService)
class AdditionalServiceAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'is_available']
    list_filter = ['is_available']
    search_fields = ['name']


@admin.register(BookingAdditionalService)
class BookingAdditionalServiceAdmin(admin.ModelAdmin):
    list_display = ['booking', 'additional_service', 'quantity']
    list_filter = ['additional_service']
