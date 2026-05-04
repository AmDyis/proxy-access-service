from django.urls import path

from users.views import (
    ChangePasswordAPIView,
    LoginAPIView,
    ProfileAPIView,
    RefreshActivationKeyAPIView,
    RegisterAPIView,
)

urlpatterns = [
    path("auth/register/", RegisterAPIView.as_view(), name="register"),
    path("auth/login/", LoginAPIView.as_view(), name="login"),
    path("profile/", ProfileAPIView.as_view(), name="profile"),
    path(
        "profile/refresh-key/",
        RefreshActivationKeyAPIView.as_view(),
        name="refresh-key",
    ),
    path(
        "profile/change-password/",
        ChangePasswordAPIView.as_view(),
        name="change-password",
    ),
]
