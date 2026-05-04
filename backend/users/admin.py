from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from users.models import User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    model = User

    list_display = (
        "id",
        "email",
        "is_active",
        "is_staff",
        "activation_key_short",
        "activation_key_expires",
        "connection_status",
        "active_proxies",
        "created_at",
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "created_at",
    )

    search_fields = (
        "email",
        "activation_key",
        "assigned_virtual_machines__name",
        "assigned_virtual_machines__host",
    )

    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Права доступа",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        (
            "Ключ активации",
            {
                "fields": (
                    "activation_key",
                    "activation_key_expires",
                    "activation_key_status",
                )
            },
        ),
        (
            "Текущее подключение",
            {
                "fields": (
                    "connection_status",
                    "active_proxies",
                )
            },
        ),
        (
            "Служебная информация",
            {
                "fields": (
                    "last_login",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    readonly_fields = (
        "created_at",
        "updated_at",
        "last_login",
        "activation_key_status",
        "connection_status",
        "active_proxies",
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
    )

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.prefetch_related("assigned_virtual_machines")

    @admin.display(description="Activation key")
    def activation_key_short(self, obj):
        if not obj.activation_key:
            return "Ключ использован / отсутствует"

        return f"{obj.activation_key[:8]}...{obj.activation_key[-6:]}"

    @admin.display(description="Статус ключа")
    def activation_key_status(self, obj):
        if obj.activation_key:
            return "Ключ создан и ожидает использования"

        return "Ключ отсутствует или уже использован"

    @admin.display(description="Статус подключения")
    def connection_status(self, obj):
        has_active_proxy = obj.assigned_virtual_machines.filter(
            is_active=True,
            current_user=obj,
        ).exists()

        if has_active_proxy:
            return "Подключён"

        return "Не подключён"

    @admin.display(description="Назначенные прокси")
    def active_proxies(self, obj):
        proxies = obj.assigned_virtual_machines.filter(
            is_active=True,
            current_user=obj,
        )

        if not proxies.exists():
            return "-"

        return ", ".join(
            f"{proxy.name} ({proxy.protocol}://{proxy.host}:{proxy.port})"
            for proxy in proxies
        )
