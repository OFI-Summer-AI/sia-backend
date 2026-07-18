"""
Invite users into SIA without setting a password for them.

Creates (or reuses) a tenant, creates each user pre-verified with NO usable
password, assigns them to the tenant, and emails each person a set-password
link so they choose their own password.

Usage:
    python manage.py invite_users \
        --tenant "Brand Babes" --agents mark \
        "Bo:bo@brandbabes.agency" "Romy:romy@brandbabes.agency"

    python manage.py invite_users \
        --tenant "Dubbel Lef" --agents mark \
        "Eline:eline@dubbellef.nl"

Users are given as positional args, either "Full Name:email" or plain "email".
Idempotent: existing users are not recreated (use --resend to re-send their
set-password email); an existing tenant with the same name is reused.
"""

from datetime import timedelta

from django.conf import settings
from django.contrib.auth.hashers import make_password
from django.core.mail import EmailMultiAlternatives
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.auth_app.models import UserProfile
from apps.tenants.models import Tenant


class Command(BaseCommand):
    help = "Create pre-verified users on a tenant and email them a set-password link."

    def add_arguments(self, parser):
        parser.add_argument(
            "users",
            nargs="+",
            help='Users to invite: "Full Name:email" or plain "email".',
        )
        parser.add_argument("--tenant", required=True, help="Tenant/company name (created if missing).")
        parser.add_argument(
            "--tenant-email",
            help="Tenant primary contact email (defaults to the first invited email).",
        )
        parser.add_argument(
            "--agents",
            choices=["mark", "hr", "both"],
            default="mark",
            help="Subscription type for a newly created tenant (default: mark).",
        )
        parser.add_argument(
            "--invite-hours",
            type=int,
            default=72,
            help="Validity of the set-password link in hours (default: 72).",
        )
        parser.add_argument(
            "--resend",
            action="store_true",
            help="Re-send the set-password email to users that already exist.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Show what would happen, change nothing.")

    def handle(self, *args, **options):
        tenant_name = options["tenant"]
        agents = options["agents"]
        invite_hours = options["invite_hours"]
        resend = options["resend"]
        dry_run = options["dry_run"]

        # ---- Parse and validate users up front ------------------------------
        invites = []  # (full_name, email)
        for raw in options["users"]:
            if ":" in raw:
                full_name, email = raw.split(":", 1)
            else:
                full_name, email = "", raw
            email = email.strip().lower()
            try:
                validate_email(email)
            except ValidationError:
                raise CommandError(f"Invalid email address: {email!r}")
            invites.append((full_name.strip(), email))

        tenant_email = options.get("tenant_email") or invites[0][1]

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN — no changes will be made.\n"))

        with transaction.atomic():
            # ---- Tenant -----------------------------------------------------
            tenant = Tenant.objects.filter(name__iexact=tenant_name).first()
            if tenant:
                self.stdout.write(f"Tenant exists: {tenant.name} ({tenant.tenant_id})")
                if tenant.subscription_type == "none":
                    tenant.subscription_type = agents
                    tenant.subscription_status = "active"
                    if not tenant.subscription_start:
                        tenant.subscription_start = timezone.now()
                    if not dry_run:
                        tenant.save(update_fields=[
                            "subscription_type", "subscription_status", "subscription_start",
                        ])
                    self.stdout.write(self.style.SUCCESS(f"  ✓ Subscription upgraded to '{agents}' (active)"))
            else:
                tenant = Tenant(
                    name=tenant_name,
                    email=tenant_email,
                    subscription_type=agents,
                    subscription_status="active",
                    subscription_start=timezone.now(),
                )
                if not dry_run:
                    tenant.save()
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Tenant created: {tenant_name} (subscription: {agents}, active)"
                ))

            # ---- Users ------------------------------------------------------
            for full_name, email in invites:
                existing = UserProfile.objects.filter(email=email).first()

                if existing:
                    self.stdout.write(f"User exists: {email}")
                    if existing.tenant_id is None:
                        if not dry_run:
                            existing.tenant = tenant
                            existing.save(update_fields=["tenant"])
                        self.stdout.write(self.style.SUCCESS(f"  ✓ Assigned to tenant '{tenant.name}'"))
                    elif existing.tenant_id != tenant.pk:
                        self.stdout.write(self.style.WARNING(
                            f"  ⚠ Already belongs to another tenant — left unchanged."
                        ))
                    if resend and not dry_run:
                        self._send_invite(existing, invite_hours)
                        self.stdout.write(self.style.SUCCESS("  ✓ Set-password email re-sent"))
                    continue

                if dry_run:
                    self.stdout.write(self.style.SUCCESS(
                        f"  ✓ Would create {email} ({full_name or 'no name'}), "
                        f"pre-verified, no password, tenant '{tenant.name}', and email an invite."
                    ))
                    continue

                profile = UserProfile(
                    email=email,
                    full_name=full_name,
                    tenant=tenant,
                    email_confirmed=True,       # invited by an admin — no verification round-trip
                    password=make_password(None),  # unusable until they set their own
                )
                profile.save()
                self._send_invite(profile, invite_hours)
                self.stdout.write(self.style.SUCCESS(
                    f"  ✓ Created {email} and sent set-password email"
                ))

            if dry_run:
                # Roll everything back just in case (nothing should have been saved).
                transaction.set_rollback(True)

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Done."))
        if not dry_run:
            self.stdout.write(
                f"Each invitee has {invite_hours}h to set a password. If a link expires, "
                'they can use "Forgot password" on the login page with the same email.'
            )

    # ---------------------------------------------------------------------- #
    # Invite email                                                            #
    # ---------------------------------------------------------------------- #

    def _send_invite(self, profile: UserProfile, invite_hours: int):
        token = profile.generate_password_reset_token()
        # generate_password_reset_token() defaults to a 1h expiry — extend for invites.
        profile.password_reset_token_expires_at = timezone.now() + timedelta(hours=invite_hours)
        profile.save(update_fields=["password_reset_token_expires_at"])

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        set_url = f"{frontend_url}/reset-password?token={token}"

        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#f9f9f9;border-radius:10px;overflow:hidden;">
          <div style="background:#0f172a;padding:28px 32px;">
            <h1 style="color:#ffffff;margin:0;font-size:22px;letter-spacing:1px;">SIA</h1>
          </div>
          <div style="padding:36px 32px;background:#ffffff;">
            <h2 style="color:#0f172a;margin-top:0;">You've been invited</h2>
            <p style="color:#555;line-height:1.6;">An account has been created for you on SIA.
            Click the button below to choose your password and activate it.
            This link expires in <strong>{invite_hours} hours</strong>.</p>
            <div style="text-align:center;margin:32px 0;">
              <a href="{set_url}" style="background:#0f172a;color:#ffffff;padding:14px 32px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:15px;">Set your password</a>
            </div>
            <p style="color:#999;font-size:12px;">If the link expires, use "Forgot password" on the login page with this email address. If you weren't expecting this invitation, you can ignore this email.</p>
          </div>
          <div style="background:#f1f5f9;padding:16px 32px;text-align:center;">
            <p style="color:#aaa;font-size:11px;margin:0;">© 2026 SIA. All rights reserved.</p>
          </div>
        </div>
        """
        text = (
            "You've been invited to SIA.\n\n"
            f"Set your password here: {set_url}\n\n"
            f"This link expires in {invite_hours} hours. If it expires, use "
            '"Forgot password" on the login page with this email address.'
        )
        msg = EmailMultiAlternatives(
            subject="Your SIA account — set your password",
            body=text,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[profile.email],
        )
        msg.attach_alternative(html, "text/html")
        msg.send(fail_silently=False)
