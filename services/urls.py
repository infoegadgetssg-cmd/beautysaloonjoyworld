# services/urls.py
from django.urls import path
from . import views

app_name = 'services'

urlpatterns = [
    path('', views.services_list, name='services_list'),
    path('category/<slug:category_slug>/', views.services_list, name='services_by_category'),
    path('service/<slug:slug>/', views.service_detail, name='service_detail'),
    path('service/<slug:slug>/review/', views.add_review, name='add_review'),
    path('stylists/', views.stylists_list, name='stylists_list'),
    path('stylist/<slug:slug>/', views.stylist_detail, name='stylist_detail'),
    path('api/services/', views.get_services_by_category, name='api_services'),
]