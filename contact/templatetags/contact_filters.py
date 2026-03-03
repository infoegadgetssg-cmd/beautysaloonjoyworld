# contact/templatetags/contact_filters.py
from django import template

register = template.Library()

@register.filter
def multiply(value, arg):
    """Multiply the value by the argument"""
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        try:
            return int(value) * int(arg)
        except (ValueError, TypeError):
            return 0

@register.filter
def add(value, arg):
    """Add the argument to the value"""
    try:
        return float(value) + float(arg)
    except (ValueError, TypeError):
        try:
            return int(value) + int(arg)
        except (ValueError, TypeError):
            return value

@register.filter
def calculate_delay(value, increment=50):
    """Calculate delay for animations: (value + 4) * 50"""
    try:
        return (int(value) + 4) * increment
    except (ValueError, TypeError):
        return 0

@register.filter
def faq_delay(value):
    """Calculate FAQ delay: (value + 1) * 100"""
    try:
        return (int(value) + 1) * 100
    except (ValueError, TypeError):
        return 0