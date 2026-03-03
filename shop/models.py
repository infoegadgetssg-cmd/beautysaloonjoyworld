from django.db import models
from django.conf import settings
from django.core.validators import MinValueValidator, MaxValueValidator
from decimal import Decimal
import uuid
import secrets


class ProductCategory(models.Model):
    """Category for products"""
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True, max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='shop/categories/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Product Categories"
        ordering = ['name']

    def __str__(self):
        return self.name
    
    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)
    

class Product(models.Model):
    """Product model for shop"""
    category = models.ForeignKey(ProductCategory, on_delete=models.CASCADE, related_name='products', null=True, blank=True)
    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, null=True, blank=True)
    description = models.TextField(blank=True)
    short_description = models.CharField(max_length=255, blank=True)
    
    # Pricing
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    compare_at_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True, 
                                          validators=[MinValueValidator(0)])
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True,
                                    validators=[MinValueValidator(0)])
    
    # Inventory
    sku = models.CharField(max_length=100, unique=True, blank=True, null=True)
    stock_quantity = models.IntegerField(default=0)
    low_stock_threshold = models.IntegerField(default=5)
    track_inventory = models.BooleanField(default=True)
    allow_backorder = models.BooleanField(default=False)
    
    # Images
    main_image = models.ImageField(upload_to='shop/products/', blank=True, null=True)
    image_2 = models.ImageField(upload_to='shop/products/', blank=True, null=True)
    image_3 = models.ImageField(upload_to='shop/products/', blank=True, null=True)
    image_4 = models.ImageField(upload_to='shop/products/', blank=True, null=True)
    
    # Product details
    brand = models.CharField(max_length=100, blank=True)
    weight = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True, 
                                help_text="Weight in grams")
    dimensions = models.CharField(max_length=100, blank=True, 
                                 help_text="L x W x H in cm")
    
    # Flags
    is_featured = models.BooleanField(default=False)
    is_bestseller = models.BooleanField(default=False)
    is_new = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    
    # SEO
    meta_title = models.CharField(max_length=255, blank=True)
    meta_description = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True, null=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    @property
    def is_on_sale(self):
        """Check if product is on sale"""
        return bool(self.compare_at_price and self.compare_at_price > self.price)

    @property
    def discount_percentage(self):
        """Calculate discount percentage if on sale"""
        if self.is_on_sale:
            discount = ((self.compare_at_price - self.price) / self.compare_at_price) * 100
            return round(discount, 0)
        return 0

    @property
    def in_stock(self):
        """Check if product is in stock"""
        if not self.track_inventory:
            return True
        if self.allow_backorder:
            return True
        return self.stock_quantity > 0

    @property
    def low_stock(self):
        """Check if product is low in stock"""
        if not self.track_inventory:
            return False
        return self.stock_quantity <= self.low_stock_threshold

    def get_main_image_url(self):
        """Get main image URL or placeholder"""
        if self.main_image and hasattr(self.main_image, 'url'):
            return self.main_image.url
        return '/static/images/placeholder-product.jpg'
    
    def get_absolute_url(self):
        """Get the absolute URL for the product detail page"""
        from django.urls import reverse
        return reverse('product_detail', args=[self.slug])


class ProductReview(models.Model):
    """Product reviews"""
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='product_reviews')
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    title = models.CharField(max_length=200)
    comment = models.TextField()
    is_verified_purchase = models.BooleanField(default=False)
    helpful_count = models.IntegerField(default=0)
    not_helpful_count = models.IntegerField(default=0)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ['product', 'user']

    def __str__(self):
        return f"Review by {self.user.email} for {self.product.name}"

    @property
    def average_rating(self):
        """Calculate average rating for the product"""
        reviews = self.product.reviews.filter(is_approved=True)
        if reviews.exists():
            return reviews.aggregate(models.Avg('rating'))['rating__avg']
        return 0

class Order(models.Model):
    """Order model for shop purchases"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
        ('refunded', 'Refunded'),
        ('payment_pending', 'Payment Pending'),
    ]

    PAYMENT_METHODS = [
        ('paystack', 'Paystack (Card)'),
        ('paypal', 'PayPal'),
        ('walk_in', 'Pay at Salon (Walk-in)'),
    ]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    shipping_address = models.TextField(blank=True)
    billing_address = models.TextField(blank=True)
    payment_method = models.CharField(max_length=50, choices=PAYMENT_METHODS, blank=True)
    payment_status = models.CharField(max_length=20, default='pending')

    # Paystack specific fields
    paystack_reference = models.CharField(max_length=100, blank=True, unique=True)
    paystack_access_code = models.CharField(max_length=100, blank=True)
    paystack_authorization_url = models.URLField(blank=True)

    # PayPal specific fields
    paypal_order_id = models.CharField(max_length=100, blank=True)
    
    notes = models.TextField(blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Order #{self.id} - {self.user.email}"
    
    def generate_paystack_reference(self):
        """Generate unique reference for Paystack"""
        while True:
            ref = f"ORD_{secrets.token_hex(10)}"
            if not Order.objects.filter(paystack_reference=ref).exists():
                return ref
    
    def save(self, *args, **kwargs):
        # Generate Paystack reference if not exists
        if not self.paystack_reference and self.payment_method == 'paystack':
            self.paystack_reference = self.generate_paystack_reference()
        
        # Auto-calculate total if not set
        if not self.total_amount and self.subtotal:
            self.total_amount = self.subtotal + self.tax_amount + self.shipping_cost
        
        super().save(*args, **kwargs)


class OrderItem(models.Model):
    """Items in an order"""
    order = models.ForeignKey(Order, related_name='items', on_delete=models.CASCADE)
    product = models.ForeignKey('Product', on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    
    def save(self, *args, **kwargs):
        # Auto-calculate total price
        self.total_price = self.unit_price * self.quantity
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.quantity} x {self.product.name} (Order #{self.order.id})"
    

class Cart(models.Model):
    """Shopping cart model for authenticated users"""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='carts', null=True, blank=True)
    session_key = models.CharField(max_length=40, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        if self.user:
            return f"Cart for {self.user.email}"
        return f"Cart (Session: {self.session_key})"

    @property
    def total_items(self):
        """Total number of items in cart"""
        result = self.items.aggregate(total=models.Sum('quantity'))
        return result['total'] or 0

    @property
    def subtotal(self):
        """Calculate subtotal of all items"""
        from django.db.models import F, Sum
        result = self.items.aggregate(
            total=Sum(F('product__price') * F('quantity'))
        )
        return result['total'] or Decimal('0.00')

    @property
    def total(self):
        """Calculate total (subtotal + shipping + tax)"""
        # For now, just return subtotal
        # In a real app, you'd calculate shipping and tax
        return self.subtotal


class CartItem(models.Model):
    """Items in shopping cart"""
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1, validators=[MinValueValidator(1)])
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

    @property
    def total_price(self):
        """Calculate total price for this item"""
        return self.product.price * self.quantity