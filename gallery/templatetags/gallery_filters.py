# gallery/templatetags/gallery_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """Get item from dictionary in template - safe version"""
    if dictionary and hasattr(dictionary, 'get'):
        return dictionary.get(key, 0)
    return 0

@register.filter
def multiply(value, arg):
    """Multiply value by arg"""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        return 0