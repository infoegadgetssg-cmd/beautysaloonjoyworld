# booking/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from django.http import JsonResponse
from django.contrib.admin.views.decorators import staff_member_required
import datetime
import requests
from .models import Booking, AdditionalService
from services.models import Service, Stylist
from contact.models import ContactMessage
from user_dashboard.models import UserNotification
from .forms import BookingForm
from core.notifications import send_booking_notifications


def _expire_unpaid_bookings():
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
            message='Your booking was cancelled because the deposit was not paid within 48 hours.',
            notification_type='booking_update'
        )

@login_required
def booking_view(request):
    _expire_unpaid_bookings()
    # Get available services and stylists
    services = Service.objects.filter(is_available=True)
    stylists = Stylist.objects.filter(is_active=True, is_available=True)
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
                    send_booking_notifications(booking)
                    ContactMessage.objects.create(
                        name=f"{booking.user.first_name or booking.user.username} {booking.user.last_name or ''}".strip() or booking.user.email,
                        email=booking.user.email,
                        subject=f"New Booking Request: {booking.service.name}",
                        message=(
                            f"New booking received via the website.\n\n"
                            f"Service: {booking.service.name}\n"
                            f"Date: {booking.date}\n"
                            f"Time: {booking.time}\n"
                            f"Total: £{booking.total_price}\n"
                            f"User: {booking.user.get_full_name() or booking.user.username} ({booking.user.email})\n"
                        ),
                        status='new',
                        topic='booking'
                    )

                messages.success(request, 'Booking confirmed successfully!')
                return redirect('booking:booking_success', booking_id=booking.id)

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
    _expire_unpaid_bookings()
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    selected_additional_services = booking.additional_services.select_related('additional_service').all()
    context = {
        'booking': booking,
        'selected_additional_services': selected_additional_services,
    }
    return render(request, 'booking/booking_success.html', context)


def cancellation_policy_view(request):
    return render(request, 'booking/cancellation_policy.html')

@login_required
def booking_history_view(request):
    _expire_unpaid_bookings()
    return redirect('user_dashboard:bookings')

@login_required
def booking_detail_view(request, booking_id):
    _expire_unpaid_bookings()
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    context = {
        'booking': booking,
    }
    return render(request, 'booking/booking_detail.html', context)

@login_required
def cancel_booking_view(request, booking_id):
    _expire_unpaid_bookings()
    if request.method == 'POST':
        booking = get_object_or_404(Booking, id=booking_id, user=request.user)
        if booking.status in [Booking.STATUS_PENDING, Booking.STATUS_AWAITING_PAYMENT, Booking.STATUS_CONFIRMED]:
            booking.status = Booking.STATUS_CANCELLED
            if booking.payment_status == "PAID":
                booking.refund_status = Booking.REFUND_PENDING
            booking.save()
            UserNotification.objects.create(
                user=request.user,
                title='Booking Cancelled',
                message='Your booking has been cancelled.',
                notification_type='booking_update'
            )
            messages.success(request, 'Booking cancelled successfully.')
        else:
            messages.error(request, 'Cannot cancel this booking.')
        return redirect('booking:booking_history')


@login_required
def booking_payment_view(request, booking_id):
    _expire_unpaid_bookings()
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)

    if booking.status == Booking.STATUS_CANCELLED:
        messages.error(request, 'This booking has been cancelled.')
        return redirect('user_dashboard:bookings')

    if request.method == 'POST':
        if booking.status == Booking.STATUS_AWAITING_PAYMENT and not booking.deposit_paid:
            booking.deposit_paid = True
            booking.status = Booking.STATUS_CONFIRMED
            booking.save()
            UserNotification.objects.create(
                user=request.user,
                title='Booking Confirmed',
                message='Your booking has been confirmed.',
                notification_type='booking_confirmation'
            )
            messages.success(request, 'Deposit paid successfully. Your booking is confirmed.')
        return redirect('booking:booking_detail', booking_id=booking.id)

    payment_amount = booking.deposit_amount if booking.deposit_amount else booking.total_price
    context = {
        'booking': booking,
        'paystack_public_key': settings.PAYSTACK_PUBLIC_KEY,
        'paystack_amount_kobo': int(payment_amount * 100),
        'paystack_reference': f"BOOKING_{booking.id}_{int(timezone.now().timestamp())}",
    }
    return render(request, 'booking/payment.html', context)


@login_required
def verify_booking_payment_view(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id, user=request.user)
    reference = request.GET.get('reference')

    if not reference:
        messages.error(request, 'Missing payment reference.')
        return redirect('booking:booking_payment', booking_id=booking.id)

    verify_url = f"https://api.paystack.co/transaction/verify/{reference}"
    headers = {"Authorization": f"Bearer {settings.PAYSTACK_SECRET_KEY}"}
    response = requests.get(verify_url, headers=headers, timeout=30)

    if response.status_code != 200:
        messages.error(request, 'Payment verification failed. Please try again.')
        return redirect('booking:booking_payment', booking_id=booking.id)

    payload = response.json()
    data = payload.get('data', {})
    paystack_status = data.get('status')
    paid_amount = data.get('amount', 0)  # in kobo
    expected_amount = int((booking.deposit_amount if booking.deposit_amount else booking.total_price) * 100)

    if payload.get('status') and paystack_status == 'success' and int(paid_amount) >= expected_amount:
        booking.deposit_paid = True
        booking.status = Booking.STATUS_CONFIRMED
        booking.notes = (booking.notes + "\n" if booking.notes else "") + f"Paystack Ref: {reference}"
        booking.save()

        UserNotification.objects.create(
            user=request.user,
            title='Booking Confirmed',
            message='Your booking has been confirmed.',
            notification_type='booking_confirmation'
        )

        messages.success(request, 'Payment successful. Your booking is confirmed.')
        return redirect('booking:booking_success', booking_id=booking.id)

    messages.error(request, 'Payment could not be verified.')
    return redirect('booking:booking_payment', booking_id=booking.id)


@staff_member_required
def admin_booking_calendar(request):
    return render(request, 'admin/booking_calendar.html')


@staff_member_required
def bookings_json(request):
    events = []
    color_map = {
        Booking.STATUS_PENDING: '#ffc107',
        Booking.STATUS_AWAITING_PAYMENT: '#fd7e14',
        Booking.STATUS_CONFIRMED: '#0d6efd',
        Booking.STATUS_COMPLETED: '#198754',
        Booking.STATUS_CANCELLED: '#dc3545',
    }

    bookings = Booking.objects.select_related('service', 'user').all()
    for booking in bookings:
        start_dt = datetime.datetime.combine(booking.date, booking.time)
        events.append({
            'title': f'{booking.service.name} - {booking.user.get_full_name() or booking.user.username}',
            'start': start_dt.isoformat(),
            'color': color_map.get(booking.status, '#6c757d'),
        })

    return JsonResponse(events, safe=False)


def calendar_events(request):
    bookings = Booking.objects.select_related('service').all()
    events = []
    for booking in bookings:
        start_dt = datetime.datetime.combine(booking.date, booking.time)
        color = booking.service.service_color or '#6b7280'
        events.append({
            'id': booking.id,
            'title': booking.service.name,
            'start': start_dt.isoformat(),
            'backgroundColor': color,
        })
    return JsonResponse(events, safe=False)
