"""
DRF authentication class using SimpleJWT tokens.

Returns UserProfile as request.user. Django's auth.User is never involved.
"""

import logging
from django.core.cache import cache
from rest_framework import authentication, exceptions
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError

from .models import UserProfile

logger = logging.getLogger(__name__)

JWT_BLACKLIST_PREFIX = "jwt_blacklist:"


class UserProfileJWTAuthentication(authentication.BaseAuthentication):
    """
    Authenticates Bearer JWT tokens issued by this backend (SimpleJWT).

    On success sets:
      request.user = UserProfile instance
      request.auth = validated AccessToken
    """

    def authenticate(self, request):
        auth_header = authentication.get_authorization_header(request).decode("utf-8")

        if not auth_header or not auth_header.startswith("Bearer "):
            return None

        token = auth_header[7:].strip()
        if not token:
            return None

        # JWTs always have exactly two dots. API keys do not — skip them here.
        if token.count(".") != 2:
            return None

        try:
            validated_token = AccessToken(token)
        except TokenError as exc:
            raise exceptions.AuthenticationFailed(str(exc))

        # Check Redis blacklist (populated on logout)
        jti = validated_token.get("jti")
        if jti and cache.get(f"{JWT_BLACKLIST_PREFIX}{jti}"):
            raise exceptions.AuthenticationFailed("Token has been revoked.")

        user_id = validated_token.get("user_id")
        if not user_id:
            raise exceptions.AuthenticationFailed("Invalid token: missing user_id")

        try:
            profile = UserProfile.objects.select_related("tenant").get(id=user_id)
        except UserProfile.DoesNotExist:
            raise exceptions.AuthenticationFailed("User not found.")

        if not profile.is_active:
            raise exceptions.AuthenticationFailed("User account is deactivated.")

        return (profile, validated_token)

    def authenticate_header(self, request):
        return "Bearer"
