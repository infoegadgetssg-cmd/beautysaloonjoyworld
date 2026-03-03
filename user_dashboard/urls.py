# user_dashboard/urls.py
from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'user_dashboard'

urlpatterns = [
    path('', views.user_dashboard, name='dashboard'),
    path('bookings/', views.user_bookings, name='bookings'),
    path('orders/', views.user_orders, name='orders'),
    path('profile/', views.user_profile, name='profile'),
    path('favorites/', views.user_favorites, name='favorites'),
    path('notifications/', views.user_notifications, name='notifications'),
    path('mark-all-read/', views.mark_all_read, name='mark_all_read'),
    path('favorites/add/', views.add_to_favorites, name='add_favorite'),
    path('favorites/remove/<int:favorite_id>/', views.remove_from_favorites, name='remove_favorite'),
    path('notifications/delete/<int:notification_id>/', views.delete_notification, name='delete_notification'),
    path('bookings/cancel/<int:booking_id>/', views.cancel_booking, name='cancel_booking'),
    path('api/stats/', views.get_dashboard_stats, name='api_stats'),
    path('password-change/', auth_views.PasswordChangeView.as_view(
             template_name='user_dashboard/password_change.html'
         ), 
         name='password_change'),
    
    path('password-change/done/', 
         auth_views.PasswordChangeDoneView.as_view(
             template_name='user_dashboard/password_change_done.html'
         ), 
         name='password_change_done'),
]