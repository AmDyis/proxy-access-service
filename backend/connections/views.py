from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db import transaction
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from proxies.models import VirtualMachine
from proxies.serializers import ProxyConnectionSerializer
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from users.models import User

from connections.models import ConnectionSession
from connections.serializers import (
    ActivateKeySerializer,
    DisconnectBySessionSerializer,
)


def send_connection_status(user_id, status_value, detail, proxy=None):
    channel_layer = get_channel_layer()

    if channel_layer is None:
        return

    async_to_sync(channel_layer.group_send)(
        f"user_status_{user_id}",
        {
            "type": "connection_status",
            "status": status_value,
            "detail": detail,
            "proxy": proxy,
        },
    )


class ActivateKeyAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=ActivateKeySerializer,
        responses={200: ProxyConnectionSerializer},
        description="Активация одноразового ключа. Если ключ валиден, пользователю назначается свободная виртуальная машина.",
    )
    def post(self, request):
        serializer = ActivateKeySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        activation_key = serializer.validated_data["activation_key"].strip()

        with transaction.atomic():
            user = (
                User.objects.select_for_update()
                .filter(activation_key=activation_key)
                .first()
            )

            if user is None:
                return Response(
                    {
                        "status": "error",
                        "detail": "Ключ активации не найден или уже был использован.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if not user.is_activation_key_valid(activation_key):
                return Response(
                    {
                        "status": "error",
                        "detail": "Ключ активации недействителен или истёк.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            now = timezone.now()

            # Закрываем старые активные сессии пользователя.
            ConnectionSession.objects.filter(
                user=user,
                status=ConnectionSession.Status.CONNECTED,
            ).update(
                status=ConnectionSession.Status.DISCONNECTED,
                disconnected_at=now,
                updated_at=now,
            )

            # Освобождаем старые виртуалки пользователя.
            VirtualMachine.objects.filter(
                current_user=user,
            ).update(
                current_user=None,
                updated_at=now,
            )

            virtual_machine = (
                VirtualMachine.objects.select_for_update()
                .filter(
                    is_active=True,
                    current_user__isnull=True,
                )
                .order_by("id")
                .first()
            )

            if virtual_machine is None:
                send_connection_status(
                    user_id=user.id,
                    status_value="no_free_vms",
                    detail="Все прокси заняты. Попробуйте позже.",
                    proxy=None,
                )

                return Response(
                    {
                        "status": "no_free_vms",
                        "detail": "Все прокси заняты. Попробуйте позже.",
                    },
                    status=status.HTTP_503_SERVICE_UNAVAILABLE,
                )

            virtual_machine.current_user = user
            virtual_machine.last_used_at = now
            virtual_machine.save(
                update_fields=[
                    "current_user",
                    "last_used_at",
                    "updated_at",
                ]
            )

            session = ConnectionSession.objects.create(
                user=user,
                virtual_machine=virtual_machine,
                status=ConnectionSession.Status.CONNECTED,
            )

            user.clear_activation_key()

        proxy_data = ProxyConnectionSerializer(virtual_machine).data

        send_connection_status(
            user_id=user.id,
            status_value="connected",
            detail="Прокси успешно назначен пользователю.",
            proxy=proxy_data,
        )

        return Response(
            {
                "status": "connected",
                "user_id": user.id,
                "connection_token": session.token,
                "proxy": proxy_data,
            },
            status=status.HTTP_200_OK,
        )


class DisconnectAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        request=None,
        responses={200: None},
        description="Отключение авторизованного пользователя от назначенного прокси. Освобождает виртуальную машину.",
    )
    def post(self, request):
        user = request.user

        with transaction.atomic():
            assigned_vms = list(
                VirtualMachine.objects.select_for_update().filter(
                    current_user=user,
                )
            )

            if not assigned_vms:
                return Response(
                    {
                        "status": "disconnected",
                        "detail": "У пользователя нет активного подключения.",
                    },
                    status=status.HTTP_200_OK,
                )

            released_proxies = [
                ProxyConnectionSerializer(vm).data for vm in assigned_vms
            ]

            now = timezone.now()

            for vm in assigned_vms:
                vm.current_user = None
                vm.save(
                    update_fields=[
                        "current_user",
                        "updated_at",
                    ]
                )

            ConnectionSession.objects.filter(
                user=user,
                status=ConnectionSession.Status.CONNECTED,
            ).update(
                status=ConnectionSession.Status.DISCONNECTED,
                disconnected_at=now,
                updated_at=now,
            )

        send_connection_status(
            user_id=user.id,
            status_value="disconnected",
            detail="Пользователь отключён от прокси.",
            proxy=None,
        )

        return Response(
            {
                "status": "disconnected",
                "detail": "Пользователь отключён от прокси.",
                "released_proxies": released_proxies,
            },
            status=status.HTTP_200_OK,
        )


class DesktopDisconnectAPIView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        request=DisconnectBySessionSerializer,
        responses={200: None},
        description="Отключение desktop-клиента по connection_token. Освобождает назначенную виртуальную машину.",
    )
    def post(self, request):
        serializer = DisconnectBySessionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        connection_token = serializer.validated_data["connection_token"].strip()

        with transaction.atomic():
            session = (
                ConnectionSession.objects.select_for_update()
                .select_related("user", "virtual_machine")
                .filter(
                    token=connection_token,
                    status=ConnectionSession.Status.CONNECTED,
                )
                .first()
            )

            if session is None:
                return Response(
                    {
                        "status": "error",
                        "detail": "Активная сессия подключения не найдена.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            user = session.user
            virtual_machine = session.virtual_machine
            released_proxy = ProxyConnectionSerializer(virtual_machine).data

            if virtual_machine.current_user_id == user.id:
                virtual_machine.current_user = None
                virtual_machine.save(
                    update_fields=[
                        "current_user",
                        "updated_at",
                    ]
                )

            now = timezone.now()
            session.status = ConnectionSession.Status.DISCONNECTED
            session.disconnected_at = now
            session.save(
                update_fields=[
                    "status",
                    "disconnected_at",
                    "updated_at",
                ]
            )

        send_connection_status(
            user_id=user.id,
            status_value="disconnected",
            detail="Desktop-клиент отключился от прокси.",
            proxy=None,
        )

        return Response(
            {
                "status": "disconnected",
                "detail": "Desktop-клиент отключился от прокси.",
                "released_proxy": released_proxy,
            },
            status=status.HTTP_200_OK,
        )
