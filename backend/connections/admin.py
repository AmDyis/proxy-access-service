from django.contrib import admin

from connections.models import ConnectionSession


@admin.register(ConnectionSession)
class ConnectionSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "virtual_machine",
        "status",
        "token_short",
        "created_at",
        "disconnected_at",
    )

    list_filter = (
        "status",
        "created_at",
        "disconnected_at",
    )

    search_fields = (
        "user__email",
        "virtual_machine__name",
        "virtual_machine__host",
        "token",
    )

    readonly_fields = (
        "token",
        "created_at",
        "updated_at",
        "disconnected_at",
    )

    @admin.display(description="Token")
    def token_short(self, obj):
        if not obj.token:
            return "-"

        return f"{obj.token[:8]}...{obj.token[-6:]}"
