"""URLs racine du projet Fëgg Jaay."""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from deploy_webhook import deploy_webhook

urlpatterns = [
    path("admin/", admin.site.urls),
    path("deploy/webhook/", deploy_webhook, name="deploy_webhook"),
    path("wa/", include("whatsapp.urls")),
    path("whatsapp/", include("whatsapp.urls")),
    path("dashboard/", include("dashboard.urls")),
    path("", include("vitrine.urls")),
]

# En développement, servir les médias localement
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
