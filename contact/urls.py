# contact/urls.py
from django.urls import path
from . import views

app_name = 'contact'

urlpatterns = [
    path('', views.contact_view, name='contact'),
    path('quick-contact/', views.handle_quick_contact, name='quick_contact'),
    path('api/faqs/', views.faq_api, name='faq_api'),
    path('api/business-hours/', views.business_hours_api, name='business_hours_api'),
    path('unsubscribe/<str:email>/', views.unsubscribe_newsletter, name='unsubscribe'),
    path('test/', views.test_contact_view, name='test'),
]