from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse
from django.conf import settings
from django.core.mail import send_mail
import logging

logger = logging.getLogger(__name__)

class CustomAccountAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, request):
        """Redirect staff/admin users to the admin dashboard, everyone else to user dashboard."""
        if request.user.is_staff:
            return reverse('admin_dashboard:index')
        return reverse('user_dashboard:dashboard')

    def confirm_email(self, request, email_address):
        """Send admin notification when a user confirms registration email."""
        result = super().confirm_email(request, email_address)

        recipients = []
        admin_email = getattr(settings, "ADMIN_EMAIL", "")
        if admin_email:
            recipients.append(admin_email)

        recipients.extend(list(getattr(settings, "ADMIN_NOTIFICATION_EMAILS", [])))

        admins = getattr(settings, "ADMINS", [])
        for admin in admins:
            if isinstance(admin, (list, tuple)) and len(admin) >= 2 and admin[1]:
                recipients.append(admin[1])

        recipients = list(dict.fromkeys([email for email in recipients if email]))

        if recipients:
            user = email_address.user
            try:
                send_mail(
                    subject="New User Registration",
                    message=(
                        "A new user has registered on the website.\n\n"
                        f"Email: {user.email}\n"
                        f"Username: {user.username}\n\n"
                        "Login to the admin dashboard to view the user."
                    ),
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=recipients,
                    fail_silently=True,
                )
            except Exception:
                logger.exception("Failed to send admin registration notification for user_id=%s", user.id)

        return result
