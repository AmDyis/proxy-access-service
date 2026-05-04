import json

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from proxies.models import VirtualMachine
from users.models import User


class ConnectionStatusConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user_id = self.scope["url_route"]["kwargs"]["user_id"]
        self.group_name = f"user_status_{self.user_id}"

        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name,
        )

        await self.accept()

        initial_status = await self.get_initial_status(self.user_id)

        await self.send(
            text_data=json.dumps(
                initial_status,
                ensure_ascii=False,
                default=str,
            )
        )

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(
            self.group_name,
            self.channel_name,
        )

    async def connection_status(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    "status": event.get("status"),
                    "detail": event.get("detail"),
                    "proxy": event.get("proxy"),
                },
                ensure_ascii=False,
                default=str,
            )
        )

    @database_sync_to_async
    def get_initial_status(self, user_id):
        user_exists = User.objects.filter(id=user_id).exists()

        if not user_exists:
            return {
                "status": "error",
                "detail": "Пользователь не найден.",
                "proxy": None,
            }

        active_proxy = VirtualMachine.objects.filter(
            current_user_id=user_id,
            is_active=True,
        ).first()

        if active_proxy:
            return {
                "status": "connected",
                "detail": "Пользователь уже подключён к прокси.",
                "proxy": {
                    "id": active_proxy.id,
                    "name": active_proxy.name,
                    "host": active_proxy.host,
                    "port": active_proxy.port,
                    "protocol": active_proxy.protocol,
                    "last_used_at": active_proxy.last_used_at,
                },
            }

        return {
            "status": "disconnected",
            "detail": "У пользователя нет активного подключения.",
            "proxy": None,
        }
