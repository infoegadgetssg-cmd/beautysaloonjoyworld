# shop/context_processors.py
from .cart import get_cart_for_request

def cart_context(request):
    """Add cart information to template context"""
    cart = get_cart_for_request(request)
    return {
        'cart_items_count': cart.total_items if cart else 0,
        'cart_subtotal': cart.subtotal if cart else 0,
    }