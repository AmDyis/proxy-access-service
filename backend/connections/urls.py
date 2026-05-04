from django.urls import path

from connections.views import (
    ActivateKeyAPIView,
    DesktopDisconnectAPIView,
    DisconnectAPIView,
)

urlpatterns = [
    path("activate-key/", ActivateKeyAPIView.as_view(), name="activate-key"),
    path("disconnect/", DisconnectAPIView.as_view(), name="disconnect"),
    path(
        "desktop/disconnect/",
        DesktopDisconnectAPIView.as_view(),
        name="desktop-disconnect",
    ),
]
