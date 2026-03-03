# shop/templatetags/shop_filters.py
from django import template
from django.db.models import Avg

register = template.Library()

@register.filter
def average_rating(reviews):
    """Calculate average rating from reviews queryset"""
    if reviews.exists():
        avg = reviews.aggregate(Avg('rating'))['rating__avg']
        return round(avg, 1) if avg else 0
    return 0

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument."""
    try:
        return int(value) * int(arg)
    except (ValueError, TypeError):
        try:
            return float(value) * float(arg)
        except (ValueError, TypeError):
            return 0

@register.filter
def add(value, arg):
    """Add the argument to the value."""
    try:
        return int(value) + int(arg)
    except (ValueError, TypeError):
        try:
            return float(value) + float(arg)
        except (ValueError, TypeError):
            return value