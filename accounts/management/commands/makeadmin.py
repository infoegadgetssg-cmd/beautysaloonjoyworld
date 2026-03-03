from django.core.management.base import BaseCommand, CommandError
from accounts.models import CustomUser


class Command(BaseCommand):
    help = 'Promote an existing user to admin (staff + superuser) by their email'

    def add_arguments(self, parser):
        parser.add_argument('email', type=str, help='Email of the user to promote')
        parser.add_argument(
            '--staff-only',
            action='store_true',
            help='Only set is_staff=True (access admin dashboard) without full superuser',
        )

    def handle(self, *args, **options):
        email = options['email']
        staff_only = options['staff_only']

        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            raise CommandError(f'No user found with email "{email}"')

        if user.is_staff and user.is_superuser:
            self.stdout.write(self.style.WARNING(f'"{email}" is already an admin.'))
            return

        user.is_staff = True
        if not staff_only:
            user.is_superuser = True

        user.save()

        level = 'staff' if staff_only else 'admin (staff + superuser)'
        self.stdout.write(self.style.SUCCESS(f'"{email}" has been promoted to {level}.'))
