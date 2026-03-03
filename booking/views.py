# booking/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
import datetime
from .models import Booking, AdditionalService
from services.models import Service, Stylist
from .forms import BookingForm

@login_required
def booking_view(request):
    # Get available services and stylists
    services = Service.objects.filter(is_available=True)
    stylists = Stylist.objects.filter(is_available=True)
    additional_services = AdditionalService.objects.filter(is_available=True)
    
    # Generate time slots (9am to 7pm)
    time_slots = []
    for hour in range(9, 19):  # 9am to 7pm
        time_slots.append(datetime.time(hour, 0))
        time_slots.append(datetime.time(hour, 30))
    
    if request.method == 'POST':
        form = BookingForm(request.POST)
        if form.is_valid():
            try:
                with transaction.atomic():
                    # Create booking
                    booking = form.save(commit=False)
                    booking.user = request.user
                    booking.duration = booking.service.duration
                    booking.total_price = booking.service.price

                    # Save booking first
                    booking.save()

                    # Handle additional services
                    additional_services_ids = request.POST.getlist('additional_services')
                    from .models import BookingAdditionalService
                    for service_id in additional_services_ids:
                        add_service = AdditionalService.objects.get(id=service_id)
                        booking.total_price += add_service.price
                        BookingAdditionalService.objects.create(
                            booking=booking,
                            additional_service=add_service
                        )

                    # Save with updated total price
                    booking.save()

                messages.success(request, 'Booking confirmed successfully!')
                return redirect('booking_success', booking_id=booking.id)

            except Exception as e:
                messages.error(request, f'Error creating booking: {str(e)}')
    else:
        form = BookingForm()
    
    context = {
        'form': form,
        'services': services,
        'stylists': stylists,
        'additional_services': additional_services,
        'time_slots': time_slots,
    }
    
    return render(request, 'booking/booking.html', context)

@login_required
def booking_success_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    context = {
        'booking': booking,
    }
    return render(request, 'booking/booking_success.html', context)

@login_required
def booking_history_view(request):
    bookings = Booking.objects.filter(user=request.user).order_by('-date', '-time')
    context = {
        'bookings': bookings,
    }
    return render(request, 'booking/booking_history.html', context)

@login_required
def booking_detail_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    context = {
        'booking': booking,
    }
    return render(request, 'booking/booking_detail.html', context)

@login_required
def cancel_booking_view(request, booking_id):
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        if booking.status in ['pending', 'confirmed']:
            booking.status = 'cancelled'
            booking.save()
            messages.success(request, 'Booking cancelled successfully.')
        else:
            messages.error(request, 'Cannot cancel this booking.')
        return redirect('booking_history')