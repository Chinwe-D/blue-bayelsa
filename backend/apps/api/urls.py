"""
API routes.

  /api/v1/public/...  anyone; published / active data only
  /api/v1/auth/...    login, logout, current user
  /api/v1/admin/...   staff only; every endpoint checks a role capability
"""

from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounts import views as auth_views
from apps.audit.views import AuditLogViewSet
from apps.geo import views as geo
from apps.governance.views import DataSourceViewSet

public = DefaultRouter()
public.register("lgas", geo.PublicLGAViewSet, basename="public-lga")
public.register("communities", geo.PublicCommunityViewSet, basename="public-community")
public.register("sectors", geo.PublicSectorViewSet, basename="public-sector")
public.register("activities", geo.PublicActivityViewSet, basename="public-activity")

admin = DefaultRouter()
admin.register("lgas", geo.AdminLGAViewSet, basename="admin-lga")
admin.register("communities", geo.AdminCommunityViewSet, basename="admin-community")
admin.register("sectors", geo.AdminSectorViewSet, basename="admin-sector")
admin.register("activities", geo.AdminActivityViewSet, basename="admin-activity")
admin.register("data-sources", DataSourceViewSet, basename="admin-datasource")
admin.register("audit-log", AuditLogViewSet, basename="admin-auditlog")

auth = [
    path("csrf/", auth_views.CsrfView.as_view(), name="auth-csrf"),
    path("login/", auth_views.LoginView.as_view(), name="auth-login"),
    path("logout/", auth_views.LogoutView.as_view(), name="auth-logout"),
    path("me/", auth_views.MeView.as_view(), name="auth-me"),
]

urlpatterns = [
    path("public/", include(public.urls)),
    path("admin/", include(admin.urls)),
    path("auth/", include(auth)),
]
