# gallery/urls.py
from django.urls import path
from . import views

app_name = 'gallery'

urlpatterns = [
    # Main gallery page
    path('', views.GalleryView.as_view(), name='gallery'),
    
    # Category pages
    path('category/<slug:slug>/', views.GalleryCategoryView.as_view(), name='category'),
    
    # Image detail page
    path('image/<slug:slug>/', views.ImageDetailView.as_view(), name='image_detail'),
    
    # AJAX endpoints
    path('filter/', views.gallery_filter_view, name='filter'),
    path('before-after/', views.before_after_data, name='before_after_data'),
    path('like/<int:image_id>/', views.toggle_image_like, name='toggle_like'),
    
    # API endpoint
    path('api/images/', views.GalleryImageView.as_view(), name='api_images'),
]