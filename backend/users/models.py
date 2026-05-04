import secrets
from datetime import timedelta

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.db import models
from django.utils import timezone


class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")

        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)

        if password:
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True")

        return self.create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    activation_key = models.CharField(
        max_length=64,
        unique=True,
        null=True,
        blank=True,
    )
    activation_key_expires = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        verbose_name = "Пользователь"
        verbose_name_plural = "Пользователи"
        ordering = ["-created_at"]

    def __str__(self):
        return self.email

    @staticmethod
    def generate_unique_activation_key():
        while True:
            key = secrets.token_hex(16)

            if not User.objects.filter(activation_key=key).exists():
                return key

    def refresh_activation_key(self):
        self.activation_key = self.generate_unique_activation_key()
        self.activation_key_expires = timezone.now() + timedelta(days=7)
        self.save(
            update_fields=[
                "activation_key",
                "activation_key_expires",
                "updated_at",
            ]
        )
        return self.activation_key

    def clear_activation_key(self):
        self.activation_key = None
        self.activation_key_expires = None
        self.save(
            update_fields=[
                "activation_key",
                "activation_key_expires",
                "updated_at",
            ]
        )

    def is_activation_key_valid(self, key):
        if not self.activation_key:
            return False

        if self.activation_key != key:
            return False

        if self.activation_key_expires and self.activation_key_expires < timezone.now():
            return False

        return True
