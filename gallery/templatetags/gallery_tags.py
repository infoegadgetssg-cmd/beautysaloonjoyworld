# gallery/templatetags/gallery_tags.py
from django import template
from django.db.models import Count
from gallery.models import GalleryCategory, GalleryImage

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary in template"""
    return dictionary.get(key, 0)

@register.inclusion_tag('gallery/includes/category_filters.html')
def gallery_category_filters(active_category=None):
    """Render gallery category filters"""
    categories = GalleryCategory.objects.filter(
        is_active=True
    ).annotate(
        image_count=Count('images')
    ).filter(
        image_count__gt=0
    ).order_by('order', 'name')
    
    return {
        'categories': categories,
        'active_category': active_category,
    }

@register.inclusion_tag('gallery/includes/featured_images.html')
def featured_images(count=4):
    """Render featured gallery images"""
    images = GalleryImage.objects.filter(
        is_published=True,
        image_type='featured'
    ).select_related('category').order_by('display_order', '-created_at')[:count]
    
    return {'images': images}

@register.simple_tag
def get_category_color(category_slug):
    """Get category color by slug"""
    try:
        category = GalleryCategory.objects.get(slug=category_slug, is_active=True)
        return category.color
    except GalleryCategory.DoesNotExist:
        return '#a86ba3'  # Default color

@register.filter
def get_category_by_slug(slug):
    """Get category object by slug"""
    try:
        return GalleryCategory.objects.get(slug=slug, is_active=True)
    except GalleryCategory.DoesNotExist:
        return None
    

    