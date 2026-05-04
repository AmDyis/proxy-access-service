from django.urls import path

from connections.consumers import ConnectionStatusConsumer

websocket_urlpatterns = [
    path("ws/status/<int:user_id>/", ConnectionStatusConsumer.as_asgi()),
]
