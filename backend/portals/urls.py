from django.urls import path

from .views import (
    PortalListView, PortalRunListView, PortalScrapeView, PortalSessionView,
)

urlpatterns = [
    path('', PortalListView.as_view(), name='portal-list'),
    path('runs/', PortalRunListView.as_view(), name='portal-runs'),
    path('<str:name>/session/', PortalSessionView.as_view(), name='portal-session'),
    path('<str:name>/scrape/', PortalScrapeView.as_view(), name='portal-scrape'),
]
