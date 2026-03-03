# admin_dashboard/context_processors.py
from booking.models import Booking
from shop.models import Product
from contact.models import ContactMessage
from .models import DashboardNotification

def admin_dashboard_context(request):
    """Add common context variables to all admin dashboard pages"""
    # Only add context for admin users
    if request.user.is_authenticated and request.user.is_staff:
        return {
            'pending_bookings': Booking.objects.filter(status='pending').count(),
            'low_stock_products': Product.objects.filter(stock_quantity__lte=10).count(),
            'unread_notifications': DashboardNotification.objects.filter(is_read=False).count(),
        }
    return {}