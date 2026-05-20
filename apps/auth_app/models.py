import uuid
import secrets
from datetime import timedelta

from django.db import models
from django.core.validators import EmailValidator
from django.contrib.auth.hashers import make_password, check_password as django_check_password
from django.utils import timezone


class UserProfile(models.Model):
    """
    Single user table. Handles all auth locally via Django + SimpleJWT.

    Access to agents is determined by the user's Tenant subscription:
      tenant.subscription_type in ['mark', 'both']  → can access Mark's Agent
      tenant.subscription_type in ['hr', 'both']    → can access HR Agent
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    email = models.EmailField(
        unique=True,
        validators=[EmailValidator()],
    )
    password = models.CharField(max_length=128)
    full_name = models.CharField(max_length=255, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    avatar_url = models.URLField(null=True, blank=True)

    ROLE_CHOICES = [
        ("super_admin", "Super Admin"),
        ("user", "User"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default="user")

    tenant = models.ForeignKey(
        "tenants.Tenant",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="members",
        help_text="Company/org this user belongs to",
    )

    is_active = models.BooleanField(default=True)
    email_confirmed = models.BooleanField(default=False)

    # Email verification
    email_verification_token = models.CharField(max_length=100, null=True, blank=True)
    email_verification_token_expires_at = models.DateTimeField(null=True, blank=True)

    # Password reset
    password_reset_token = models.CharField(max_length=100, null=True, blank=True)
    password_reset_token_expires_at = models.DateTimeField(null=True, blank=True)

    last_login = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # DRF compatibility — makes UserProfile work as request.user
    is_authenticated = True
    is_anonymous = False

    class Meta:
        db_table = "user_profiles"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["email"]),
            models.Index(fields=["role"]),
            models.Index(fields=["tenant"]),
        ]

    def __str__(self):
        return f"{self.email} ({self.role})"

    # ------------------------------------------------------------------ #
    # Password                                                              #
    # ------------------------------------------------------------------ #

    def set_password(self, raw_password: str):
        self.password = make_password(raw_password)

    def check_password(self, raw_password: str) -> bool:
        return django_check_password(raw_password, self.password)

    # ------------------------------------------------------------------ #
    # Email verification token                                              #
    # ------------------------------------------------------------------ #

    def generate_email_verification_token(self) -> str:
        token = secrets.token_urlsafe(48)
        self.email_verification_token = token
        self.email_verification_token_expires_at = timezone.now() + timedelta(hours=24)
        self.save(update_fields=[
            "email_verification_token",
            "email_verification_token_expires_at",
        ])
        return token

    # ------------------------------------------------------------------ #
    # Password reset token                                                  #
    # ------------------------------------------------------------------ #

    def generate_password_reset_token(self) -> str:
        token = secrets.token_urlsafe(48)
        self.password_reset_token = token
        self.password_reset_token_expires_at = timezone.now() + timedelta(hours=1)
        self.save(update_fields=[
            "password_reset_token",
            "password_reset_token_expires_at",
        ])
        return token

    # ------------------------------------------------------------------ #
    # Agent access helpers                                                  #
    # ------------------------------------------------------------------ #

    @property
    def can_access_mark(self) -> bool:
        return (
            self.is_active
            and self.tenant is not None
            and self.tenant.has_mark_agent_access
        )

    @property
    def can_access_hr(self) -> bool:
        return (
            self.is_active
            and self.tenant is not None
            and self.tenant.has_hr_agent_access
        )

    @property
    def is_super_admin(self) -> bool:
        return self.role == "super_admin"

    def get_accessible_agents(self) -> list:
        agents = []
        if self.can_access_mark:
            agents.append("mark")
        if self.can_access_hr:
            agents.append("hr")
        return agents

    def record_login(self):
        self.last_login = timezone.now()
        self.save(update_fields=["last_login"])
