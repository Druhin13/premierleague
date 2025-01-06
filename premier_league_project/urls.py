"""
URL configuration for premier_league_project project.
"""

from django.contrib import admin
from django.urls import path, include
from league_app.views import homepage
from rest_framework import permissions
from drf_yasg.views import get_schema_view
from drf_yasg import openapi

schema_view = get_schema_view(
    openapi.Info(
        title="Premier League API",
        default_version='v1',
        description="API for Premier League Data",
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    path('admin/', admin.site.urls), # Django admin
    path('api/', include('league_app.urls')),  # Delegate to app-level urls.py
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'), # Swagger UI
    path('', homepage, name='homepage'),  # Homepage
]
