from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from config.health import health

api_v1 = [
    path('auth/', include('accounts.urls')),
    path('profile/', include('profiles.urls')),
    path('resumes/', include('resumes.urls')),
    path('jobs/', include('jobs.urls')),
    path('ingestion/', include('ingestion.urls')),
    path('matching/', include('matching.urls')),
    path('notifications/', include('notifications.urls')),
    path('applications/', include('applications.urls')),
    path('networking/', include('networking.urls')),
    path('tailoring/', include('tailoring.urls')),
    path('agent/', include('agent.urls')),
    path('interview/', include('interview.urls')),
    path('credentials/', include('credentials.urls')),
    path('ext/', include('extension_api.urls')),
    path('vault/', include('vault.urls')),
    path('portals/', include('portals.urls')),
    path('billing/', include('billing.urls')),
]

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/health/', health, name='health'),
    path('api/v1/', include(api_v1)),
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger'),
]
