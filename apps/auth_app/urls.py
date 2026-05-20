"""
URL configuration for auth_app.
"""

from django.urls import path
from . import views, views_admin

urlpatterns = [
    # ------------------------------------------------------------------ #
    # Public auth endpoints                                                 #
    # ------------------------------------------------------------------ #
    path("register/", views.register, name="auth-register"),
    path("verify-email/", views.verify_email, name="auth-verify-email"),
    path("login/", views.login, name="auth-login"),
    path("refresh/", views.refresh_token, name="auth-refresh"),
    path("password/reset/", views.request_password_reset, name="auth-password-reset"),
    path("password/reset/confirm/", views.confirm_password_reset, name="auth-password-reset-confirm"),

    # ------------------------------------------------------------------ #
    # Authenticated user endpoints                                          #
    # ------------------------------------------------------------------ #
    path("logout/", views.logout, name="auth-logout"),
    path("session/validate/", views.validate_session, name="auth-validate-session"),
    path("profile/", views.profile, name="auth-profile"),
    path("profile/update/", views.update_profile, name="auth-update-profile"),

    # ------------------------------------------------------------------ #
    # Admin portal — all require IsSuperAdmin                              #
    # ------------------------------------------------------------------ #

    # Users
    path("admin/users/", views_admin.AdminUserListView.as_view(), name="admin-user-list"),
    path("admin/users/<uuid:user_id>/", views_admin.AdminUserDetailView.as_view(), name="admin-user-detail"),
    path("admin/users/<uuid:user_id>/status/", views_admin.AdminUserStatusView.as_view(), name="admin-user-status"),
    path("admin/users/<uuid:user_id>/tenant/", views_admin.AdminUserAssignTenantView.as_view(), name="admin-user-tenant"),

    # Tenants
    path("admin/tenants/", views_admin.AdminTenantListView.as_view(), name="admin-tenant-list"),
    path("admin/tenants/<uuid:tenant_id>/", views_admin.AdminTenantDetailView.as_view(), name="admin-tenant-detail"),

    # Agent configs (per tenant)
    path("admin/tenants/<uuid:tenant_id>/agent-configs/", views_admin.AdminAgentConfigView.as_view(), name="admin-agent-config-list"),
    path("admin/tenants/<uuid:tenant_id>/agent-configs/<str:agent_type>/", views_admin.AdminAgentConfigView.as_view(), name="admin-agent-config-detail"),

    # API keys (per tenant)
    path("admin/tenants/<uuid:tenant_id>/keys/", views_admin.AdminTenantAPIKeyView.as_view(), name="admin-apikey-list"),
    path("admin/tenants/<uuid:tenant_id>/keys/<uuid:key_id>/revoke/", views_admin.AdminTenantAPIKeyRevokeView.as_view(), name="admin-apikey-revoke"),

    # Dashboard
    path("admin/stats/", views_admin.AdminStatsView.as_view(), name="admin-stats"),
    path("admin/logs/", views_admin.AdminLogsView.as_view(), name="admin-logs"),
]
