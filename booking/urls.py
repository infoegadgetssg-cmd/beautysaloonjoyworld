# booking/urls.py
from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    path('', views.booking_view, name='booking'),
    path('success/<int:booking_id>/', views.booking_success_view, name='booking_success'),
    path('history/', views.booking_history_view, name='booking_history'),
    path('detail/<int:booking_id>/', views.booking_detail_view, name='booking_detail'),
    path('cancel/<int:booking_id>/', views.cancel_booking_view, name='cancel_booking'),
]