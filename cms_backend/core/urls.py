from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path

from rest_framework.authtoken.views import obtain_auth_token
from .views import LogoutView


urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.content.urls")),\
    
    path("api/login/", obtain_auth_token, name="api_login"),
    path("api/logout/", LogoutView.as_view(), name="api_logout"),
    
    path("api-auth/", include("rest_framework.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
