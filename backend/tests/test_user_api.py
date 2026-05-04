import pytest
from django.contrib.auth import get_user_model
from proxies.models import VirtualMachine
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_register_user_creates_activation_key(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "users.views.send_activation_key_email.delay",
        lambda user_id: None,
    )

    response = client.post(
        "/api/auth/register/",
        {
            "email": "user@example.com",
            "password": "StrongPassword123",
            "password_confirm": "StrongPassword123",
        },
        format="json",
    )

    assert response.status_code == 201

    user = User.objects.get(email="user@example.com")

    assert user.activation_key is not None
    assert len(user.activation_key) == 32
    assert user.activation_key_expires is not None

    assert response.data["message"] == "Письмо с ключом отправлено на почту."
    assert response.data["user"]["email"] == "user@example.com"


@pytest.mark.django_db
def test_login_returns_token():
    client = APIClient()

    User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )

    response = client.post(
        "/api/auth/login/",
        {
            "email": "user@example.com",
            "password": "StrongPassword123",
        },
        format="json",
    )

    assert response.status_code == 200
    assert "token" in response.data
    assert response.data["user"]["email"] == "user@example.com"


@pytest.mark.django_db
def test_profile_requires_authentication():
    client = APIClient()

    response = client.get("/api/profile/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_profile_returns_authenticated_user():
    client = APIClient()

    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )

    token = Token.objects.create(user=user)

    client.credentials(
        HTTP_AUTHORIZATION=f"Token {token.key}",
    )

    response = client.get("/api/profile/")

    assert response.status_code == 200
    assert response.data["email"] == "user@example.com"
    assert response.data["connection_status"] == "disconnected"
    assert response.data["active_proxy"] is None


@pytest.mark.django_db
def test_refresh_activation_key(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "users.views.send_activation_key_email.delay",
        lambda user_id: None,
    )

    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )

    old_key = user.refresh_activation_key()

    token = Token.objects.create(user=user)

    client.credentials(
        HTTP_AUTHORIZATION=f"Token {token.key}",
    )

    response = client.post("/api/profile/refresh-key/")

    assert response.status_code == 200

    user.refresh_from_db()

    assert user.activation_key is not None
    assert user.activation_key != old_key
    assert response.data["message"] == "Новый ключ создан и отправлен на почту."


@pytest.mark.django_db
def test_change_password_successfully():
    client = APIClient()

    user = User.objects.create_user(
        email="user@example.com",
        password="OldPassword123",
    )

    token = Token.objects.create(user=user)

    client.credentials(
        HTTP_AUTHORIZATION=f"Token {token.key}",
    )

    response = client.post(
        "/api/profile/change-password/",
        {
            "old_password": "OldPassword123",
            "new_password": "NewPassword123",
            "new_password_confirm": "NewPassword123",
        },
        format="json",
    )

    assert response.status_code == 200

    user.refresh_from_db()

    assert user.check_password("NewPassword123")


@pytest.mark.django_db
def test_register_user_with_existing_email_returns_error(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "users.views.send_activation_key_email.delay",
        lambda user_id: None,
    )

    User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )

    response = client.post(
        "/api/auth/register/",
        {
            "email": "user@example.com",
            "password": "StrongPassword123",
            "password_confirm": "StrongPassword123",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "email" in response.data


@pytest.mark.django_db
def test_register_user_with_password_mismatch_returns_error(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "users.views.send_activation_key_email.delay",
        lambda user_id: None,
    )

    response = client.post(
        "/api/auth/register/",
        {
            "email": "user@example.com",
            "password": "StrongPassword123",
            "password_confirm": "AnotherPassword123",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "password_confirm" in response.data


@pytest.mark.django_db
def test_refresh_activation_key_requires_authentication():
    client = APIClient()

    response = client.post("/api/profile/refresh-key/")

    assert response.status_code == 401


@pytest.mark.django_db
def test_profile_returns_active_proxy_when_user_connected():
    client = APIClient()

    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )

    token = Token.objects.create(user=user)

    virtual_machine = VirtualMachine.objects.create(
        name="proxy-1",
        host="127.0.0.1",
        port=1080,
        protocol=VirtualMachine.Protocol.SOCKS5,
        is_active=True,
        current_user=user,
    )

    client.credentials(
        HTTP_AUTHORIZATION=f"Token {token.key}",
    )

    response = client.get("/api/profile/")

    assert response.status_code == 200
    assert response.data["connection_status"] == "connected"
    assert response.data["active_proxy"] is not None
    assert response.data["active_proxy"]["id"] == virtual_machine.id
    assert response.data["active_proxy"]["name"] == "proxy-1"
    assert response.data["active_proxy"]["host"] == "127.0.0.1"
    assert response.data["active_proxy"]["port"] == 1080
    assert response.data["active_proxy"]["protocol"] == "socks5"
