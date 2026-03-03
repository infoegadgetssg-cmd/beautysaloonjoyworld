# shop/cart.py
from .models import Cart, CartItem
from django.utils.crypto import get_random_string

def get_cart_for_request(request):
    """Get or create cart for current user/session"""
    cart = None
    
    if request.user.is_authenticated:
        # Try to get existing cart for user
        cart = Cart.objects.filter(user=request.user).first()
        
        # If user has no cart but has session cart, merge them
        if not cart and 'cart_id' in request.session:
            session_cart = Cart.objects.filter(
                session_key=request.session.session_key
            ).first()
            if session_cart:
                session_cart.user = request.user
                session_cart.save()
                cart = session_cart
                del request.session['cart_id']
    else:
        # For anonymous users, use session
        if 'cart_id' in request.session:
            cart = Cart.objects.filter(
                session_key=request.session.session_key
            ).first()
    
    # Create new cart if none exists
    if not cart:
        if request.user.is_authenticated:
            cart = Cart.objects.create(user=request.user)
        else:
            # Create cart for anonymous user
            cart = Cart.objects.create(session_key=request.session.session_key)
            request.session['cart_id'] = cart.id
    
    return cart


def merge_carts(user, session_key):
    """Merge session cart into user cart after login"""
    if session_key:
        session_cart = Cart.objects.filter(session_key=session_key).first()
        if session_cart:
            user_cart = Cart.objects.filter(user=user).first()
            
            if user_cart:
                # Merge session cart items into user cart
                for session_item in session_cart.items.all():
                    user_item = user_cart.items.filter(
                        product=session_item.product
                    ).first()
                    
                    if user_item:
                        user_item.quantity += session_item.quantity
                        user_item.save()
                    else:
                        session_item.cart = user_cart
                        session_item.save()
                
                # Delete session cart
                session_cart.delete()
            else:
                # Assign session cart to user
                session_cart.user = user
                session_cart.session_key = None
                session_cart.save()