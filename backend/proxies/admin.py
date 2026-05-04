from django.contrib import admin

from proxies.models import VirtualMachine


@admin.register(VirtualMachine)
class VirtualMachineAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "host",
        "port",
        "protocol",
        "is_active",
        "is_free_status",
        "current_user_email",
        "last_used_at",
    )

    list_filter = (
        "protocol",
        "is_active",
        "current_user",
    )

    search_fields = (
        "name",
        "host",
        "current_user__email",
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_used_at",
        "is_free_status",
        "current_user_email",
    )

    fieldsets = (
        (
            "Прокси-сервер",
            {
                "fields": (
                    "name",
                    "host",
                    "port",
                    "protocol",
                    "is_active",
                )
            },
        ),
        (
            "Использование",
            {
                "fields": (
                    "current_user",
                    "current_user_email",
                    "is_free_status",
                    "last_used_at",
                )
            },
        ),
        (
            "Служебная информация",
            {
                "fields": (
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    @admin.display(description="Свободна")
    def is_free_status(self, obj):
        if obj.is_active and obj.current_user_id is None:
            return "Да"

        return "Нет"

    @admin.display(description="Текущий пользователь")
    def current_user_email(self, obj):
        if not obj.current_user:
            return "-"

        return obj.current_user.email
