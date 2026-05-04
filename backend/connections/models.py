import secrets

from django.conf import settings
from django.db import models


class ConnectionSession(models.Model):
    class Status(models.TextChoices):
        CONNECTED = "connected", "Connected"
        DISCONNECTED = "disconnected", "Disconnected"
        ERROR = "error", "Error"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="connection_sessions",
    )

    virtual_machine = models.ForeignKey(
        "proxies.VirtualMachine",
        on_delete=models.CASCADE,
        related_name="connection_sessions",
    )

    token = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.CONNECTED,
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    disconnected_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Сессия подключения"
        verbose_name_plural = "Сессии подключений"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.user.email} → {self.virtual_machine.name} [{self.status}]"

    @staticmethod
    def generate_unique_token():
        while True:
            token = secrets.token_hex(24)

            if not ConnectionSession.objects.filter(token=token).exists():
                return token

    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_unique_token()

        super().save(*args, **kwargs)
