"""
Management command: create_super_admin

Usage:
    python manage.py create_super_admin admin@example.com --password SecurePass123

Crea un super admin directamente sin pasar por el flujo de verificación de email.
Útil para el setup inicial del proyecto.
"""

from django.core.management.base import BaseCommand, CommandError
from apps.auth_app.models import UserProfile


class Command(BaseCommand):
    help = "Create a super admin user directly (bypasses email verification)."

    def add_arguments(self, parser):
        parser.add_argument("email", type=str, help="Email for the super admin")
        parser.add_argument("--password", type=str, required=True, help="Password (min 8 chars)")
        parser.add_argument("--name", type=str, default="", help="Full name (optional)")

    def handle(self, *args, **options):
        email = options["email"].strip().lower()
        password = options["password"]
        full_name = options.get("name", "")

        if len(password) < 8:
            raise CommandError("Password must be at least 8 characters.")

        if UserProfile.objects.filter(email=email).exists():
            raise CommandError(
                f'A user with email "{email}" already exists. '
                "Use make_super_admin to promote an existing user."
            )

        profile = UserProfile(
            email=email,
            full_name=full_name,
            role="super_admin",
            email_confirmed=True,
            is_active=True,
        )
        profile.set_password(password)
        profile.save()

        self.stdout.write(
            self.style.SUCCESS(f'Super admin "{email}" created successfully.')
        )
