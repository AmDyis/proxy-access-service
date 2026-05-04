from django.conf import settings
from django.db import models


class VirtualMachine(models.Model):
    class Protocol(models.TextChoices):
        SOCKS5 = "socks5", "SOCKS5"
        HTTP = "http", "HTTP"
        HTTPS = "https", "HTTPS"

    name = models.CharField(max_length=100, unique=True)
    host = models.CharField(max_length=255)
    port = models.PositiveIntegerField()
    protocol = models.CharField(
        max_length=20,
        choices=Protocol.choices,
        default=Protocol.SOCKS5,
    )

    is_active = models.BooleanField(default=True)

    current_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_virtual_machines",
    )

    last_used_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Виртуальная машина"
        verbose_name_plural = "Виртуальные машины"
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.protocol}://{self.host}:{self.port})"

    @property
    def is_free(self):
        return self.is_active and self.current_user_id is None
