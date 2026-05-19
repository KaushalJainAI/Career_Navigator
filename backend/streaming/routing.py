from django.urls import re_path

from .consumers import InterviewConsumer, NotificationsConsumer

websocket_urlpatterns = [
    re_path(r'^ws/notifications/$', NotificationsConsumer.as_asgi()),
    re_path(r'^ws/interview/(?P<session_id>\d+)/$', InterviewConsumer.as_asgi()),
]
