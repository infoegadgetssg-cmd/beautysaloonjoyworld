# booking/urls.py
from django.urls import path
from . import views

app_name = 'booking'

urlpatterns = [
    path('', views.booking_view, name='booking'),
    path('cancellation-policy/', views.cancellation_policy_view, name='cancellation_policy'),
    path('success/<int:booking_id>/', views.booking_success_view, name='booking_success'),
    path('history/', views.booking_history_view, name='booking_history'),
    path('detail/<int:booking_id>/', views.booking_detail_view, name='booking_detail'),
    path('payment/<int:booking_id>/', views.booking_payment_view, name='booking_payment'),
    path('verify-payment/<int:booking_id>/', views.verify_booking_payment_view, name='verify_booking_payment'),
    path('admin-booking-calendar/', views.admin_booking_calendar, name='admin_booking_calendar'),
    path('bookings-json/', views.bookings_json, name='bookings_json'),
    path('cancel/<int:booking_id>/', views.cancel_booking_view, name='cancel_booking'),
]
