from django.db import transaction
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from users.serializers import (
    ChangePasswordSerializer,
    LoginSerializer,
    ProfileSerializer,
    RegisterSerializer,
)
from users.tasks import send_activation_key_email


class RegisterAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=RegisterSerializer,
        responses={201: ProfileSerializer},
        description="Регистрация пользователя. После регистрации создаётся ключ активации и отправляется письмо.",
    )
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user = serializer.save()

            transaction.on_commit(lambda: send_activation_key_email.delay(user.id))

        return Response(
            {
                "message": "Письмо с ключом отправлено на почту.",
                "user": ProfileSerializer(user).data,
            },
            status=status.HTTP_201_CREATED,
        )


class LoginAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=LoginSerializer,
        responses={200, ProfileSerializer},
        description="Авторизация пользователя по email и паролю. Возвращает token.",
    )
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]
        token, _ = Token.objects.get_or_create(user=user)

        return Response(
            {
                "token": token.key,
                "user": ProfileSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class ProfileAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = ProfileSerializer(request.user)

        return Response(
            serializer.data,
            status=status.HTTP_200_OK,
        )


class RefreshActivationKeyAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: ProfileSerializer},
        description="Обновляет ключ активации пользователя и отправляет его на почту.",
    )
    def post(self, request):
        request.user.refresh_activation_key()

        send_activation_key_email.delay(request.user.id)

        return Response(
            {
                "message": "Новый ключ создан и отправлен на почту.",
                "user": ProfileSerializer(request.user).data,
            },
            status=status.HTTP_200_OK,
        )


class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=ChangePasswordSerializer,
        responses={200: None},
        description="Смена пароля пользователя.",
    )
    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "message": "Пароль успешно изменён.",
            },
            status=status.HTTP_200_OK,
        )
