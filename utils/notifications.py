# utils/notifications.py
from django.core.mail import send_mail
from django.conf import settings

def send_booking_confirmation(booking):
    subject = f'Booking Confirmation - {booking.service.name}'
    message = f'''
    Dear {booking.user.get_full_name()},
    
    Your booking has been confirmed:
    Service: {booking.service.name}
    Date: {booking.date}
    Time: {booking.time}
    Stylist: {booking.stylist.name if booking.stylist else 'Any Available'}
    Total: £{booking.total_price}
    
    Thank you for choosing Joy World Beauty!
    '''
    send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [booking.user.email])

def send_order_confirmation(order):
    # Similar implementation for orders
    pass