# dashboard/urls.py
from django.urls import path
from . import views
from booking import views as booking_views

app_name = 'admin_dashboard'

urlpatterns = [
    path('', views.dashboard_index, name='index'),
    path('bookings/', views.bookings_management, name='bookings'),
    path('bookings/calendar/', booking_views.admin_booking_calendar, name='bookings_calendar'),
    path('customers/', views.customers_management, name='customers'),
    path('customers/<int:user_id>/', views.customer_detail_view, name='customer_detail'),
    path('services/', views.services_management, name='services'),
    path('products/', views.products_management, name='products'),
    path('gallery/', views.gallery_management, name='gallery'),
    path('gallery/categories/', views.gallery_categories_management, name='gallery_categories'),
    path('messages/', views.messages_management, name='messages'),
    path('analytics/', views.analytics_view, name='analytics'),
    path('settings/', views.settings_view, name='settings'),
    
    # API endpoints
    path('api/stats/', views.get_dashboard_stats, name='api_stats'),
    path('api/booking/<int:booking_id>/update-status/', views.update_booking_status, name='update_booking_status'),
    path('api/booking/<int:booking_id>/mark-refunded/', views.mark_booking_refunded, name='mark_booking_refunded'),
    path('api/messages/', views.messages_api, name='messages_api'),
    path('api/service/<int:service_id>/', views.get_service_data, name='get_service_data'),
    path('api/service-category/create/', views.create_service_category, name='create_service_category'),
    path('api/service-category/<int:category_id>/update/', views.update_service_category, name='update_service_category'),
    path('api/service-category/<int:category_id>/delete/', views.delete_service_category, name='delete_service_category'),
    path('service/<int:service_id>/update/', views.update_service, name='update_service'),
    path('service/<int:service_id>/delete/', views.delete_service, name='delete_service'),
    
    # Gallery endpoints
    path('api/gallery-image/<int:image_id>/', views.get_gallery_image, name='get_gallery_image'),
    path('api/gallery-categories/', views.list_gallery_categories, name='list_gallery_categories'),
    path('api/gallery-category/create/', views.create_gallery_category, name='create_gallery_category'),
    path('api/gallery-category/<int:category_id>/update/', views.update_gallery_category, name='update_gallery_category'),
    path('api/gallery-category/<int:category_id>/delete/', views.delete_gallery_category, name='delete_gallery_category'),
    path('gallery-image/add/', views.add_gallery_image, name='add_image'),
    path('gallery-image/<int:image_id>/update/', views.update_gallery_image, name='update_gallery_image'),
    path('gallery-image/<int:image_id>/delete/', views.delete_gallery_image, name='delete_gallery_image'),
    
    # Product endpoints
    path('api/product/<int:product_id>/', views.get_product_data, name='get_product_data'),
    path('product/<int:product_id>/update/', views.update_product, name='update_product'),
    path('product/<int:product_id>/delete/', views.delete_product, name='delete_product'),
    path('product/<int:product_id>/update-stock/', views.update_product_stock, name='update_product_stock'),
]
