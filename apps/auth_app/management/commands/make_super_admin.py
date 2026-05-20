"""
Management command: make_super_admin

Usage:
    python manage.py make_super_admin admin@example.com

Promueve un UserProfile existente al rol super_admin.
El usuario ya debe estar registrado y con email confirmado.
"""

from django.core.management.base import BaseCommand, CommandError
from apps.auth_app.models import UserProfile


class Command(BaseCommand):
    help = "Promote an existing user to super_admin role."

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="Email of the user to promote")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()

        try:
            profile = UserProfile.objects.get(email=email)
        except UserProfile.DoesNotExist:
            raise CommandError(
                f'No UserProfile found for "{email}". '
                "Use create_super_admin to create a new super admin user."
            )

        if profile.role == "super_admin":
            self.stdout.write(self.style.WARNING(f'"{email}" is already a super_admin.'))
            return

        profile.role = "super_admin"
        profile.save(update_fields=["role"])

        self.stdout.write(
            self.style.SUCCESS(f'Successfully promoted "{email}" to super_admin.')
        )
