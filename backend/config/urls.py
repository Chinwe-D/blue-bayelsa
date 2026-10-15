from django.conf import settings
from django.contrib import admin
from django.http import JsonResponse
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView


def health(request):
    return JsonResponse({"status": "ok"})


# The built-in Django admin is a technical fallback for the super-administrator only.
admin.site.has_permission = lambda request: request.user.is_active and request.user.is_superuser
admin.site.site_header = "Blue Bayelsa Invest – technical administration"

urlpatterns = [
    path("api/v1/", include("apps.api.urls")),
    path("api/health/", health),
    path("django-admin/", admin.site.urls),
]

if settings.DEBUG:
    urlpatterns += [
        path("api/v1/schema/", SpectacularAPIView.as_view(), name="schema"),
        path("api/v1/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="api-docs"),
    ]
