# admin_dashboard/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum, Avg, Q
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse
from django.core.paginator import Paginator

from accounts.models import CustomUser
from booking.models import Booking
from services.models import Stylist
from services.models import Service, ServiceCategory 
from shop.models import Product, ProductCategory, Order
from contact.models import ContactMessage
from .models import DashboardNotification, RecentActivity, AdminDashboard
from .forms import DashboardSettingsForm, ServiceForm, ProductForm
from gallery.models import GalleryImage, GalleryCategory
import json



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
    
    # Revenue statistics
    total_revenue = Booking.objects.filter(
        status__in=['confirmed', 'completed']
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    monthly_revenue = Booking.objects.filter(
        status__in=['confirmed', 'completed'],
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
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
        'total_revenue': f"£{total_revenue:.2f}",
        'monthly_revenue': f"£{monthly_revenue:.2f}",
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
    
    customers = CustomUser.objects.filter(is_staff=False)
    
    if search_query:
        customers = customers.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    # Get specific customer if requested
    customer_id = request.GET.get('customer_id')
    selected_customer = None
    
    if customer_id:
        try:
            selected_customer = customers.get(id=customer_id)
        except CustomUser.DoesNotExist:
            pass
    elif customers.exists():
        # Default to first customer
        selected_customer = customers.first()
    

    # Calculate statistics for selected customer
    customer_stats = {}
    if selected_customer:
        # Get bookings count
        booking_count = Booking.objects.filter(user=selected_customer).count()
        
        # Get total spent from completed orders
        total_spent = Order.objects.filter(
            user=selected_customer,
            status='completed'
        ).aggregate(total=Sum('total_amount'))['total'] or 0
        
        # Get recent bookings
        recent_bookings = Booking.objects.filter(
            user=selected_customer
        ).select_related('service').order_by('-date', '-time')[:5]
        
        # Calculate loyalty points (example: £1 spent = 10 points)
        loyalty_points = int(total_spent * 10)
        
        # Determine tier based on spending
        if total_spent >= 1000:
            tier = "Platinum"
        elif total_spent >= 500:
            tier = "Gold"
        elif total_spent >= 200:
            tier = "Silver"
        else:
            tier = "Bronze"
        
        customer_stats = {
            'customer': selected_customer,
            'booking_count': booking_count,
            'total_spent': total_spent,
            'recent_bookings': recent_bookings,
            'loyalty_points': loyalty_points,
            'tier': tier,
            'member_since': selected_customer.date_joined.strftime("%b %d, %Y") if selected_customer.date_joined else "N/A",
        }
    
    context = {
        'customers': customers,
        'selected_customer': customer_stats,
        'search_query': search_query,
        'total_customers': customers.count(),
    }
    
    return render(request, 'admin_dashboard/customers.html', context)

@admin_required
def services_management(request):
    """Manage services"""
    services = Service.objects.all()
    
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
                
                messages.success(request, 'Service added successfully!')
                return redirect('admin_dashboard:services')
            except Exception as e:
                messages.error(request, f'Error saving service: {str(e)}')
        else:
            # Show form errors
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = ServiceForm()
    
    context = {
        'services': services,
        'form': form,
        'total_services': services.count(),
    }
    
    return render(request, 'admin_dashboard/services.html', context)


@admin_required
def products_management(request):
    """Manage products"""
    products = Product.objects.all()
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
            
            return JsonResponse({
                'success': True,
                'message': 'Product deleted successfully.'
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
    total_revenue = Booking.objects.filter(
        status__in=['confirmed', 'completed']
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    # Monthly revenue (last 30 days)
    monthly_revenue = Booking.objects.filter(
        status__in=['confirmed', 'completed'],
        created_at__gte=thirty_days_ago
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    # Previous month revenue for comparison
    previous_month_start = timezone.now() - timedelta(days=60)
    previous_month_end = timezone.now() - timedelta(days=30)
    previous_month_revenue = Booking.objects.filter(
        status__in=['confirmed', 'completed'],
        created_at__range=[previous_month_start, previous_month_end]
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
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
        revenue = Booking.objects.filter(
            status__in=['confirmed', 'completed'],
            created_at__range=[day_start, day_end]
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
        daily_bookings_labels.append(day.strftime('%b %d'))
        daily_bookings_data.append(count)
        daily_revenue_data.append(float(revenue))
    
    # ============ MONTHLY REVENUE (Last 6 months) ============
    monthly_labels = []
    monthly_data = []
    
    for i in range(5, -1, -1):
        month_start = (timezone.now() - timedelta(days=30*i)).replace(day=1)
        month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
        
        revenue = Booking.objects.filter(
            status__in=['confirmed', 'completed'],
            created_at__range=[month_start, month_end]
        ).aggregate(total=Sum('total_price'))['total'] or 0
        
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
        status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    # Average order value
    completed_orders = Order.objects.filter(status='completed')
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
            
            if new_status in ['pending', 'confirmed', 'completed', 'cancelled']:
                booking.status = new_status
                booking.save()
                
                # Create notification
                DashboardNotification.objects.create(
                    title='Booking Status Updated',
                    message=f'Booking #{booking_id} status changed to {new_status}',
                    notification_type='booking_update',
                    priority='normal'
                )
                
                # Log activity
                RecentActivity.objects.create(
                    user=request.user,
                    activity_type='booking_updated',
                    description=f'Booking #{booking_id} status updated to {new_status}',
                    related_id=str(booking_id),
                    related_model='booking',
                    ip_address=request.META.get('REMOTE_ADDR')
                )
                
                return JsonResponse({
                    'success': True,
                    'message': 'Booking status updated successfully.'
                })
        except Booking.DoesNotExist:
            pass
    
    return JsonResponse({
        'success': False,
        'message': 'Failed to update booking status.'
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
                'description': service.description,
                'category': service.category.name if service.category else None,
                'duration': service.duration,
                'price': float(service.price),
                'is_available': service.is_available,
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
                'message': 'Image added successfully.'
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
                'message': 'Image updated successfully.'
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
