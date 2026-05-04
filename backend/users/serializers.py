from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from users.models import User


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate_email(self, value):
        email = value.lower().strip()

        if User.objects.filter(email=email).exists():
            raise serializers.ValidationError(
                "Пользователь с таким email уже существует."
            )

        return email

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError(
                {"password_confirm": "Пароли не совпадают."}
            )

        validate_password(attrs["password"])

        return attrs

    def create(self, validated_data):
        validated_data.pop("password_confirm")

        user = User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
        )

        user.refresh_activation_key()

        return user


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs["email"].lower().strip()
        password = attrs["password"]

        user = authenticate(
            username=email,
            password=password,
        )

        if user is None:
            raise serializers.ValidationError("Неверный email или пароль.")

        if not user.is_active:
            raise serializers.ValidationError("Пользователь отключён.")

        attrs["user"] = user
        return attrs


class ProfileSerializer(serializers.ModelSerializer):
    connection_status = serializers.SerializerMethodField()
    active_proxy = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            "id",
            "email",
            "activation_key",
            "activation_key_expires",
            "connection_status",
            "active_proxy",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_connection_status(self, obj):
        active_proxy = obj.assigned_virtual_machines.filter(
            is_active=True,
            current_user=obj,
        ).first()

        if active_proxy:
            return "connected"

        return "disconnected"

    def get_active_proxy(self, obj):
        active_proxy = obj.assigned_virtual_machines.filter(
            is_active=True,
            current_user=obj,
        ).first()

        if not active_proxy:
            return None

        return {
            "id": active_proxy.id,
            "name": active_proxy.name,
            "host": active_proxy.host,
            "port": active_proxy.port,
            "protocol": active_proxy.protocol,
            "last_used_at": active_proxy.last_used_at,
        }


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=8)
    new_password_confirm = serializers.CharField(write_only=True, min_length=8)

    def validate(self, attrs):
        user = self.context["request"].user

        if not user.check_password(attrs["old_password"]):
            raise serializers.ValidationError(
                {"old_password": "Старый пароль указан неверно."}
            )

        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError(
                {"new_password_confirm": "Новые пароли не совпадают."}
            )

        validate_password(attrs["new_password"], user=user)

        return attrs

    def save(self, **kwargs):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password", "updated_at"])
        return user
