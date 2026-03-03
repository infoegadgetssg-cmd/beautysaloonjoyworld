# user_dashboard/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Count, Sum
from django.utils import timezone
from datetime import datetime, timedelta
from django.http import JsonResponse
import json

from accounts.models import CustomUser
from booking.models import Booking
from services.models import Stylist
from services.models import Service
from shop.models import Product, Order, OrderItem
from .models import UserFavorite, UserNotification, UserLoyalty, LoyaltyProgram
from .forms import UserProfileForm
from django.core.paginator import Paginator


@login_required
def user_dashboard(request):
    """Main user dashboard view"""
    user = request.user
    
    # Get user bookings
    all_bookings = Booking.objects.filter(user=user).select_related('service', 'stylist').order_by('-date', '-time')
    recent_bookings = all_bookings[:10]  # Slice after ordering
    
    # Get upcoming bookings
    today = timezone.now().date()
    upcoming_bookings = all_bookings.filter(
        date__gte=today,
        status__in=['pending', 'confirmed']
    )[:5]
    
    # Get user orders
    orders = Order.objects.filter(user=user).order_by('-created_at')[:5]

    # Calculate total spent using database aggregation
    total_spent = Order.objects.filter(user=user).aggregate(
        total=Sum('total_amount')
    )['total'] or 0
    
    # Get user favorites
    favorite_services = UserFavorite.objects.filter(user=user, service__isnull=False).select_related('service')[:5]
    favorite_products = UserFavorite.objects.filter(user=user, product__isnull=False).select_related('product')[:5]
    
    # Get unread notifications
    unread_notifications = UserNotification.objects.filter(user=user, is_read=False).count()
    
    # Get or create user loyalty
    user_loyalty, created = UserLoyalty.objects.get_or_create(user=user)
    if created:
        # Initialize with appropriate level based on points
        user_loyalty.update_level()
    
    # Calculate statistics
    total_bookings = Booking.objects.filter(user=user).count()
    total_orders = Order.objects.filter(user=user).count()
    
    # Add booking total to spent
    booking_spent = Booking.objects.filter(
        user=user,
        status__in=['confirmed', 'completed']
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    total_spent += booking_spent
    
    # Update loyalty total spent
    if created or user_loyalty.total_spent != total_spent:
        user_loyalty.total_spent = total_spent
        user_loyalty.save()
    
    context = {
        'user': user,
        'bookings': recent_bookings,
        'upcoming_bookings': upcoming_bookings,
        'orders': orders,
        'favorite_services': favorite_services,
        'favorite_products': favorite_products,
        'unread_notifications': unread_notifications,
        'user_loyalty': user_loyalty,
        'total_bookings': total_bookings,
        'total_orders': total_orders,
        'total_spent': total_spent,
    }
    
    return render(request, 'user_dashboard/dashboard.html', context)

@login_required
def user_bookings(request):
    """User's booking history"""
    user = request.user
    bookings_list = Booking.objects.filter(user=user).select_related('service', 'stylist').order_by('-date', '-time')

    # Pagination
    paginator = Paginator(bookings_list, 10)
    page_number = request.GET.get('page')
    bookings = paginator.get_page(page_number)

    context = {
        'bookings': bookings,
        'total_bookings': paginator.count,
    }
    
    return render(request, 'user_dashboard/bookings.html', context)

# Update user_orders view
@login_required
def user_orders(request):
    """User's order history"""
    user = request.user
    orders_list = Order.objects.filter(user=user).order_by('-created_at')

    # Pagination
    paginator = Paginator(orders_list, 5)
    page_number = request.GET.get('page')
    orders = paginator.get_page(page_number)

    context = {
        'orders': orders,
        'total_orders': paginator.count,
    }
    
    return render(request, 'user_dashboard/orders.html', context)

# Add mark_all_read view
@login_required
def mark_all_read(request):
    """Mark all notifications as read"""
    UserNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    messages.success(request, 'All notifications marked as read')
    return redirect('user_dashboard:notifications')


@login_required
def user_profile(request):
    """User profile editing"""
    user = request.user
    
    if request.method == 'POST':
        form = UserProfileForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Profile updated successfully!')
            return redirect('user_dashboard:profile')
    else:
        form = UserProfileForm(instance=user)
    
    context = {
        'form': form,
    }
    
    return render(request, 'user_dashboard/profile.html', context)

@login_required
def user_favorites(request):
    """User's favorite items"""
    user = request.user
    favorite_services = UserFavorite.objects.filter(user=user, service__isnull=False).select_related('service')
    favorite_products = UserFavorite.objects.filter(user=user, product__isnull=False).select_related('product')
    
    context = {
        'favorite_services': favorite_services,
        'favorite_products': favorite_products,
    }
    
    return render(request, 'user_dashboard/favorites.html', context)

@login_required
def add_to_favorites(request):
    """AJAX endpoint to add item to favorites"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item_type = data.get('type')
            item_id = data.get('id')
            
            if item_type == 'service':
                service = get_object_or_404(Service, id=item_id)
                favorite, created = UserFavorite.objects.get_or_create(
                    user=request.user,
                    service=service
                )
                message = 'Service added to favorites' if created else 'Service already in favorites'
            elif item_type == 'product':
                product = get_object_or_404(Product, id=item_id)
                favorite, created = UserFavorite.objects.get_or_create(
                    user=request.user,
                    product=product
                )
                message = 'Product added to favorites' if created else 'Product already in favorites'
            else:
                return JsonResponse({'success': False, 'message': 'Invalid item type'})
            
            return JsonResponse({'success': True, 'message': message})
            
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def remove_from_favorites(request, favorite_id):
    """Remove item from favorites"""
    favorite = get_object_or_404(UserFavorite, id=favorite_id, user=request.user)
    favorite.delete()
    messages.success(request, 'Removed from favorites')
    return redirect('user_dashboard:favorites')

@login_required
def user_notifications(request):
    """User notifications"""
    notifications = UserNotification.objects.filter(user=request.user).order_by('-created_at')
    
    # Mark as read
    unread_notifications = notifications.filter(is_read=False)
    if unread_notifications.exists():
        unread_notifications.update(is_read=True)
    
    context = {
        'notifications': notifications,
    }
    
    return render(request, 'user_dashboard/notifications.html', context)

@login_required
def delete_notification(request, notification_id):
    """Delete a notification"""
    notification = get_object_or_404(UserNotification, id=notification_id, user=request.user)
    notification.delete()
    messages.success(request, 'Notification deleted')
    return redirect('user_dashboard:notifications')

@login_required
def cancel_booking(request, booking_id):
    """Cancel a booking"""
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    
    if booking.status in ['pending', 'confirmed']:
        booking.status = 'cancelled'
        booking.save()
        
        # Create notification for user
        UserNotification.objects.create(
            user=request.user,
            title='Booking Cancelled',
            message=f'Your booking for {booking.service.name} on {booking.date} at {booking.time} has been cancelled.',
            notification_type='booking_update'
        )
        
        messages.success(request, 'Booking cancelled successfully')
    else:
        messages.error(request, 'Cannot cancel this booking')
    
    return redirect('user_dashboard:bookings')


@login_required
def get_dashboard_stats(request):
    """API endpoint for dashboard stats"""
    user = request.user
    
    # Calculate stats
    total_bookings = Booking.objects.filter(user=user).count()
    
    today = timezone.now().date()
    today_bookings = Booking.objects.filter(user=user, date=today).count()
    
    user_loyalty, _ = UserLoyalty.objects.get_or_create(user=user)
    
    total_spent = Order.objects.filter(
        user=user,
        status='completed'
    ).aggregate(total=Sum('total_amount'))['total'] or 0
    
    booking_spent = Booking.objects.filter(
        user=user,
        status__in=['confirmed', 'completed']
    ).aggregate(total=Sum('total_price'))['total'] or 0
    
    total_spent += booking_spent
    
    stats = {
        'total_bookings': total_bookings,
        'today_bookings': today_bookings,
        'loyalty_points': user_loyalty.points,
        'total_spent': f"£{total_spent:.2f}",
        'loyalty_level': user_loyalty.level.get_level_display() if user_loyalty.level else 'Beauty Explorer',
    }
    
    return JsonResponse(stats)