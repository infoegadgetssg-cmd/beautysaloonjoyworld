# admin_dashboard/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Count, Sum, Avg, Q
from django.db.models.functions import Coalesce
from django.utils import timezone
from django.utils.timesince import timesince
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.utils.text import slugify
from django.urls import reverse

from accounts.models import CustomUser
from booking.models import Booking
from services.models import Stylist
from services.models import Service, ServiceCategory 
from shop.models import Product, ProductCategory, Order
from contact.models import ContactMessage
from user_dashboard.models import UserNotification
from .models import DashboardNotification, RecentActivity, AdminDashboard
from .forms import DashboardSettingsForm, ServiceForm, ProductForm
from gallery.models import GalleryImage, GalleryCategory
import json

DEFAULT_SERVICE_CATEGORIES = [
    ("Hair", "hair"),
    ("Nails", "nails"),
    ("Facial", "facial"),
    ("Massage", "massage"),
    ("Spa", "spa"),
]


def _ensure_default_service_categories():
    if not ServiceCategory.objects.exists():
        ServiceCategory.objects.bulk_create([
            ServiceCategory(name=name, slug=slug, is_active=True)
            for name, slug in DEFAULT_SERVICE_CATEGORIES
        ])


def _ensure_uncategorized_gallery_category():
    category, _ = GalleryCategory.objects.get_or_create(
        slug='uncategorized',
        defaults={
            'name': 'Uncategorized',
            'description': 'Fallback category for uncategorized images',
            'is_active': True,
            'order': 999,
        }
    )

    # Backward-compatibility for legacy records that may have null category.
    GalleryImage.objects.filter(category__isnull=True).update(category=category)
    return category



def admin_required(view_func):
    """Decorator to check if user is staff/admin"""
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            messages.error(request, 'Please login to access admin dashboard.')
            return redirect('account_login')
        if not request.user.is_staff:
            messages.error(request, 'Access denied. Admin privileges required.')
            return redirect('user_dashboard:dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view

@admin_required
def dashboard_index(request):
    """Main admin dashboard view"""
    today = timezone.now().date()
    thirty_days_ago = timezone.now() - timedelta(days=30)
    
    # Booking statistics
    total_bookings = Booking.objects.count()
    today_bookings = Booking.objects.filter(date=today).count()
    pending_bookings = Booking.objects.filter(status='pending').count()
    
    # Revenue statistics (orders only)
    total_revenue = Order.objects.filter(
        status__in=['paid', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    monthly_revenue = Order.objects.filter(
        status__in=['paid', 'completed'],
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Customer statistics
    total_customers = CustomUser.objects.filter(is_staff=False).count()
    new_customers = CustomUser.objects.filter(
        date_joined__gte=thirty_days_ago,
        is_staff=False
    ).count()
    
    # Product statistics
    total_products = Product.objects.count()
    low_stock_products = Product.objects.filter(stock_quantity__lte=10).count()
    
    # Recent bookings
    recent_bookings = Booking.objects.select_related(
        'user', 'service'
    ).order_by('-created_at')[:10]
    
    # Recent activities
    recent_activities = RecentActivity.objects.select_related('user').order_by('-created_at')[:10]
    
    # Unread notifications
    unread_notifications = DashboardNotification.objects.filter(is_read=False).count()
    
    # Popular services
    popular_services = Service.objects.select_related('category').annotate(
        booking_count=Count('booking')
    ).order_by('-booking_count')[:5]
    
    context = {
        'total_bookings': total_bookings,
        'today_bookings': today_bookings,
        'pending_bookings': pending_bookings,
        'total_revenue': f"\u00a3{total_revenue:.2f}",
        'monthly_revenue': f"\u00a3{monthly_revenue:.2f}",
        'total_customers': total_customers,
        'new_customers': new_customers,
        'total_products': total_products,
        'low_stock_products': low_stock_products,
        'recent_bookings': recent_bookings,
        'recent_activities': recent_activities,
        'unread_notifications': unread_notifications,
        'popular_services': popular_services,
        'today': today,
    }
    
    return render(request, 'admin_dashboard/admin_index.html', context)

# Keep all the other management views as they were but update decorator
@admin_required
def bookings_management(request):
    """Manage bookings"""
    overdue_bookings = Booking.objects.filter(
        status=Booking.STATUS_AWAITING_PAYMENT,
        deposit_paid=False,
        payment_deadline__isnull=False,
        payment_deadline__lt=timezone.now()
    )
    for booking in overdue_bookings:
        booking.status = Booking.STATUS_CANCELLED
        booking.save()
        UserNotification.objects.create(
            user=booking.user,
            title='Booking Cancelled',
            message='Your booking was cancelled because the required deposit was not paid within 48 hours.',
            notification_type='booking_update'
        )

    status_filter = request.GET.get('status', 'all')
    date_filter = request.GET.get('date', '')
    
    bookings = Booking.objects.select_related('user', 'service')
    
    if status_filter != 'all':
        bookings = bookings.filter(status=status_filter)
    
    if date_filter:
        bookings = bookings.filter(date=date_filter)
    
    # Pagination
    paginator = Paginator(bookings.order_by('-date', '-time'), 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'bookings': page_obj,
        'status_filter': status_filter,
        'date_filter': date_filter,
        'total_bookings': bookings.count(),
    }
    
    return render(request, 'admin_dashboard/bookings.html', context)

@admin_required
def customers_management(request):
    """Manage customers"""
    search_query = request.GET.get('search', '')

    customers = CustomUser.objects.filter(is_staff=False).distinct()

    if search_query:
        customers = customers.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    customers_with_stats = []
    for customer in customers:
        order_count = Order.objects.filter(user=customer).count()
        total_spent = Order.objects.filter(
            user=customer,
            status__in=['paid', 'completed']
        ).aggregate(total=Sum('total_amount'))['total'] or 0

        if total_spent >= 1000:
            tier = "Platinum"
        elif total_spent >= 500:
            tier = "Gold"
        elif total_spent >= 200:
            tier = "Silver"
        else:
            tier = "Bronze"

        customers_with_stats.append({
            'customer': customer,
            'booking_count': order_count,
            'total_spent': total_spent,
            'tier': tier,
        })

    context = {
        'customers_with_stats': customers_with_stats,
        'search_query': search_query,
        'total_customers': len(customers_with_stats),
    }

    return render(request, 'admin_dashboard/customers.html', context)


@admin_required
def customer_detail_view(request, user_id):
    """Customer detail page."""
    customer = get_object_or_404(CustomUser, id=user_id, is_staff=False)

    orders = Order.objects.filter(user=customer).prefetch_related('items__product').order_by('-created_at')
    paid_orders = orders.filter(status__in=['paid', 'completed'])
    bookings = Booking.objects.filter(user=customer).select_related('service').order_by('-date', '-time')

    total_spent = paid_orders.aggregate(total=Sum('total_amount'))['total'] or 0
    total_orders = orders.count()
    total_bookings = bookings.count()
    loyalty_points = int(total_spent * 10)

    context = {
        'customer': customer,
        'orders': orders[:5],
        'recent_bookings': bookings[:5],
        'total_orders': total_orders,
        'total_bookings': total_bookings,
        'total_spent': total_spent,
        'loyalty_points': loyalty_points,
    }
    return render(request, 'admin_dashboard/customer_detail.html', context)

@admin_required
def services_management(request):
    """Manage services"""
    _ensure_default_service_categories()
    services = Service.objects.all().order_by('-created_at')
    categories = ServiceCategory.objects.all().order_by('display_order', 'name')
    is_ajax = request.headers.get('x-requested-with') == 'XMLHttpRequest'
    
    if request.method == 'POST':
        form = ServiceForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                service = form.save()
                
                # Create activity log
                RecentActivity.objects.create(
                    user=request.user,
                    activity_type='service_added',
                    description=f'Added new service: {service.name}',
                    related_id=str(service.id),
                    related_model='service',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                if is_ajax:
                    return JsonResponse({
                        'success': True,
                        'message': 'Service added successfully.'
                    })

                messages.success(request, 'Service added successfully!')
                return redirect('admin_dashboard:services')
            except Exception as e:
                if is_ajax:
                    return JsonResponse({
                        'success': False,
                        'error': str(e)
                    }, status=500)
                messages.error(request, f'Error saving service: {str(e)}')
        else:
            if is_ajax:
                error_messages = []
                for field, errors in form.errors.items():
                    for error in errors:
                        error_messages.append(f"{field}: {error}")
                return JsonResponse({
                    'success': False,
                    'message': '; '.join(error_messages) or 'Invalid service data.',
                    'errors': form.errors
                }, status=400)
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ServiceForm()
    
    context = {
        'services': services,
        'categories': categories,
        'form': form,
        'total_services': services.count(),
    }
    
    return render(request, 'admin_dashboard/services.html', context)


@admin_required
def create_service_category(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    name = (request.POST.get('name') or '').strip()
    display_order = request.POST.get('display_order') or 0
    is_active = request.POST.get('is_active') in ('on', 'true', '1')

    if not name:
        return JsonResponse({'success': False, 'message': 'Category name is required.'}, status=400)

    slug_base = slugify(name) or 'category'
    slug = slug_base
    counter = 1
    while ServiceCategory.objects.filter(slug=slug).exists():
        slug = f"{slug_base}-{counter}"
        counter += 1

    category = ServiceCategory.objects.create(
        name=name,
        slug=slug,
        display_order=int(display_order),
        is_active=is_active
    )
    return JsonResponse({
        'success': True,
        'message': 'Category created successfully.',
        'category': {'id': category.id, 'name': category.name, 'display_order': category.display_order, 'is_active': category.is_active}
    })


@admin_required
def update_service_category(request, category_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    category = get_object_or_404(ServiceCategory, id=category_id)
    name = (request.POST.get('name') or '').strip()
    display_order = request.POST.get('display_order') or category.display_order
    is_active = request.POST.get('is_active') in ('on', 'true', '1')

    if not name:
        return JsonResponse({'success': False, 'message': 'Category name is required.'}, status=400)

    category.name = name
    category.display_order = int(display_order)
    category.is_active = is_active
    category.save()

    return JsonResponse({'success': True, 'message': 'Category updated successfully.'})


@admin_required
def delete_service_category(request, category_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    category = get_object_or_404(ServiceCategory, id=category_id)
    if category.services.exists():
        return JsonResponse({'success': False, 'message': 'Cannot delete a category with linked services.'}, status=400)

    category.delete()
    return JsonResponse({'success': True, 'message': 'Category deleted successfully.'})


@admin_required
def products_management(request):
    """Manage products"""
    products = Product.objects.annotate(
        sold_count=Coalesce(
            Sum(
                'orderitem__quantity',
                filter=Q(orderitem__order__status__in=['paid', 'completed'])
            ),
            0
        )
    )
    categories = ProductCategory.objects.filter(is_active=True)
    low_stock_products = Product.objects.filter(
        stock_quantity__lte=10,
        track_inventory=True
    )
    
    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save()
            
            # Create activity log
            RecentActivity.objects.create(
                user=request.user,
                activity_type='product_added',
                description=f'Added new product: {product.name}',
                related_id=str(product.id),
                related_model='product',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            messages.success(request, 'Product added successfully!')
            return redirect('admin_dashboard:products')
    else:
        form = ProductForm()
    
    context = {
        'products': products,
        'categories': categories,
        'form': form,
        'low_stock_products': low_stock_products,
        'total_products': products.count(),
        'low_stock_count': low_stock_products.count(),
    }
    
    return render(request, 'admin_dashboard/products.html', context)

@admin_required
def get_product_data(request, product_id):
    """Get product data for editing via AJAX"""
    try:
        product = Product.objects.get(id=product_id)
        data = {
            'success': True,
            'product': {
                'id': product.id,
                'name': product.name,
                'description': product.description,
                'short_description': product.short_description,
                'category_id': product.category.id if product.category else None,
                'price': float(product.price),
                'compare_at_price': float(product.compare_at_price) if product.compare_at_price else None,
                'stock_quantity': product.stock_quantity,
                'sku': product.sku,
                'brand': product.brand,
                'is_featured': product.is_featured,
                'is_bestseller': product.is_bestseller,
                'is_active': product.is_active,
                'image_url': product.main_image.url if product.main_image else None,
            }
        }
    except Product.DoesNotExist:
        data = {'success': False, 'message': 'Product not found'}
    
    return JsonResponse(data)

@admin_required
def update_product(request, product_id):
    """Update product via AJAX"""
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id)
            form = ProductForm(request.POST, request.FILES, instance=product)
            
            if form.is_valid():
                product = form.save()
                
                # Log activity
                RecentActivity.objects.create(
                    user=request.user,
                    activity_type='product_updated',
                    description=f'Updated product: {product.name}',
                    related_id=str(product.id),
                    related_model='product',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Product updated successfully.'
                })
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Product not found.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

@admin_required
def delete_product(request, product_id):
    """Delete product via AJAX"""
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id)
            product_name = product.name
            product.delete()
            
            # Log activity
            RecentActivity.objects.create(
                user=request.user,
                activity_type='product_updated',
                description=f'Deleted product: {product_name}',
                related_model='product',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'message': 'Product deleted successfully.'
                })
            messages.success(request, 'Product deleted successfully.')
            return redirect('admin_dashboard:products')
        except Product.DoesNotExist:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': False,
                    'message': 'Product not found.'
                })
            messages.error(request, 'Product not found.')
            return redirect('admin_dashboard:products')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': False,
            'message': 'Invalid request method.'
        })
    messages.error(request, 'Invalid request method.')
    return redirect('admin_dashboard:products')

@admin_required
def update_product_stock(request, product_id):
    """Update product stock via AJAX"""
    if request.method == 'POST':
        try:
            product = Product.objects.get(id=product_id)
            action = request.POST.get('action')
            amount = int(request.POST.get('amount', 0))
            
            if action == 'set':
                product.stock_quantity = amount
            elif action == 'add':
                product.stock_quantity += amount
            elif action == 'remove':
                product.stock_quantity = max(0, product.stock_quantity - amount)
            
            product.save()
            
            return JsonResponse({
                'success': True,
                'message': f'Stock updated to {product.stock_quantity}',
                'new_stock': product.stock_quantity
            })
        except Product.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Product not found.'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })


@admin_required
def messages_management(request):
    """Manage contact messages"""
    messages_list = ContactMessage.objects.order_by('-created_at')
    unread_count = ContactMessage.objects.filter(is_read=False).count()

    context = {
        'messages': messages_list,
        'unread_count': unread_count,
        'total_messages': messages_list.count(),
    }

    return render(request, 'admin_dashboard/messages.html', context)


@admin_required
def messages_api(request):
    """Return filtered messages for AJAX"""
    filter_param = request.GET.get('filter')
    queryset = ContactMessage.objects.order_by('-created_at')

    if filter_param == 'unread':
        queryset = queryset.filter(is_read=False)
    elif filter_param == 'urgent':
        queryset = queryset.filter(status='urgent')

    messages_data = []
    for message in queryset:
        messages_data.append({
            'id': message.id,
            'name': message.name,
            'email': message.email,
            'subject': message.subject or 'No Subject',
            'message': message.message,
            'is_read': message.is_read,
            'is_urgent': message.status == 'urgent',
            'status': message.status,
            'created_at': message.created_at.strftime('%b %d, %Y %I:%M %p'),
            'timesince': timesince(message.created_at) + ' ago',
        })

    return JsonResponse({
        'messages': messages_data,
        'total': queryset.count(),
        'unread': ContactMessage.objects.filter(is_read=False).count(),
    })

# admin_dashboard/views.py - Update analytics_view function
# admin_dashboard/views.py - Update analytics_view function
@admin_required
def analytics_view(request):
    """Analytics dashboard with real data"""
    from django.db.models import Count, Sum, Q
    from django.utils import timezone
    from datetime import timedelta
    import json
    
    thirty_days_ago = timezone.now() - timedelta(days=30)
    ninety_days_ago = timezone.now() - timedelta(days=90)
    
    # ============ REVENUE METRICS ============
    # Total revenue
    total_revenue = Order.objects.filter(
        status__in=['paid', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Monthly revenue (last 30 days)
    monthly_revenue = Order.objects.filter(
        status__in=['paid', 'completed'],
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Previous month revenue for comparison
    previous_month_start = timezone.now() - timedelta(days=60)
    previous_month_end = timezone.now() - timedelta(days=30)
    previous_month_revenue = Order.objects.filter(
        status__in=['paid', 'completed'],
        created_at__range=[previous_month_start, previous_month_end]
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Revenue growth percentage
    revenue_growth = 0
    if previous_month_revenue > 0:
        revenue_growth = ((monthly_revenue - previous_month_revenue) / previous_month_revenue) * 100
    
    # ============ DAILY BOOKINGS (Last 30 days) ============
    daily_bookings_labels = []
    daily_bookings_data = []
    daily_revenue_data = []
    
    for i in range(29, -1, -1):
        day = timezone.now() - timedelta(days=i)
        day_start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day.replace(hour=23, minute=59, second=59, microsecond=999999)
        
        # Bookings count
        count = Booking.objects.filter(
            created_at__range=[day_start, day_end]
        ).count()
        
        # Revenue
        revenue = Order.objects.filter(
            status__in=['paid', 'completed'],
            created_at__range=[day_start, day_end]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        daily_bookings_labels.append(day.strftime('%b %d'))
        daily_bookings_data.append(count)
        daily_revenue_data.append(float(revenue))
    
    # ============ MONTHLY REVENUE (Last 6 months) ============
    monthly_labels = []
    monthly_data = []
    
    for i in range(5, -1, -1):
        month_start = (timezone.now() - timedelta(days=30*i)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        revenue = Order.objects.filter(
            status__in=['paid', 'completed'],
            created_at__range=[month_start, month_end]
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        monthly_labels.append(month_start.strftime('%b %Y'))
        monthly_data.append(float(revenue))
    
    # ============ SERVICE CATEGORIES ============
    category_labels = []
    category_data = []
    
    # Get booking counts by service category
    service_categories = ServiceCategory.objects.filter(is_active=True).annotate(
        booking_count=Count('services__booking')
    ).order_by('-booking_count')[:6]
    
    for category in service_categories:
        if category.booking_count > 0:
            category_labels.append(category.name)
            category_data.append(category.booking_count)
    
    # If no data, provide fallback
    if not category_labels:
        category_labels = ['No Data']
        category_data = [1]
    
    # ============ CUSTOMER GROWTH ============
    customer_growth_labels = []
    new_customers_data = []
    returning_customers_data = []
    
    for i in range(5, -1, -1):
        month_start = (timezone.now() - timedelta(days=30*i)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        # New customers (joined this month)
        new_count = CustomUser.objects.filter(
            date_joined__range=[month_start, month_end],
            is_staff=False
        ).count()
        
        # Returning customers (booked this month and joined before)
        returning_count = Booking.objects.filter(
            created_at__range=[month_start, month_end]
        ).values('user').distinct().count()
        
        customer_growth_labels.append(month_start.strftime('%b'))
        new_customers_data.append(new_count)
        returning_customers_data.append(returning_count)
    
    # ============ BOOKING TRENDS ============
    # This month vs last month by week
    current_week_labels = ['Week 1', 'Week 2', 'Week 3', 'Week 4']
    current_month_data = []
    last_month_data = []
    
    # Current month
    current_month_start = timezone.now().replace(day=1)
    for week in range(4):
        week_start = current_month_start + timedelta(days=week*7)
        week_end = week_start + timedelta(days=6)
        
        count = Booking.objects.filter(
            created_at__range=[week_start, week_end]
        ).count()
        current_month_data.append(count)
    
    # Last month
    last_month_start = (timezone.now().replace(day=1) - timedelta(days=1)).replace(day=1)
    for week in range(4):
        week_start = last_month_start + timedelta(days=week*7)
        week_end = week_start + timedelta(days=6)
        
        count = Booking.objects.filter(
            created_at__range=[week_start, week_end]
        ).count()
        last_month_data.append(count)
    
    # ============ TOP SERVICES ============
    top_services = Service.objects.select_related('category').annotate(
        booking_count=Count('booking'),
        total_revenue=Sum('booking__total_price'),
        avg_rating=Avg('reviews__rating')
    ).filter(booking_count__gt=0).order_by('-booking_count')[:10]
    
    # ============ OTHER METRICS ============
    new_customers_total = CustomUser.objects.filter(
        date_joined__gte=thirty_days_ago,
        is_staff=False
    ).count()
    
    product_revenue = Order.objects.filter(
        status__in=['paid', 'completed']
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Average order value
    completed_orders = Order.objects.filter(status__in=['paid', 'completed'])
    total_orders = completed_orders.count()
    avg_order_value = 0
    if total_orders > 0:
        total_order_value = completed_orders.aggregate(total=Sum('total_amount'))['total'] or 0
        avg_order_value = total_order_value / total_orders
    
    # Customer repeat rate
    total_customers = CustomUser.objects.filter(is_staff=False).count()
    repeat_customers = Booking.objects.values('user').annotate(
        booking_count=Count('id')
    ).filter(booking_count__gt=1).count()
    repeat_rate = 0
    if total_customers > 0:
        repeat_rate = (repeat_customers / total_customers) * 100
    
    context = {
        # Revenue metrics
        'total_revenue': total_revenue,
        'monthly_revenue': monthly_revenue,
        'revenue_growth': revenue_growth,
        
        # Chart data as JSON strings
        'daily_bookings_labels': json.dumps(daily_bookings_labels),
        'daily_bookings_data': json.dumps(daily_bookings_data),
        'daily_revenue_data': json.dumps(daily_revenue_data),
        'monthly_labels': json.dumps(monthly_labels),
        'monthly_data': json.dumps(monthly_data),
        'category_labels': json.dumps(category_labels),
        'category_data': json.dumps(category_data),
        'customer_growth_labels': json.dumps(customer_growth_labels),
        'new_customers_data': json.dumps(new_customers_data),
        'returning_customers_data': json.dumps(returning_customers_data),
        'current_month_data': json.dumps(current_month_data),
        'last_month_data': json.dumps(last_month_data),
        
        # Service stats
        'top_services': top_services,
        
        # Other metrics
        'new_customers': new_customers_total,
        'product_revenue': product_revenue,
        'avg_order_value': avg_order_value,
        'repeat_rate': repeat_rate,
    }
    
    return render(request, 'admin_dashboard/analytics.html', context)


@admin_required
def settings_view(request):
    """Admin settings view"""
    settings_obj, created = AdminDashboard.objects.get_or_create(id=1)
    
    if request.method == 'POST':
        form = DashboardSettingsForm(request.POST, request.FILES, instance=settings_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Settings saved successfully!')
            return redirect('admin_dashboard:settings')
    else:
        form = DashboardSettingsForm(instance=settings_obj)
    
    context = {
        'form': form,
        'settings': settings_obj,
    }
    
    return render(request, 'admin_dashboard/settings.html', context)

@admin_required
def update_booking_status(request, booking_id):
    """Update booking status via AJAX"""
    if request.method == 'POST':
        try:
            booking = Booking.objects.get(id=booking_id)
            new_status = request.POST.get('status')
            if new_status == 'approved':
                new_status = 'confirmed'
            cancellation_reason = (request.POST.get('reason') or '').strip()
            
            if new_status in ['pending', 'awaiting_payment', 'confirmed', 'completed', 'cancelled']:
                if new_status == 'confirmed':
                    booking.status = Booking.STATUS_AWAITING_PAYMENT
                    booking.approval_time = timezone.now()
                    booking.payment_deadline = booking.approval_time + timedelta(hours=48)
                    if booking.total_price and (not booking.deposit_amount or booking.deposit_amount <= 0):
                        booking.deposit_amount = (booking.total_price * 0.5)
                    booking.save()

                    UserNotification.objects.create(
                        user=booking.user,
                        title='Booking Approved',
                        message='Your booking has been approved. Please pay the required 50% deposit to confirm your appointment.',
                        notification_type='booking_update'
                    )

                    payment_link = request.build_absolute_uri(
                        reverse('booking:booking_payment', kwargs={'booking_id': booking.id})
                    )
                    stylist_name = booking.stylist.name if booking.stylist else "Any Available Stylist"
                    email_subject = 'Booking Approved - Payment Required'
                    email_message = (
                        "Your booking has been approved.\n\n"
                        f"Service: {booking.service.name}\n"
                        f"Appointment Date: {booking.date} {booking.time}\n"
                        f"Stylist: {stylist_name}\n"
                        f"Deposit Required (50%): £{booking.deposit_amount}\n\n"
                        f"Complete payment here: {payment_link}\n"
                    )
                    try:
                        send_mail(
                            email_subject,
                            email_message,
                            settings.DEFAULT_FROM_EMAIL,
                            [booking.user.email],
                            fail_silently=False
                        )
                    except Exception:
                        pass
                    status_for_logs = Booking.STATUS_AWAITING_PAYMENT
                else:
                    booking.status = new_status
                    if new_status == Booking.STATUS_CANCELLED and booking.payment_status == "PAID":
                        booking.refund_status = Booking.REFUND_PENDING
                    booking.save()
                    status_for_logs = new_status

                if status_for_logs == Booking.STATUS_CANCELLED:
                    cancel_message = 'Your booking has been cancelled.'
                    if cancellation_reason:
                        cancel_message = f'{cancel_message} Reason: {cancellation_reason}'
                    UserNotification.objects.create(
                        user=booking.user,
                        title='Booking Cancelled',
                        message=cancel_message,
                        notification_type='booking_update'
                    )

                # Create notification
                DashboardNotification.objects.create(
                    title='Booking Status Updated',
                    message=f'Booking #{booking_id} status changed to {status_for_logs}',
                    notification_type='booking_update',
                    priority='normal'
                )
                
                # Log activity
                RecentActivity.objects.create(
                    user=request.user,
                    activity_type='booking_updated',
                    description=f'Booking #{booking_id} status updated to {status_for_logs}',
                    related_id=str(booking_id),
                    related_model='booking',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Booking status updated successfully.',
                    'updated_status': status_for_logs,
                    'display_status': booking.get_status_display(),
                    'refund_status': booking.refund_status,
                })
        except Booking.DoesNotExist:
            pass
    
    return JsonResponse({
        'success': False,
        'message': 'Failed to update booking status.'
    })


@admin_required
def mark_booking_refunded(request, booking_id):
    """Mark pending refund as refunded for a cancelled paid booking."""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    booking = get_object_or_404(Booking, id=booking_id)
    if booking.status != Booking.STATUS_CANCELLED:
        return JsonResponse({'success': False, 'message': 'Only cancelled bookings can be refunded.'}, status=400)

    if booking.refund_status != Booking.REFUND_PENDING:
        return JsonResponse({'success': False, 'message': 'Refund is not pending for this booking.'}, status=400)

    booking.refund_status = Booking.REFUND_REFUNDED
    booking.save()

    DashboardNotification.objects.create(
        title='Booking Refund Updated',
        message=f'Booking #{booking_id} marked as refunded',
        notification_type='booking_update',
        priority='normal'
    )

    RecentActivity.objects.create(
        user=request.user,
        activity_type='booking_updated',
        description=f'Booking #{booking_id} refund marked as refunded',
        related_id=str(booking_id),
        related_model='booking',
        ip_address=request.META.get('REMOTE_ADDR')
    )

    return JsonResponse({
        'success': True,
        'message': 'Refund marked as completed.',
        'refund_status': booking.refund_status,
    })

@admin_required
def get_dashboard_stats(request):
    """API endpoint for real-time dashboard stats"""
    today = timezone.now().date()
    
    stats = {
        'today_bookings': Booking.objects.filter(date=today).count(),
        'pending_bookings': Booking.objects.filter(status='pending').count(),
        'unread_messages': ContactMessage.objects.filter(is_read=False).count(),
        'low_stock_products': Product.objects.filter(stock_quantity__lte=10).count(),
    }
    
    return JsonResponse(stats)


@admin_required
def get_service_data(request, service_id):
    """Get service data for editing via AJAX"""
    try:
        service = Service.objects.get(id=service_id)
        data = {
            'success': True,
                'service': {
                    'id': service.id,
                    'name': service.name,
                    'short_description': service.short_description,
                    'full_description': service.full_description,
                    'category_id': service.category.id if service.category else None,
                    'duration': service.duration,
                    'price': float(service.price),
                    'is_available': service.is_available,
                    'service_color': service.service_color,
                }
            }
    except Service.DoesNotExist:
        data = {'success': False, 'message': 'Service not found'}
    
    return JsonResponse(data)

@admin_required
def update_service(request, service_id):
    """Update service via AJAX"""
    if request.method == 'POST':
        try:
            service = Service.objects.get(id=service_id)
            form = ServiceForm(request.POST, request.FILES, instance=service)
            
            if form.is_valid():
                service = form.save()
                
                # Log activity
                RecentActivity.objects.create(
                    user=request.user,
                    activity_type='service_updated',
                    description=f'Updated service: {service.name}',
                    related_id=str(service.id),
                    related_model='service',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Service updated successfully.'
                })
        except Service.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Service not found.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

@admin_required
def delete_service(request, service_id):
    """Delete service via AJAX"""
    if request.method == 'POST':
        try:
            service = Service.objects.get(id=service_id)
            service_name = service.name
            service.delete()
            
            # Log activity
            RecentActivity.objects.create(
                user=request.user,
                activity_type='service_updated',
                description=f'Deleted service: {service_name}',
                related_model='service',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Service deleted successfully.'
            })
        except Service.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Service not found.'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })


@admin_required
def gallery_management(request):
    """Manage gallery images"""
    _ensure_uncategorized_gallery_category()
    images = GalleryImage.objects.select_related('category').order_by('-created_at')
    categories = GalleryCategory.objects.filter(is_active=True).order_by('name')
    
    if request.method == 'POST' and 'image' in request.FILES:
        # Handle image upload
        image_file = request.FILES.get('image')
        if image_file:
            try:
                # Create new image
                image = GalleryImage(
                    title=request.POST.get('title', 'Untitled'),
                    description=request.POST.get('description', ''),
                    display_order=int(request.POST.get('display_order', 0)),
                    image_type=request.POST.get('image_type', 'standard'),
                    is_published=request.POST.get('is_published') == 'on',
                    created_by=request.user
                )
                
                # Set category
                category_id = request.POST.get('category')
                if category_id:
                    try:
                        category = GalleryCategory.objects.get(id=category_id)
                        image.category = category
                    except GalleryCategory.DoesNotExist:
                        messages.error(request, 'Invalid category selected.')
                
                # Handle image upload
                image.image = image_file
                image.save()
                
                messages.success(request, 'Image added successfully!')
                return redirect('admin_dashboard:gallery')
                
            except Exception as e:
                messages.error(request, f'Error adding image: {str(e)}')
    
    context = {
        'images': images,
        'categories': categories,
        'total_images': images.count(),
    }
    
    return render(request, 'admin_dashboard/gallery.html', context)


@admin_required
def gallery_categories_management(request):
    """Manage gallery categories."""
    _ensure_uncategorized_gallery_category()
    categories = GalleryCategory.objects.order_by('order', 'name')
    context = {
        'categories': categories,
        'total_categories': categories.count(),
    }
    return render(request, 'admin_dashboard/gallery_categories.html', context)


@admin_required
def list_gallery_categories(request):
    """Return gallery categories for dynamic dropdowns."""
    categories = GalleryCategory.objects.filter(is_active=True).order_by('order', 'name')
    return JsonResponse({
        'success': True,
        'categories': [
            {
                'id': c.id,
                'name': c.name,
                'description': c.description or '',
            }
            for c in categories
        ]
    })


@admin_required
def create_gallery_category(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    name = (request.POST.get('name') or '').strip()
    description = (request.POST.get('description') or '').strip()

    if not name:
        return JsonResponse({'success': False, 'message': 'Category name is required.'}, status=400)

    slug_base = slugify(name) or 'gallery-category'
    slug = slug_base
    counter = 1
    while GalleryCategory.objects.filter(slug=slug).exists():
        slug = f'{slug_base}-{counter}'
        counter += 1

    category = GalleryCategory.objects.create(
        name=name,
        slug=slug,
        description=description,
        is_active=True,
    )

    return JsonResponse({
        'success': True,
        'message': 'Category created successfully.',
        'category': {
            'id': category.id,
            'name': category.name,
            'description': category.description or '',
            'created_at': category.created_at.strftime('%Y-%m-%d %H:%M'),
        }
    })


@admin_required
def update_gallery_category(request, category_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    category = get_object_or_404(GalleryCategory, id=category_id)
    name = (request.POST.get('name') or '').strip()
    description = (request.POST.get('description') or '').strip()

    if not name:
        return JsonResponse({'success': False, 'message': 'Category name is required.'}, status=400)

    if category.slug == 'uncategorized' and name.lower() != 'uncategorized':
        return JsonResponse({'success': False, 'message': 'Uncategorized category name cannot be changed.'}, status=400)

    category.name = name
    category.description = description
    category.save()

    return JsonResponse({'success': True, 'message': 'Category updated successfully.'})


@admin_required
def delete_gallery_category(request, category_id):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Invalid request method.'}, status=405)

    category = get_object_or_404(GalleryCategory, id=category_id)
    if category.slug == 'uncategorized':
        return JsonResponse({'success': False, 'message': 'Uncategorized category cannot be deleted.'}, status=400)

    image_count = GalleryImage.objects.filter(category=category).count()
    if image_count > 0:
        return JsonResponse({
            'success': False,
            'message': 'This category contains images and cannot be deleted until those images are reassigned.'
        }, status=400)

    category.delete()
    return JsonResponse({'success': True, 'message': 'Category deleted successfully.'})

@admin_required
def get_gallery_image(request, image_id):
    """Get gallery image data for editing via AJAX"""
    try:
        image = GalleryImage.objects.get(id=image_id)
        data = {
            'success': True,
            'image': {
                'id': image.id,
                'title': image.title,
                'description': image.description,
                'category_id': image.category.id,
                'display_order': image.display_order,
                'image_type': image.image_type,
                'is_published': image.is_published,
                'image_url': image.image.url if image.image else None,
            }
        }
    except GalleryImage.DoesNotExist:
        data = {'success': False, 'message': 'Image not found'}
    
    return JsonResponse(data)

@admin_required
def add_gallery_image(request):
    """Add gallery image via AJAX"""
    if request.method == 'POST':
        try:
            # Handle image upload
            image_file = request.FILES.get('image')
            if not image_file:
                return JsonResponse({
                    'success': False,
                    'message': 'Please select an image file.'
                })

            category_id = request.POST.get('category')
            if not category_id:
                return JsonResponse({
                    'success': False,
                    'message': 'Please select a category.'
                }, status=400)
            
            # Create new image
            image = GalleryImage(
                title=request.POST.get('title', ''),
                description=request.POST.get('description', ''),
                display_order=int(request.POST.get('display_order', 0)),
                image_type=request.POST.get('image_type', 'standard'),
                is_published=request.POST.get('is_published') == 'on',
                created_by=request.user
            )
            
            # Set category
            try:
                category = GalleryCategory.objects.get(id=category_id)
                image.category = category
            except GalleryCategory.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Invalid category selected.'
                }, status=400)
            
            # Handle image upload
            image.image = image_file
            image.save()
            
            # Log activity
            RecentActivity.objects.create(
                user=request.user,
                activity_type='service_added',
                description=f'Added gallery image: {image.title}',
                related_id=str(image.id),
                related_model='gallery_image',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Image added successfully.',
                'image': {
                    'id': image.id,
                    'title': image.title,
                    'image_url': image.image.url if image.image else '',
                    'category': image.category.name if image.category else '',
                }
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

@admin_required
def update_gallery_image(request, image_id):
    """Update gallery image via AJAX"""
    if request.method == 'POST':
        try:
            image = GalleryImage.objects.get(id=image_id)
            
            # Update fields
            image.title = request.POST.get('title', image.title)
            image.description = request.POST.get('description', image.description)
            image.display_order = int(request.POST.get('display_order', image.display_order))
            image.image_type = request.POST.get('image_type', image.image_type)
            image.is_published = request.POST.get('is_published') == 'on'
            
            # Update category
            category_id = request.POST.get('category')
            if category_id:
                try:
                    category = GalleryCategory.objects.get(id=category_id)
                    image.category = category
                except GalleryCategory.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Invalid category selected.'
                    })
            
            # Handle image upload if new image provided
            new_image = request.FILES.get('image')
            if new_image:
                image.image = new_image
            
            image.save()
            
            # Log activity
            RecentActivity.objects.create(
                user=request.user,
                activity_type='service_updated',
                description=f'Updated gallery image: {image.title}',
                related_id=str(image.id),
                related_model='gallery_image',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Image updated successfully.',
                'image': {
                    'id': image.id,
                    'title': image.title,
                    'image_url': image.image.url if image.image else '',
                    'category': image.category.name if image.category else '',
                }
            })
            
        except GalleryImage.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Image not found.'
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': f'Error: {str(e)}'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

@admin_required
def delete_gallery_image(request, image_id):
    """Delete gallery image via AJAX"""
    if request.method == 'POST':
        try:
            image = GalleryImage.objects.get(id=image_id)
            image_title = image.title
            image.delete()
            
            # Log activity
            RecentActivity.objects.create(
                user=request.user,
                activity_type='service_updated',
                description=f'Deleted gallery image: {image_title}',
                related_model='gallery_image',
                ip_address=request.META.get('REMOTE_ADDR')
            )
            
            return JsonResponse({
                'success': True,
                'message': 'Image deleted successfully.'
            })
        except GalleryImage.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Image not found.'
            })
    
    return JsonResponse({
        'success': False,
        'message': 'Invalid request method.'
    })

