from django.contrib import admin
from .models import UserFavorite, UserNotification, LoyaltyProgram, UserLoyalty


@admin.register(UserFavorite)
class UserFavoriteAdmin(admin.ModelAdmin):
    list_display = ['user', 'service', 'product', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__email', 'service__name', 'product__name']


@admin.register(UserNotification)
class UserNotificationAdmin(admin.ModelAdmin):
    list_display = ['user', 'title', 'notification_type', 'is_read', 'created_at']
    list_filter = ['notification_type', 'is_read', 'created_at']
    search_fields = ['user__email', 'title']


@admin.register(LoyaltyProgram)
class LoyaltyProgramAdmin(admin.ModelAdmin):
    list_display = ['level', 'points_required', 'icon_class']
    ordering = ['points_required']


@admin.register(UserLoyalty)
class UserLoyaltyAdmin(admin.ModelAdmin):
    list_display = ['user', 'points', 'level', 'total_spent', 'last_updated']
    list_filter = ['level']
    search_fields = ['user__email']
