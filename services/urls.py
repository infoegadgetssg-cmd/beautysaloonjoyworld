# services/urls.py
from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.services_list, name='services_list'),
    path('dashboard/stylists/', views.stylist_management, name='dashboard_stylists'),
    path('dashboard/stylists/<int:stylist_id>/update/', views.update_stylist, name='dashboard_update_stylist'),
    path('dashboard/stylists/<int:stylist_id>/delete/', views.delete_stylist, name='dashboard_delete_stylist'),
    path('category/<slug:category_slug>/', views.services_list, name='services_by_category'),
    path('service/<slug:slug>/', views.service_detail, name='service_detail'),
    path('service/<slug:slug>/review/', views.add_review, name='add_review'),
    path('stylists/', views.stylists_list, name='stylists_list'),
    path('stylist/<slug:slug>/', views.stylist_detail, name='stylist_detail'),
    path('api/services/', views.get_services_by_category, name='api_services'),
]
