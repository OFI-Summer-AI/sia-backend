"""
Serializers for authentication endpoints.
"""

from rest_framework import serializers
from .models import UserProfile


# ------------------------------------------------------------------ #
# Request serializers                                                  #
# ------------------------------------------------------------------ #

class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(min_length=8, write_only=True)
    full_name = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_email(self, value):
        if UserProfile.objects.filter(email=value).exists():
            raise serializers.ValidationError("Email already registered.")
        return value.lower()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)


class TokenRefreshSerializer(serializers.Serializer):
    refresh_token = serializers.CharField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    token = serializers.CharField()
    new_password = serializers.CharField(min_length=8, write_only=True)


class ProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["full_name", "phone", "avatar_url"]


# ------------------------------------------------------------------ #
# Response serializers                                                  #
# ------------------------------------------------------------------ #

class TenantBriefSerializer(serializers.Serializer):
    """Compact tenant info embedded in user profile responses."""
    id = serializers.UUIDField(source="tenant_id")
    name = serializers.CharField()
    subscription_type = serializers.CharField()
    subscription_status = serializers.CharField()


class UserProfileSerializer(serializers.ModelSerializer):
    """Full profile — for the authenticated user's own /profile/ endpoint."""

    tenant = TenantBriefSerializer(read_only=True)
    can_access_mark = serializers.BooleanField(read_only=True)
    can_access_hr = serializers.BooleanField(read_only=True)
    accessible_agents = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "id", "email", "full_name", "phone", "avatar_url",
            "role", "is_active", "email_confirmed",
            "tenant",
            "can_access_mark", "can_access_hr", "accessible_agents",
            "last_login", "created_at", "updated_at",
        ]
        read_only_fields = fields

    def get_accessible_agents(self, obj):
        return obj.get_accessible_agents()


# ------------------------------------------------------------------ #
# Admin serializers                                                    #
# ------------------------------------------------------------------ #

class AdminUserListSerializer(serializers.ModelSerializer):
    """Compact user listing for the admin portal."""

    tenant = TenantBriefSerializer(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id", "email", "full_name", "role", "is_active",
            "email_confirmed", "tenant",
            "last_login", "created_at",
        ]


class AdminUserDetailSerializer(serializers.ModelSerializer):
    """Full user detail for the admin portal."""

    tenant = TenantBriefSerializer(read_only=True)
    can_access_mark = serializers.BooleanField(read_only=True)
    can_access_hr = serializers.BooleanField(read_only=True)

    class Meta:
        model = UserProfile
        fields = [
            "id", "email", "full_name", "phone", "avatar_url",
            "role", "is_active", "email_confirmed",
            "tenant",
            "can_access_mark", "can_access_hr",
            "last_login", "created_at", "updated_at",
        ]
        read_only_fields = fields


class AssignTenantSerializer(serializers.Serializer):
    """Body for PATCH /api/admin/users/<id>/tenant/"""

    tenant_id = serializers.UUIDField(required=False, allow_null=True)
