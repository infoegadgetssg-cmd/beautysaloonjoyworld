from allauth.account.adapter import DefaultAccountAdapter
from django.urls import reverse


class CustomAccountAdapter(DefaultAccountAdapter):

    def get_login_redirect_url(self, request):
        """Redirect staff/admin users to the admin dashboard, everyone else to user dashboard."""
        if request.user.is_staff:
            return reverse('admin_dashboard:index')
        return reverse('user_dashboard:dashboard')
