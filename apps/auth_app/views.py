"""
Authentication views — register, login, logout, refresh, profile, password reset.
"""

import logging
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from .models import UserProfile
from .serializers import (
    RegisterSerializer, LoginSerializer, TokenRefreshSerializer,
    UserProfileSerializer, ProfileUpdateSerializer,
    PasswordResetConfirmSerializer,
)
from .services import AuthService

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Registration & Login                                                  #
# ------------------------------------------------------------------ #

@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    """
    Register a new user account.

    Body: { "email", "password", "full_name" (optional) }
    Sends a verification email; the user must verify before logging in.
    """
    serializer = RegisterSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data
    success, result = AuthService.register_user(
        email=data["email"],
        password=data["password"],
        full_name=data.get("full_name", ""),
    )

    if not success:
        return Response(
            {"success": False, "error": result.get("error", "Registration failed")},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response(
        {"success": True, "message": result["message"]},
        status=status.HTTP_201_CREATED,
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def verify_email(request):
    """
    Verify email address using the token sent by email.

    Query param: ?token=<token>
    """
    token = request.query_params.get("token", "").strip()
    if not token:
        return Response(
            {"success": False, "error": "Token is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    success, result = AuthService.verify_email(token)
    if not success:
        return Response(
            {"success": False, "error": result["error"]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({"success": True, "message": result["message"]})


@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """
    Login with email + password.

    Body: { "email", "password" }
    Returns: { access_token, refresh_token, expires_in, user }
    """
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data
    success, result = AuthService.login_user(
        email=data["email"], password=data["password"]
    )

    if not success:
        return Response(
            {"success": False, "error": result.get("error", "Login failed")},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    return Response({"success": True, "data": result})


@api_view(["POST"])
@permission_classes([AllowAny])
def refresh_token(request):
    """
    Exchange a refresh token for a new access token.

    Body: { "refresh_token" }
    """
    serializer = TokenRefreshSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    success, result = AuthService.refresh_token(serializer.validated_data["refresh_token"])
    if not success:
        return Response(
            {"success": False, "error": result.get("error", "Token refresh failed")},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    return Response({
        "success": True,
        "data": {
            "access_token": result.get("access_token"),
            "refresh_token": result.get("refresh_token"),
            "expires_in": result.get("expires_in"),
        },
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Blacklist the current access token so it cannot be reused.
    The client must also discard its local tokens.
    """
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    access_token = auth_header[7:].strip() if auth_header.startswith("Bearer ") else ""

    AuthService.logout_user(access_token)
    return Response({"success": True, "message": "Logged out successfully."})


# ------------------------------------------------------------------ #
# Session                                                               #
# ------------------------------------------------------------------ #

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def validate_session(request):
    """Return minimal user info confirming the token is still valid."""
    profile: UserProfile = request.user
    return Response({
        "success": True,
        "data": {
            "valid": True,
            "user": {
                "id": str(profile.id),
                "email": profile.email,
                "role": profile.role,
                "can_access_mark": profile.can_access_mark,
                "can_access_hr": profile.can_access_hr,
            },
        },
    })


# ------------------------------------------------------------------ #
# Profile                                                               #
# ------------------------------------------------------------------ #

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def profile(request):
    """Return the authenticated user's full profile."""
    serializer = UserProfileSerializer(request.user)
    return Response({"success": True, "data": serializer.data})


@api_view(["PATCH"])
@permission_classes([IsAuthenticated])
def update_profile(request):
    """
    Update editable profile fields.

    Body (all optional): { "full_name", "phone", "avatar_url" }
    """
    serializer = ProfileUpdateSerializer(
        request.user, data=request.data, partial=True
    )
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )
    serializer.save()
    return Response({
        "success": True,
        "message": "Profile updated.",
        "data": UserProfileSerializer(request.user).data,
    })


# ------------------------------------------------------------------ #
# Password reset                                                        #
# ------------------------------------------------------------------ #

@api_view(["POST"])
@permission_classes([AllowAny])
def request_password_reset(request):
    """
    Send a password-reset email.

    Body: { "email" }
    Always returns 200 to prevent email enumeration.
    """
    email = request.data.get("email", "").strip().lower()
    if email:
        AuthService.request_password_reset(email)

    return Response({
        "success": True,
        "message": "If an account with that email exists, a reset link has been sent.",
    })


@api_view(["POST"])
@permission_classes([AllowAny])
def confirm_password_reset(request):
    """
    Confirm a password reset using the token from the email.

    Body: { "token", "new_password" }
    """
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"success": False, "errors": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST,
        )

    data = serializer.validated_data
    success, result = AuthService.confirm_password_reset(
        token=data["token"],
        new_password=data["new_password"],
    )

    if not success:
        return Response(
            {"success": False, "error": result["error"]},
            status=status.HTTP_400_BAD_REQUEST,
        )

    return Response({"success": True, "message": result["message"]})
