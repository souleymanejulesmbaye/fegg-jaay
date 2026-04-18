"""URLs racine du projet Fëgg Jaay."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path("admin/", admin.site.urls),
    path("wa/", include("whatsapp.urls")),
    path("whatsapp/", include("whatsapp.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("", include("vitrine.urls")),
]

# En développement, servir les médias localement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
