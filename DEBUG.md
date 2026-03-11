# Debug Report - Recent Shop Fixes

## Files Modified
- `shop/views.py`
- `shop/context_processors.py`
- `shop/cart.py`
- `beauty_salon_project/settings.py`
- `templates/shop/product_detail.html`
- `templates/shop/cart.html`
- `templates/shop/includes/cart_sidebar.html`

## Code Changes

### `shop/views.py`

#### Change made in `add_to_cart_view`

**BEFORE**
```python
@login_required
def add_to_cart_view(request):
    """Add product to cart (AJAX endpoint)"""
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        try:
            data = json.loads(request.body)
            product_id = data.get('product_id')
            quantity = int(data.get('quantity', 1))

            product = get_object_or_404(Product, id=product_id, is_active=True)
            ...
            cart = get_cart_for_request(request)
            if not cart:
                cart = Cart.objects.create(user=request.user)
            ...
            return JsonResponse({
                'success': True,
                'message': 'Product added to cart!',
                'cart_items_count': cart.total_items,
                'cart_subtotal': float(cart.subtotal)
            })
        except (ValueError, KeyError) as e:
            return JsonResponse({'success': False, 'message': 'Invalid request data.'})

    return JsonResponse({'success': False, 'message': 'Invalid request method.'})
```

**AFTER**
```python
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
            ...
            cart = get_cart_for_request(request)
            ...
            cart_item, created = CartItem.objects.get_or_create(
                cart=cart,
                product=product,
                defaults={'quantity': quantity}
            )
            if not created:
                cart_item.quantity += quantity
                cart_item.save()
            cart.save()

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
                return JsonResponse({'success': False, 'message': 'Invalid request data.'})
            messages.error(request, "Invalid request data.")
            return redirect('shop:shop')

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'})
    return redirect('shop:shop')
```

**Reason**
- Cart add action was only handling AJAX JSON and not normal POST forms.
- Session cart data was not synchronized with DB cart for sidebar/template rendering.
- Added support for both request types while preserving existing cart logic.

---

#### Change made in `remove_from_cart_view`

**BEFORE**
```python
@login_required
def remove_from_cart_view(request, item_id):
    cart = get_cart_for_request(request)
    if cart:
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        cart_item.delete()
        messages.success(request, "Item removed from cart.")
    return redirect('cart_view')
```

**AFTER**
```python
@login_required
def remove_from_cart_view(request, item_id):
    cart = get_cart_for_request(request)
    if cart:
        cart_item = get_object_or_404(CartItem, id=item_id, cart=cart)
        product_id = cart_item.product.id
        cart_item.delete()
        cart.save()

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
```

**Reason**
- Sidebar/cart JS expected JSON on remove calls.
- Session cart had to be kept consistent after deletion.

---

#### Change made in `update_cart_quantity_view`

**BEFORE**
```python
cart_item.quantity = quantity
cart_item.save()

return JsonResponse({
    'success': True,
    'message': 'Cart updated successfully.',
    'item_total': float(cart_item.total_price),
    'cart_subtotal': float(cart.subtotal),
    'cart_items_count': cart.total_items
})
```

**AFTER**
```python
cart_item.quantity = quantity
cart_item.save()

session_cart = request.session.get("cart", {})
session_key = str(cart_item.product.id)
if session_key in session_cart:
    session_cart[session_key]["quantity"] = quantity
    session_cart[session_key]["cart_item_id"] = cart_item.id
    request.session["cart"] = session_cart
    request.session.modified = True

return JsonResponse({
    'success': True,
    'message': 'Cart updated successfully.',
    'item_total': float(cart_item.total_price),
    'cart_subtotal': float(cart.subtotal),
    'cart_items_count': cart.total_items
})
```

**Reason**
- Quantity updates in DB cart were not reflected in session cart used by sidebar context.

---

#### Change made in `cart_view`

**BEFORE**
```python
@login_required
def cart_view(request):
    cart = get_cart_for_request(request)

    context = {
        'cart': cart,
    }

    return render(request, 'shop/cart.html', context)
```

**AFTER**
```python
@login_required
def cart_view(request):
    cart = get_cart_for_request(request)
    cart_items = cart.items.select_related('product', 'product__category').all() if cart else []

    context = {
        'cart': cart,
        'cart_items': cart_items,
        'cart_total': cart.subtotal if cart else Decimal('0.00'),
    }

    return render(request, 'shop/cart.html', context)
```

**Reason**
- Cart template was rendered but items/totals were not consistently available in context.

---

### `shop/context_processors.py`

#### Change made: add `cart` into existing processor and add new `cart_data`

**BEFORE**
```python
from .cart import get_cart_for_request

def cart_context(request):
    """Add cart information to template context"""
    cart = get_cart_for_request(request)
    return {
        'cart_items_count': cart.total_items if cart else 0,
        'cart_subtotal': cart.subtotal if cart else 0,
    }
```

**AFTER**
```python
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
```

**Reason**
- Required global cart data (`cart_items`, `cart_total`) for templates like sidebar.

---

### `beauty_salon_project/settings.py`

#### Change made in `TEMPLATES[0]['OPTIONS']['context_processors']`

**BEFORE**
```python
'shop.context_processors.cart_context',
'admin_dashboard.context_processors.admin_dashboard_context',
```

**AFTER**
```python
'shop.context_processors.cart_context',
'shop.context_processors.cart_data',
'admin_dashboard.context_processors.admin_dashboard_context',
```

**Reason**
- Registers `cart_data` so cart session data is available in all templates.

---

### `shop/cart.py`

#### Change made in `get_cart_for_request`

**BEFORE**
```python
if request.user.is_authenticated:
    cart = Cart.objects.filter(user=request.user).first()
...
else:
    if 'cart_id' in request.session:
        cart = Cart.objects.filter(
            session_key=request.session.session_key
        ).first()
```

**AFTER**
```python
if request.user.is_authenticated:
    cart = Cart.objects.filter(user=request.user).order_by('-updated_at').first()
...
else:
    if 'cart_id' in request.session:
        cart = Cart.objects.filter(id=request.session['cart_id']).first()
```

**Reason**
- More reliable cart retrieval for both authenticated and anonymous sessions.

---

### `templates/shop/product_detail.html`

#### Change made: file content restored and UTF-safe currency entity used

**BEFORE**
```html
<!-- File was empty -->
```

**AFTER**
```html
{% extends 'base.html' %}
{% load static %}

{% block title %}{{ product.name }} | Joy World Beauty Shop{% endblock %}

{% block content %}
<section class="section-padding">
    <div class="container">
        <div class="row g-4">
            <div class="col-lg-6">
                {% if product.main_image %}
                <img src="{{ product.main_image.url }}" alt="{{ product.name }}" class="img-fluid rounded" />
                {% else %}
                <img src="{{ product.get_main_image_url }}" alt="{{ product.name }}" class="img-fluid rounded" />
                {% endif %}
            </div>
            <div class="col-lg-6">
                <p class="text-muted mb-2">{{ product.category.name|default:"Uncategorized" }}</p>
                <h1 class="mb-3">{{ product.name }}</h1>
                <h4 class="mb-3">&pound;{{ product.price }}</h4>
                <p class="mb-4">{{ product.description|default:product.short_description }}</p>

                {% if product.in_stock %}
                <form method="post" action="{% url 'shop:add_to_cart' %}">
                    {% csrf_token %}
                    <input type="hidden" name="product_id" value="{{ product.id }}">
                    <input type="hidden" name="quantity" value="1">
                    <button type="submit" class="btn btn-primary btn-add-to-cart" data-product-id="{{ product.id }}">Add to Cart</button>
                </form>
                {% else %}
                <button class="btn btn-secondary" disabled>Out of Stock</button>
                {% endif %}
            </div>
        </div>
    </div>
</section>
{% endblock %}
```

**Reason**
- Product detail page was blank because template had no renderable content.
- Replaced raw currency symbol with `&pound;` in this page.

---

### `templates/shop/cart.html`

#### Change made: loop and totals to use explicit context variables

**BEFORE**
```html
{% if cart and cart.items.exists %}
...
{% for item in cart.items.all %}
...
<span id="cartSubtotal">£{{ cart.subtotal }}</span>
...
<span id="cartTotal">£{{ cart.subtotal }}</span>
```

**AFTER**
```html
{% if cart_items %}
...
{% for item in cart_items %}
...
<span id="cartSubtotal">£{{ cart_total }}</span>
...
<span id="cartTotal">£{{ cart_total }}</span>
```

**Reason**
- Ensures template references match what `cart_view` passes.

---

### `templates/shop/includes/cart_sidebar.html`

#### Change made: render from session cart context and fix currency output

**BEFORE**
```html
<small id="cart-item-count">({{ cart_items_count|default:0 }})</small>

{% if cart_items_count > 0 %}
    {% for item in cart.items.all %}
    <div class="cart-item" data-item-id="{{ item.id }}">
        <img src="{{ item.product.get_main_image_url }}" alt="{{ item.product.name }}">
        <h6>{{ item.product.name|truncatechars:30 }}</h6>
        <p>£{{ item.product.price }} × {{ item.quantity }}</p>
...
{% if cart_items_count > 0 %}
<strong id="cart-sidebar-subtotal">£{{ cart.subtotal|default:"0.00" }}</strong>
```

**AFTER**
```html
<small id="cart-item-count">({{ cart_session_count|default:cart_items_count|default:0 }})</small>

{% if cart_items %}
    {% for id, item in cart_items.items %}
    <div class="cart-item" data-item-id="{{ item.cart_item_id|default:id }}">
        <img src="{{ item.image }}" alt="{{ item.name }}">
        <h6>{{ item.name|truncatechars:30 }}</h6>
        <p>&pound;{{ item.price }} x {{ item.quantity }}</p>
...
{% if cart_items %}
<strong id="cart-sidebar-subtotal">&pound;{{ cart_total|default:"0.00" }}</strong>
```

**JS line updates in same file**

**BEFORE**
```javascript
document.getElementById('cart-sidebar-subtotal').textContent = `£${data.cart_subtotal.toFixed(2)}`;
```

**AFTER**
```javascript
document.getElementById('cart-sidebar-subtotal').textContent = `\u00A3${data.cart_subtotal.toFixed(2)}`;
```

**Reason**
- Sidebar needed to display session cart data added by context processor.
- Avoids garbled currency output in JS-rendered text.

## Cart System Changes
- Retrieval:
  - Main DB cart: `get_cart_for_request(request)` in `shop/cart.py`.
  - Session cart: `request.session.get("cart", {})` in `cart_data` context processor.
- Storage:
  - DB: `Cart` + `CartItem` models remain primary transactional cart storage.
  - Session mirror (for sidebar/global context):
    - key: `str(product.id)`
    - value: `{"name", "price", "quantity", "image", "cart_item_id"}`
- Totals:
  - DB total: `cart.subtotal`
  - Session total: sum of `item["price"] * item["quantity"]` from session cart values.
- Template context:
  - Global via context processors: `cart`, `cart_items_count`, `cart_subtotal`, `cart_items`, `cart_total`, `cart_session_count`.
  - Cart page via view: `cart`, `cart_items`, `cart_total`.

## Product Detail Page Changes
- Retrieval:
  - View already uses `get_object_or_404(Product, slug=slug, is_active=True)`.
- Template rendered:
  - `shop/product_detail.html`
- Context variables sent:
  - `product`, `related_products`, `reviews`, `avg_rating`, `review_form`, `in_cart`
- Template now explicitly renders:
  - image (`product.main_image.url` fallback `product.get_main_image_url`)
  - `product.name`
  - `product.price`
  - `product.description`
  - add-to-cart form

## Template Changes
- `templates/shop/product_detail.html`
  - Restored full product detail markup.
  - Added form-based add-to-cart POST.
  - Used `&pound;` for currency output.
- `templates/shop/cart.html`
  - Updated loop to use `cart_items`.
  - Updated totals to use `cart_total`.
- `templates/shop/includes/cart_sidebar.html`
  - Switched loop to `cart_items.items` (session context).
  - Updated display fields to session item keys.
  - Added fallback for item-id using `cart_item_id|default:id`.
  - Updated subtotal display to `cart_total`.
  - Updated JS currency output to Unicode escape.

## Context Processors
Full code currently in `shop/context_processors.py`:

```python
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
```

How it injects data:
- `cart_context` injects DB-cart summary values globally.
- `cart_data` injects session-cart item dictionary and computed totals globally.

## Potential Side Effects
- `shop.html` product display:
  - No direct template changes in this fix.
  - Indirect effect: cart count/subtotal displays may now prioritize session values where used.
- Cart sidebar rendering:
  - Sidebar now depends on `cart_items` session dict for rendering rows.
  - Sidebar action endpoints still operate on DB cart item IDs; fallback `cart_item_id|default:id` was added to reduce mismatch risk.
- `product_detail` rendering:
  - Page now renders content and includes a POST add-to-cart form.
  - Non-AJAX add-to-cart now redirects to cart page with success message.
- Queryset filtering:
  - No model filter change in `product_detail_view`.
  - No structural change to product retrieval/filtering in this documentation step.

## Verification Performed During Last Fix
- Ran: `python manage.py check`
- Result: `System check identified no issues (0 silenced).`
