# dashboard/urls.py
from django.urls import path
from . import views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='index'),
    path('bookings/', views.bookings_management, name='bookings'),
    path('customers/', views.customers_management, name='customers'),
    path('services/', views.services_management, name='services'),
    path('products/', views.products_management, name='products'),
    path('gallery/', views.gallery_management, name='gallery'),
    path('messages/', views.messages_management, name='messages'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('settings/', views.settings_view, name='settings'),
    
    # API endpoints
    path('api/stats/', views.get_dashboard_stats, name='api_stats'),
    path('api/booking/<int:booking_id>/update-status/', views.update_booking_status, name='update_booking_status'),
    path('api/service/<int:service_id>/', views.get_service_data, name='get_service_data'),
    path('service/<int:service_id>/update/', views.update_service, name='update_service'),
    path('service/<int:service_id>/delete/', views.delete_service, name='delete_service'),
    
    # Gallery endpoints
    path('api/gallery-image/<int:image_id>/', views.get_gallery_image, name='get_gallery_image'),
    path('gallery-image/add/', views.add_gallery_image, name='add_image'),
    path('gallery-image/<int:image_id>/update/', views.update_gallery_image, name='update_gallery_image'),
    path('gallery-image/<int:image_id>/delete/', views.delete_gallery_image, name='delete_gallery_image'),
    
    # Product endpoints
    path('api/product/<int:product_id>/', views.get_product_data, name='get_product_data'),
    path('product/<int:product_id>/update/', views.update_product, name='update_product'),
    path('product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('product/<int:product_id>/update-stock/', views.update_product_stock, name='update_product_stock'),
]