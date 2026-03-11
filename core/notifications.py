import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings

logger = logging.getLogger(__name__)


def _admin_recipients():
    recipients = []

    admin_email = getattr(settings, "ADMIN_EMAIL", None)
    if admin_email:
        if isinstance(admin_email, str) and "," in admin_email:
            recipients.extend([email.strip() for email in admin_email.split(",") if email.strip()])
        elif isinstance(admin_email, (list, tuple)):
            recipients.extend([email for email in admin_email if isinstance(email, str) and email.strip()])
        elif isinstance(admin_email, str):
            recipients.append(admin_email)

    admins = getattr(settings, "ADMINS", [])
    for admin in admins:
        if isinstance(admin, (list, tuple)) and len(admin) >= 2 and admin[1]:
            recipients.append(admin[1])

    if not recipients:
        recipients.append(settings.DEFAULT_FROM_EMAIL)

    # preserve order, remove duplicates
    return list(dict.fromkeys(recipients))


def log_admin_activity(action, description, user=None, related_id="", related_model="order"):
    """Create admin dashboard activity entries for business events."""
    try:
        from admin_dashboard.models import RecentActivity

        RecentActivity.objects.create(
            user=user,
            activity_type="payment_received",
            description=f"{action}: {description}",
            related_id=str(related_id) if related_id else "",
            related_model=related_model,
        )
    except Exception as exc:
        logger.exception("Failed to log admin activity: %s", exc)


def _send_html_email(subject, template_name, context, recipient_list):
    try:
        html_message = render_to_string(template_name, context)
        send_mail(
            subject=subject,
            message="",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as exc:
        logger.exception("Email send failed for subject '%s': %s", subject, exc)


def send_order_notifications(order):
    context = {
        "order": order,
        "customer_name": order.user.get_full_name() or order.user.email,
        "order_items": order.items.select_related("product").all(),
    }

    _send_html_email(
        subject="New Order Received",
        template_name="emails/admin_new_order.html",
        context=context,
        recipient_list=_admin_recipients(),
    )

    if order.user and order.user.email:
        _send_html_email(
            subject="Your Order Has Been Received",
            template_name="emails/order_confirmation.html",
            context=context,
            recipient_list=[order.user.email],
        )

    customer_name = order.user.get_full_name() or order.user.email
    log_admin_activity(
        action="New Order",
        description=f"Order #{order.id} placed by {customer_name} ({order.total_amount:.2f})",
        user=order.user,
        related_id=order.id,
        related_model="order",
    )


def send_booking_notifications(booking):
    context = {
        "booking": booking,
        "customer_name": booking.user.get_full_name() or booking.user.email,
    }

    _send_html_email(
        subject="New Service Booking",
        template_name="emails/admin_new_booking.html",
        context=context,
        recipient_list=_admin_recipients(),
    )

    if booking.user and booking.user.email:
        _send_html_email(
            subject="Booking Request Received",
            template_name="emails/booking_confirmation.html",
            context=context,
            recipient_list=[booking.user.email],
        )


def send_contact_notifications(contact):
    context = {"contact": contact}

    _send_html_email(
        subject="New Contact Message",
        template_name="emails/admin_new_contact.html",
        context=context,
        recipient_list=_admin_recipients(),
    )

    if contact.email:
        _send_html_email(
            subject="We Have Received Your Message",
            template_name="emails/contact_received.html",
            context=context,
            recipient_list=[contact.email],
        )
