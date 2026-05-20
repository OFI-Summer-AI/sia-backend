"""
Authentication service — lógica local Django + SimpleJWT.
No hay dependencias externas de Supabase.
"""

import logging
from typing import Dict, Tuple

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import UserProfile
from .authentication import JWT_BLACKLIST_PREFIX

logger = logging.getLogger(__name__)


class AuthService:

    @staticmethod
    def register_user(email: str, password: str, full_name: str = "") -> Tuple[bool, Dict]:
        if UserProfile.objects.filter(email=email).exists():
            return False, {"error": "Email already registered."}

        profile = UserProfile(email=email, full_name=full_name)
        profile.set_password(password)
        profile.save()

        token = profile.generate_email_verification_token()
        AuthService._send_verification_email(email, token)

        return True, {
            "message": "Registration successful. Please verify your email before logging in.",
            "email": email,
        }

    @staticmethod
    def verify_email(token: str) -> Tuple[bool, Dict]:
        try:
            profile = UserProfile.objects.get(email_verification_token=token)
        except UserProfile.DoesNotExist:
            return False, {"error": "Invalid or expired verification token."}

        if profile.email_confirmed:
            return True, {"message": "Email already verified."}

        if profile.email_verification_token_expires_at < timezone.now():
            return False, {"error": "Verification token has expired. Please request a new one."}

        profile.email_confirmed = True
        profile.email_verification_token = None
        profile.email_verification_token_expires_at = None
        profile.save(update_fields=[
            "email_confirmed",
            "email_verification_token",
            "email_verification_token_expires_at",
        ])

        return True, {"message": "Email verified successfully. You can now log in."}

    @staticmethod
    def login_user(email: str, password: str) -> Tuple[bool, Dict]:
        try:
            profile = UserProfile.objects.select_related("tenant").get(email=email)
        except UserProfile.DoesNotExist:
            return False, {"error": "Invalid email or password."}

        if not profile.check_password(password):
            return False, {"error": "Invalid email or password."}

        if not profile.is_active:
            return False, {"error": "Account is deactivated. Contact support."}

        if not profile.email_confirmed:
            return False, {
                "error": "Email not verified. Please check your inbox and confirm your account.",
                "code": "email_not_verified",
            }

        refresh = RefreshToken()
        refresh["user_id"] = str(profile.id)
        refresh["email"] = profile.email
        refresh["role"] = profile.role

        profile.record_login()

        access_lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]

        return True, {
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "expires_in": int(access_lifetime.total_seconds()),
            "user": {
                "id": str(profile.id),
                "email": profile.email,
                "full_name": profile.full_name,
                "role": profile.role,
                "subscription_type": profile.tenant.subscription_type if profile.tenant else None,
                "subscription_status": profile.tenant.subscription_status if profile.tenant else None,
                "can_access_mark": profile.can_access_mark,
                "can_access_hr": profile.can_access_hr,
            },
        }

    @staticmethod
    def refresh_token(refresh_token_str: str) -> Tuple[bool, Dict]:
        try:
            refresh = RefreshToken(refresh_token_str)
            access_lifetime = settings.SIMPLE_JWT["ACCESS_TOKEN_LIFETIME"]
            return True, {
                "access_token": str(refresh.access_token),
                "refresh_token": str(refresh),
                "expires_in": int(access_lifetime.total_seconds()),
            }
        except TokenError as exc:
            return False, {"error": str(exc)}

    @staticmethod
    def logout_user(access_token: str) -> bool:
        """Blacklist the JWT JTI in Redis so it cannot be reused."""
        from django.core.cache import cache
        from rest_framework_simplejwt.tokens import AccessToken

        try:
            token = AccessToken(access_token)
            jti = token.get("jti")
            exp = token.get("exp")
            if jti and exp:
                remaining = exp - int(timezone.now().timestamp())
                if remaining > 0:
                    cache.set(f"{JWT_BLACKLIST_PREFIX}{jti}", True, timeout=remaining)
        except TokenError:
            pass
        return True

    @staticmethod
    def request_password_reset(email: str) -> Tuple[bool, Dict]:
        # Always return success to prevent email enumeration
        try:
            profile = UserProfile.objects.get(email=email)
        except UserProfile.DoesNotExist:
            return True, {}

        token = profile.generate_password_reset_token()
        AuthService._send_password_reset_email(email, token)
        return True, {}

    @staticmethod
    def confirm_password_reset(token: str, new_password: str) -> Tuple[bool, Dict]:
        try:
            profile = UserProfile.objects.get(password_reset_token=token)
        except UserProfile.DoesNotExist:
            return False, {"error": "Invalid or expired reset token."}

        if profile.password_reset_token_expires_at < timezone.now():
            return False, {"error": "Reset token has expired. Please request a new one."}

        profile.set_password(new_password)
        profile.password_reset_token = None
        profile.password_reset_token_expires_at = None
        profile.save(update_fields=[
            "password",
            "password_reset_token",
            "password_reset_token_expires_at",
        ])

        return True, {"message": "Password reset successfully. You can now log in."}

    # ------------------------------------------------------------------ #
    # Email helpers                                                          #
    # ------------------------------------------------------------------ #

    @staticmethod
    def _send_verification_email(email: str, token: str):
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        verify_url = f"{frontend_url}/verify-email?token={token}"
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#f9f9f9;border-radius:10px;overflow:hidden;">
          <div style="background:#0f172a;padding:28px 32px;">
            <h1 style="color:#ffffff;margin:0;font-size:22px;letter-spacing:1px;">SIA</h1>
          </div>
          <div style="padding:36px 32px;background:#ffffff;">
            <h2 style="color:#0f172a;margin-top:0;">Verify your email</h2>
            <p style="color:#555;line-height:1.6;">Click the button below to confirm your account. This link expires in <strong>24 hours</strong>.</p>
            <div style="text-align:center;margin:32px 0;">
              <a href="{verify_url}" style="background:#0f172a;color:#ffffff;padding:14px 32px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:15px;">Verify account</a>
            </div>
            <p style="color:#999;font-size:12px;">If you did not create a SIA account, you can safely ignore this email.</p>
          </div>
          <div style="background:#f1f5f9;padding:16px 32px;text-align:center;">
            <p style="color:#aaa;font-size:11px;margin:0;">© 2026 SIA. All rights reserved.</p>
          </div>
        </div>
        """
        text = f"Verify your SIA account:\n\n{verify_url}\n\nThis link expires in 24 hours."
        try:
            msg = EmailMultiAlternatives(
                subject="Verify your SIA account",
                body=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            msg.attach_alternative(html, "text/html")
            msg.send(fail_silently=False)
        except Exception as exc:
            logger.error("Failed to send verification email to %s: %s", email, exc)

    @staticmethod
    def _send_password_reset_email(email: str, token: str):
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000")
        reset_url = f"{frontend_url}/reset-password?token={token}"
        html = f"""
        <div style="font-family:Arial,sans-serif;max-width:520px;margin:0 auto;background:#f9f9f9;border-radius:10px;overflow:hidden;">
          <div style="background:#0f172a;padding:28px 32px;">
            <h1 style="color:#ffffff;margin:0;font-size:22px;letter-spacing:1px;">SIA</h1>
          </div>
          <div style="padding:36px 32px;background:#ffffff;">
            <h2 style="color:#0f172a;margin-top:0;">Reset your password</h2>
            <p style="color:#555;line-height:1.6;">We received a request to reset your password. Click the button below. This link expires in <strong>1 hour</strong>.</p>
            <div style="text-align:center;margin:32px 0;">
              <a href="{reset_url}" style="background:#0f172a;color:#ffffff;padding:14px 32px;border-radius:6px;text-decoration:none;font-weight:bold;font-size:15px;">Reset password</a>
            </div>
            <p style="color:#999;font-size:12px;">If you did not request this, you can safely ignore this email. Your password will not change.</p>
          </div>
          <div style="background:#f1f5f9;padding:16px 32px;text-align:center;">
            <p style="color:#aaa;font-size:11px;margin:0;">© 2025 SIA. All rights reserved.</p>
          </div>
        </div>
        """
        text = f"Reset your SIA password:\n\n{reset_url}\n\nThis link expires in 1 hour."
        try:
            msg = EmailMultiAlternatives(
                subject="Reset your SIA password",
                body=text,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[email],
            )
            msg.attach_alternative(html, "text/html")
            msg.send(fail_silently=False)
        except Exception as exc:
            logger.error("Failed to send password reset email to %s: %s", email, exc)
