# shop/context_processors.py
from .cart import get_cart_for_request

def cart_context(request):
    """Add cart information to template context"""
    cart = get_cart_for_request(request)
    return {
        'cart': cart,
        'cart_items_count': cart.total_items if cart else 0,
        'cart_subtotal': cart.subtotal if cart else 0,
    }


def cart_data(request):
    cart = request.session.get("cart", {})
    total = 0
    count = 0

    for item in cart.values():
        total += item["price"] * item["quantity"]
        count += item["quantity"]

    return {
        "cart_items": cart,
        "cart_total": total,
        "cart_session_count": count,
    }


def cart_item_count(request):
    session_cart = request.session.get("cart", {})
    count = 0
    for item in session_cart.values():
        count += int(item.get("quantity", 0))
    return {"cart_item_count": count}
