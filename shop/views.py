# shop/views.py
from django.shortcuts import render, get_object_or_404, redirect
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Q, Avg, Count
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
from django.db.models import F
from decimal import Decimal
import json
import logging
import requests
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from .paystack import Paystack

from .models import Product, ProductCategory, ProductReview, Cart, CartItem, Order, OrderItem, Wishlist
from .forms import ProductReviewForm, CheckoutForm
from .cart import get_cart_for_request
from core.notifications import send_order_notifications

logger = logging.getLogger(__name__)


def _clear_session_cart(request):
    request.session["cart"] = {}
    request.session.modified = True


def _reduce_order_stock(order):
    for item in order.items.select_related('product').all():
        product = item.product
        new_stock = (product.stock_quantity or 0) - item.quantity
        product.stock_quantity = max(0, new_stock)
        product.save(update_fields=['stock_quantity'])


@login_required
@require_POST
def toggle_wishlist(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
    wishlist_item = Wishlist.objects.filter(user=request.user, product=product).first()

    if wishlist_item:
        wishlist_item.delete()
        payload = {
            "success": True,
            "action": "removed",
            "message": "Removed from favorites.",
        }
        if is_ajax:
            return JsonResponse(payload)
        messages.success(request, payload["message"])
        return redirect(request.META.get('HTTP_REFERER', 'user_dashboard:favorites'))

    Wishlist.objects.create(user=request.user, product=product)
    payload = {
        "success": True,
        "action": "added",
        "message": "Added to favorites.",
    }
    if is_ajax:
        return JsonResponse(payload)
    messages.success(request, payload["message"])
    return redirect(request.META.get('HTTP_REFERER', 'shop:shop'))

def shop_view(request):
    """Main shop page with product listings"""
    # Get filter parameters
    category_slug = request.GET.get('category', '')
    search_query = request.GET.get('q', '')
    min_price = request.GET.get('min_price', '')
    max_price = request.GET.get('max_price', '')
    sort_by = request.GET.get('sort', 'featured')
    page_number = request.GET.get('page', 1)
    
    # Start with all active products
    products = Product.objects.filter(is_active=True)
    
    # Apply filters
    if category_slug:
        try:
            category = get_object_or_404(ProductCategory, slug=category_slug, is_active=True)
            products = products.filter(category=category)
        except ProductCategory.DoesNotExist:
            pass
    
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(short_description__icontains=search_query) |
            Q(brand__icontains=search_query)
        )
    
    if min_price:
        try:
            products = products.filter(price__gte=Decimal(min_price))
        except (ValueError, Decimal.InvalidOperation):
            pass
    
    if max_price:
        try:
            products = products.filter(price__lte=Decimal(max_price))
        except (ValueError, Decimal.InvalidOperation):
            pass
    
    # Apply sorting
    if sort_by == 'price_low':
        products = products.order_by('price')
    elif sort_by == 'price_high':
        products = products.order_by('-price')
    elif sort_by == 'name_asc':
        products = products.order_by('name')
    elif sort_by == 'name_desc':
        products = products.order_by('-name')
    elif sort_by == 'newest':
        products = products.order_by('-created_at')
    elif sort_by == 'rating':
        products = products.annotate(avg_rating=Avg('reviews__rating')).order_by('-avg_rating')
    elif sort_by == 'bestsellers':
        products = products.filter(is_bestseller=True).order_by('-created_at')
    else:  # featured
        featured_products = products.filter(is_featured=True)
        if featured_products.exists():
            products = featured_products.order_by('-created_at')
        else:
            products = products.order_by('-created_at')
    
    # Get categories for sidebar
    categories = ProductCategory.objects.filter(is_active=True).order_by('name')
    
    # Pagination
    paginator = Paginator(products, 12)  # 12 products per page
    page_obj = paginator.get_page(page_number)
    
    # Get cart info
    cart = get_cart_for_request(request)
    cart_items_count = cart.total_items if cart else 0
    
    context = {
        'products': page_obj,
        'categories': categories,
        'current_category': category_slug,
        'search_query': search_query,
        'min_price': min_price,
        'max_price': max_price,
        'sort_by': sort_by,
        'cart_items_count': cart_items_count,
    }
    
    return render(request, 'shop/shop.html', context)


def filter_products_view(request):
    """AJAX endpoint for category-based product filtering."""
    category_id = request.GET.get('category_id')
    products = Product.objects.filter(is_active=True).select_related('category').order_by('-created_at')

    if category_id:
        try:
            products = products.filter(category_id=int(category_id))
        except (TypeError, ValueError):
            products = Product.objects.none()

    data = [
        {
            "id": product.id,
            "name": product.name,
            "slug": product.slug or "",
            "price": float(product.price),
            "description": (product.short_description or product.description or "")[:160],
            "category": product.category.name if product.category else "Uncategorized",
            "image": product.get_main_image_url(),
            "in_stock": product.in_stock,
            "is_new": product.is_new,
            "is_on_sale": product.is_on_sale,
            "discount_percentage": int(product.discount_percentage or 0),
            "compare_at_price": float(product.compare_at_price) if product.compare_at_price else None,
        }
        for product in products
    ]
    return JsonResponse({"products": data})


def product_detail_view(request, slug):
    """Product detail page"""
    product = get_object_or_404(Product, slug=slug, is_active=True)
    
    # Get related products
    related_products = Product.objects.filter(
        category=product.category,
        is_active=True
    ).exclude(id=product.id)[:4]
    
    # Get reviews
    reviews = product.reviews.filter(is_approved=True).order_by('-created_at')
    
    # Calculate average rating
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Get cart info
    cart = get_cart_for_request(request)
    in_cart = False
    if cart:
        in_cart = cart.items.filter(product=product).exists()
    
    if request.method == 'POST' and request.user.is_authenticated:
        review_form = ProductReviewForm(request.POST)
        if review_form.is_valid():
            # Check if user already reviewed this product
            existing_review = ProductReview.objects.filter(
                product=product,
                user=request.user
            ).first()
            
            if existing_review:
                messages.warning(request, "You've already reviewed this product.")
            else:
                review = review_form.save(commit=False)
                review.product = product
                review.user = request.user
                review.is_verified_purchase = OrderItem.objects.filter(
                    order__user=request.user,
                    product=product,
                    order__status='completed'
                ).exists()
                review.save()
                messages.success(request, "Thank you for your review!")
                return redirect('product_detail', slug=slug)
    else:
        review_form = ProductReviewForm()
    
    context = {
        'product': product,
        'related_products': related_products,
        'reviews': reviews,
        'avg_rating': avg_rating,
        'review_form': review_form,
        'in_cart': in_cart,
    }
    
    return render(request, 'shop/product_detail.html', context)


def add_to_cart_view(request):
    """Add product to cart (AJAX endpoint)"""
    if request.method == 'POST':
        try:
            is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
            if is_ajax:
                data = json.loads(request.body)
                product_id = data.get('product_id')
                quantity = int(data.get('quantity', 1))
            else:
                product_id = request.POST.get('product_id')
                quantity = int(request.POST.get('quantity', 1))
            
            product = get_object_or_404(Product, id=product_id, is_active=True)
            
            # Check stock
            if product.track_inventory and not product.allow_backorder:
                if product.stock_quantity < quantity:
                    return JsonResponse({
                        'success': False,
                        'message': f'Only {product.stock_quantity} items in stock.'
                    })
            
            cart = get_cart_for_request(request)
            
            # Add or update item in cart
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            
            # Update cart totals
            cart.save()

            # Keep session cart in sync for template-wide sidebar rendering.
            session_cart = request.session.get("cart", {})
            session_key = str(product.id)
            if session_key in session_cart:
                session_cart[session_key]["quantity"] += quantity
                session_cart[session_key]["cart_item_id"] = cart_item.id
            else:
                session_cart[session_key] = {
                    "name": product.name,
                    "price": float(product.price),
                    "quantity": quantity,
                    "image": product.get_main_image_url(),
                    "cart_item_id": cart_item.id,
                }
            request.session["cart"] = session_cart
            request.session.modified = True

            session_total = sum(item["price"] * item["quantity"] for item in session_cart.values())

            if is_ajax:
                return JsonResponse({
                    'success': True,
                    'message': 'Product added to cart!',
                    'cart_items_count': cart.total_items,
                    'cart_subtotal': float(cart.subtotal),
                    'cart_total': float(session_total),
                })

            messages.success(request, "Product added to cart!")
            return redirect('shop:cart_view')
            
        except (ValueError, KeyError) as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid request data.'
                })
            messages.error(request, "Invalid request data.")
            return redirect('shop:shop')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method.'
        })
    return redirect('shop:shop')


@login_required
def remove_from_cart_view(request, item_id):
    """Remove item from cart"""
    cart = get_cart_for_request(request)
    if cart:
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        product_id = cart_item.product.id
        cart_item.delete()
        cart.save()

        # Sync session cart for sidebar context
        session_cart = request.session.get("cart", {})
        session_cart.pop(str(product_id), None)
        request.session["cart"] = session_cart
        request.session.modified = True

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'message': 'Item removed from cart.',
                'cart_subtotal': float(cart.subtotal),
                'cart_items_count': cart.total_items,
            })
        messages.success(request, "Item removed from cart.")
    return redirect('shop:cart_view')


@login_required
def update_cart_quantity_view(request):
    """Update cart item quantity (AJAX endpoint)"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            item_id = data.get('item_id')
            quantity = int(data.get('quantity', 1))
            
            if quantity < 1:
                return JsonResponse({
                    'success': False,
                    'message': 'Quantity must be at least 1.'
                })
            
            cart = get_cart_for_request(request)
            if cart:
                cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
                
                # Check stock
                if cart_item.product.track_inventory and not cart_item.product.allow_backorder:
                    if cart_item.product.stock_quantity < quantity:
                        return JsonResponse({
                            'success': False,
                            'message': f'Only {cart_item.product.stock_quantity} items in stock.'
                        })
                
                cart_item.quantity = quantity
                cart_item.save()

                # Sync session cart for sidebar context
                session_cart = request.session.get("cart", {})
                session_key = str(cart_item.product.id)
                existing_item = session_cart.get(session_key, {})
                session_cart[session_key] = {
                    "name": existing_item.get("name", cart_item.product.name),
                    "price": existing_item.get("price", float(cart_item.product.price)),
                    "quantity": quantity,
                    "image": existing_item.get("image", cart_item.product.get_main_image_url()),
                    "cart_item_id": cart_item.id,
                }
                request.session["cart"] = session_cart
                request.session.modified = True
                
                return JsonResponse({
                    'success': True,
                    'message': 'Cart updated successfully.',
                    'item_total': float(cart_item.total_price),
                    'cart_subtotal': float(cart.subtotal),
                    'cart_items_count': cart.total_items
                })
            
        except (ValueError, KeyError) as e:
            return JsonResponse({
                'success': False,
                'message': 'Invalid request data.'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })


@login_required
def cart_view(request):
    """Cart page"""
    cart = get_cart_for_request(request)
    cart_items = cart.items.select_related('product', 'product__category').all() if cart else []

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'cart_total': cart.subtotal if cart else Decimal('0.00'),
    }
    
    return render(request, 'shop/cart.html', context)


@login_required
def checkout_view(request):
    """Checkout process with Paystack integration"""
    cart = get_cart_for_request(request)
    logger.info("Checkout started")
    
    if not cart or cart.items.count() == 0:
        messages.warning(request, "Your cart is empty.")
        return redirect('shop')
    
    # Check stock availability
    out_of_stock_items = []
    for item in cart.items.all():
        if item.product.track_inventory and not item.product.allow_backorder:
            if item.product.stock_quantity < item.quantity:
                out_of_stock_items.append(item.product.name)
    
    if out_of_stock_items:
        messages.error(request, f"Some items are out of stock: {', '.join(out_of_stock_items)}")
        return redirect('cart_view')
    
    if request.method == 'POST':
        form = CheckoutForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create order first
                    order = Order.objects.create(
                        user=request.user,
                        status='pending',
                        subtotal=cart.subtotal,
                        tax_amount=Decimal('0.00'),
                        shipping_cost=Decimal('0.00'),
                        total_amount=cart.subtotal,
                        shipping_address=form.cleaned_data['shipping_address'],
                        billing_address=form.cleaned_data.get('billing_address', ''),
                        payment_method=form.cleaned_data['payment_method'],
                        payment_status='pending',
                        notes=form.cleaned_data.get('notes', '')
                    )

                    # Create order items
                    for cart_item in cart.items.all():
                        OrderItem.objects.create(
                            order=order,
                            product=cart_item.product,
                            quantity=cart_item.quantity,
                            unit_price=cart_item.product.price,
                            total_price=cart_item.total_price
                        )

                    payment_method = form.cleaned_data['payment_method']
                    logger.info(f"Payment method: {payment_method}")

                    # Handle payment based on method
                    if payment_method == 'paystack':
                        return initiate_payment(request, order.id)

                    elif payment_method == 'paypal':
                        return initiate_paypal_payment(request, order.id)

                    elif payment_method == 'walk_in':
                        # Walk-in / pay at salon - no immediate payment
                        order.status = 'payment_pending'
                        order.payment_method = 'walk_in'
                        order.save()

                        _reduce_order_stock(order)

                        # Clear cart
                        cart.items.all().delete()
                        cart.delete()
                        CartItem.objects.filter(cart__user=request.user).delete()
                        request.session["last_order_id"] = order.id
                        _clear_session_cart(request)
                        send_order_notifications(order)

                        messages.success(request, "Order placed! Pay when you visit the salon.")
                        return redirect('shop:checkout_success', order_id=order.id)

            except Exception as e:
                messages.error(request, f"An error occurred: {str(e)}")
    else:
        form = CheckoutForm()
    
    context = {
        'cart': cart,
        'form': form,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
    }
    
    return render(request, 'shop/checkout.html', context)


@login_required
def order_success_view(request, order_id):
    """Order confirmation page"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    context = {
        'order': order,
    }
    
    return render(request, 'shop/order_success.html', context)


@login_required
def checkout_success_view(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, "shop/checkout_success.html", {"order": order})


def terms_view(request):
    return render(request, "legal/terms.html")


@login_required
def order_history_view(request):
    """User's order history"""
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    
    context = {
        'orders': orders,
    }
    
    return render(request, 'shop/order_history.html', context)


def search_suggestions_view(request):
    """AJAX endpoint for search suggestions"""
    query = request.GET.get('q', '')
    
    if query and len(query) >= 2:
        products = Product.objects.select_related('category').filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query),
            is_active=True
        )[:10]
        
        suggestions = [
            {
                'name': product.name,
                'url': product.get_absolute_url(),
                'image': product.get_main_image_url(),
                'price': float(product.price),
                'category': product.category.name
            }
            for product in products
        ]
        
        return JsonResponse({'suggestions': suggestions})
    
    return JsonResponse({'suggestions': []})



@login_required
def initiate_payment(request, order_id):
    """Initiate Paystack payment for an order"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if order.status not in ('pending', 'payment_pending'):
        messages.error(request, "This order cannot be paid for.")
        return redirect('shop:order_history')
    
    # Initialize Paystack transaction
    paystack = Paystack()
    
    callback_url = f"{request.scheme}://{request.get_host()}{reverse('shop:verify_payment', args=[order.id])}"
    
    metadata = {
        "order_id": order.id,
        "user_id": request.user.id,
        "cart_total": str(order.total_amount)
    }
    
    response = paystack.initialize_transaction(
        email=request.user.email,
        amount=order.total_amount,
        reference=order.paystack_reference,
        callback_url=callback_url,
        metadata=metadata
    )
    
    if response.get('status'):
        data = response['data']
        order.paystack_access_code = data['access_code']
        order.paystack_authorization_url = data['authorization_url']
        order.save()
        
        # Return JSON for AJAX or redirect
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'authorization_url': data['authorization_url']
            })
        else:
            # Redirect to Paystack checkout
            return redirect(data['authorization_url'])
    
    messages.error(request, "Failed to initialize payment. Please try again.")
    return redirect('shop:checkout')


@login_required
def initiate_paypal_payment(request, order_id):
    """Initiate PayPal payment for an order"""
    import requests as http_requests
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status not in ('pending', 'payment_pending'):
        messages.error(request, "This order cannot be paid for.")
        return redirect('shop:order_history')

    client_id = settings.PAYPAL_CLIENT_ID
    client_secret = settings.PAYPAL_CLIENT_SECRET
    base_url = settings.PAYPAL_BASE_URL

    # Get PayPal access token
    auth_response = http_requests.post(
        f'{base_url}/v1/oauth2/token',
        auth=(client_id, client_secret),
        data={'grant_type': 'client_credentials'},
        headers={'Accept': 'application/json'},
    )

    if auth_response.status_code != 200:
        messages.error(request, "Failed to connect to PayPal. Please try again.")
        return redirect('shop:checkout')

    access_token = auth_response.json()['access_token']

    # Create PayPal order
    callback_url = f"{request.scheme}://{request.get_host()}"
    paypal_order_data = {
        'intent': 'CAPTURE',
        'purchase_units': [{
            'reference_id': str(order.id),
            'amount': {
                'currency_code': settings.PAYPAL_CURRENCY,
                'value': str(order.total_amount),
            },
            'description': f'Joy World Beauty - Order #{order.id}',
        }],
        'application_context': {
            'return_url': f"{callback_url}{reverse('shop:paypal_success', args=[order.id])}",
            'cancel_url': f"{callback_url}{reverse('shop:paypal_cancel', args=[order.id])}",
            'brand_name': 'Joy World Home of Beauty',
            'user_action': 'PAY_NOW',
        }
    }

    create_response = http_requests.post(
        f'{base_url}/v2/checkout/orders',
        json=paypal_order_data,
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        },
    )

    if create_response.status_code in (200, 201):
        paypal_data = create_response.json()
        # Find the approval link
        approval_url = None
        for link in paypal_data.get('links', []):
            if link['rel'] == 'approve':
                approval_url = link['href']
                break

        if approval_url:
            order.paypal_order_id = paypal_data['id']
            order.save()
            return redirect(approval_url)

    messages.error(request, "Failed to create PayPal payment. Please try again.")
    return redirect('shop:checkout')


@login_required
def paypal_success(request, order_id):
    """Handle PayPal return after successful approval"""
    import requests as http_requests
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status == 'paid':
        return redirect('shop:checkout_success', order_id=order.id)

    paypal_order_id = order.paypal_order_id
    if not paypal_order_id:
        messages.error(request, "Invalid PayPal session.")
        return redirect('shop:checkout')

    client_id = settings.PAYPAL_CLIENT_ID
    client_secret = settings.PAYPAL_CLIENT_SECRET
    base_url = settings.PAYPAL_BASE_URL

    # Get access token
    auth_response = http_requests.post(
        f'{base_url}/v1/oauth2/token',
        auth=(client_id, client_secret),
        data={'grant_type': 'client_credentials'},
        headers={'Accept': 'application/json'},
    )

    if auth_response.status_code != 200:
        messages.error(request, "Failed to verify payment.")
        return redirect('shop:checkout')

    access_token = auth_response.json()['access_token']

    # Capture the payment
    capture_response = http_requests.post(
        f'{base_url}/v2/checkout/orders/{paypal_order_id}/capture',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {access_token}',
        },
    )

    if capture_response.status_code in (200, 201):
        capture_data = capture_response.json()
        if capture_data.get('status') == 'COMPLETED':
            with transaction.atomic():
                order.status = 'paid'
                order.payment_status = 'completed'
                order.save()

                _reduce_order_stock(order)

                # Clear cart
                cart = get_cart_for_request(request)
                if cart:
                    cart.items.all().delete()
                    cart.delete()
                CartItem.objects.filter(cart__user=request.user).delete()
                request.session["last_order_id"] = order.id
                _clear_session_cart(request)
                send_order_notifications(order)

            messages.success(request, "PayPal payment successful! Your order is being processed.")
            return redirect('shop:checkout_success', order_id=order.id)

    # Payment not completed
    order.status = 'failed'
    order.payment_status = 'failed'
    order.save()
    messages.error(request, "PayPal payment could not be completed. Please try again.")
    return redirect('shop:checkout')


@login_required
def paypal_cancel(request, order_id):
    """Handle PayPal cancellation"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.status = 'pending'
    order.payment_status = 'cancelled'
    order.save()
    messages.warning(request, "PayPal payment was cancelled. You can try again.")
    return redirect('shop:checkout')


@login_required
def verify_payment(request, order_id):
    """Verify Paystack payment after callback"""
    order = get_object_or_404(Order, id=order_id, user=request.user)

    if order.status == 'paid':
        return redirect('shop:checkout_success', order_id=order.id)
    
    # Get reference from query parameters
    reference = request.GET.get('reference', order.paystack_reference)
    
    if not reference:
        messages.error(request, "No payment reference provided.")
        return redirect('shop:order_history')
    
    # Verify payment with Paystack (server-side)
    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    response = requests.get(verify_url, headers=headers, timeout=30)

    if response.status_code != 200:
        messages.error(request, "Payment verification failed. Please try again.")
        return redirect('shop:checkout')

    verification = response.json()
    paystack_data = verification.get('data', {})
    paystack_status = paystack_data.get('status')
    paystack_amount = Decimal(str(paystack_data.get('amount', 0))) / Decimal('100')

    if paystack_amount != order.total_amount:
        return HttpResponseForbidden("Payment mismatch")

    if verification.get('status') and paystack_status == 'success':
        with transaction.atomic():
            # Payment successful
            order.status = 'paid'
            order.payment_status = 'completed'
            order.paystack_reference = reference
            order.save()

            _reduce_order_stock(order)

            # Clear cart if it exists
            cart = get_cart_for_request(request)
            if cart:
                cart.items.all().delete()
                cart.delete()
            CartItem.objects.filter(cart__user=request.user).delete()
            request.session["last_order_id"] = order.id
            _clear_session_cart(request)
            send_order_notifications(order)

        messages.success(request, "Payment successful! Your order is being processed.")
        return redirect('shop:checkout_success', order_id=order.id)
    else:
        # Payment failed
        order.status = 'failed'
        order.payment_status = 'failed'
        order.save()
        
        messages.error(request, "Payment failed. Please try again.")
        return redirect('shop:checkout')

@csrf_exempt
def paystack_webhook(request):
    """Handle Paystack webhook notifications [citation:4][citation:10]"""
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    # Verify webhook signature [citation:4]
    signature = request.headers.get('x-paystack-signature', '')
    payload = request.body
    
    paystack = Paystack()
    if not paystack.verify_webhook_signature(payload, signature):
        return JsonResponse({'error': 'Invalid signature'}, status=400)
    
    try:
        data = json.loads(payload)
        event = data.get('event')
        
        if event == 'charge.success':
            reference = data['data']['reference']

            try:
                with transaction.atomic():
                    order = Order.objects.get(paystack_reference=reference)
                    order.status = 'processing'
                    order.payment_status = 'completed'
                    order.save()

                # Send email notification
                send_order_confirmation_email(order)

            except Order.DoesNotExist:
                pass

        elif event == 'charge.failed':
            reference = data['data']['reference']

            try:
                with transaction.atomic():
                    order = Order.objects.get(paystack_reference=reference)
                    order.status = 'pending'
                    order.payment_status = 'failed'
                    order.save()

                # Send failure notification
                send_payment_failure_email(order)

            except Order.DoesNotExist:
                pass
        
        return JsonResponse({'status': 'success'})
    
    except Exception as e:
        print(f"Webhook error: {e}")
        return JsonResponse({'error': str(e)}, status=400)
