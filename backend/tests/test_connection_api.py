import pytest
from connections.models import ConnectionSession
from django.contrib.auth import get_user_model
from django.utils import timezone
from proxies.models import VirtualMachine
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient

User = get_user_model()


@pytest.mark.django_db
def test_activate_key_assigns_free_virtual_machine(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "connections.views.send_connection_status",
        lambda *args, **kwargs: None,
    )

    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )
    activation_key = user.refresh_activation_key()

    virtual_machine = VirtualMachine.objects.create(
        name="proxy-1",
        host="127.0.0.1",
        port=1080,
        protocol=VirtualMachine.Protocol.SOCKS5,
        is_active=True,
    )

    response = client.post(
        "/api/activate-key/",
        {
            "activation_key": activation_key,
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == "connected"
    assert response.data["user_id"] == user.id
    assert "connection_token" in response.data

    assert response.data["proxy"]["id"] == virtual_machine.id
    assert response.data["proxy"]["host"] == "127.0.0.1"
    assert response.data["proxy"]["port"] == 1080
    assert response.data["proxy"]["protocol"] == "socks5"

    user.refresh_from_db()
    virtual_machine.refresh_from_db()

    assert user.activation_key is None
    assert user.activation_key_expires is None
    assert virtual_machine.current_user == user
    assert virtual_machine.last_used_at is not None

    session = ConnectionSession.objects.get(user=user)

    assert session.virtual_machine == virtual_machine
    assert session.status == ConnectionSession.Status.CONNECTED
    assert session.token == response.data["connection_token"]


@pytest.mark.django_db
def test_activate_key_returns_error_for_invalid_key(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "connections.views.send_connection_status",
        lambda *args, **kwargs: None,
    )

    response = client.post(
        "/api/activate-key/",
        {
            "activation_key": "invalid-key",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["status"] == "error"
    assert (
        response.data["detail"] == "Ключ активации не найден или уже был использован."
    )


@pytest.mark.django_db
def test_activate_key_returns_no_free_vms(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "connections.views.send_connection_status",
        lambda *args, **kwargs: None,
    )

    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )
    activation_key = user.refresh_activation_key()

    other_user = User.objects.create_user(
        email="other@example.com",
        password="StrongPassword123",
    )

    VirtualMachine.objects.create(
        name="proxy-1",
        host="127.0.0.1",
        port=1080,
        protocol=VirtualMachine.Protocol.SOCKS5,
        is_active=True,
        current_user=other_user,
    )

    response = client.post(
        "/api/activate-key/",
        {
            "activation_key": activation_key,
        },
        format="json",
    )

    assert response.status_code == 503
    assert response.data["status"] == "no_free_vms"
    assert response.data["detail"] == "Все прокси заняты. Попробуйте позже."

    user.refresh_from_db()

    assert user.activation_key == activation_key


@pytest.mark.django_db
def test_authenticated_disconnect_releases_virtual_machine(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "connections.views.send_connection_status",
        lambda *args, **kwargs: None,
    )

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

    ConnectionSession.objects.create(
        user=user,
        virtual_machine=virtual_machine,
        status=ConnectionSession.Status.CONNECTED,
    )

    client.credentials(
        HTTP_AUTHORIZATION=f"Token {token.key}",
    )

    response = client.post("/api/disconnect/")

    assert response.status_code == 200
    assert response.data["status"] == "disconnected"

    virtual_machine.refresh_from_db()

    assert virtual_machine.current_user is None

    session = ConnectionSession.objects.get(user=user)

    assert session.status == ConnectionSession.Status.DISCONNECTED
    assert session.disconnected_at is not None


@pytest.mark.django_db
def test_desktop_disconnect_by_connection_token(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "connections.views.send_connection_status",
        lambda *args, **kwargs: None,
    )

    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )

    virtual_machine = VirtualMachine.objects.create(
        name="proxy-1",
        host="127.0.0.1",
        port=1080,
        protocol=VirtualMachine.Protocol.SOCKS5,
        is_active=True,
        current_user=user,
    )

    session = ConnectionSession.objects.create(
        user=user,
        virtual_machine=virtual_machine,
        status=ConnectionSession.Status.CONNECTED,
    )

    response = client.post(
        "/api/desktop/disconnect/",
        {
            "connection_token": session.token,
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == "disconnected"

    virtual_machine.refresh_from_db()
    session.refresh_from_db()

    assert virtual_machine.current_user is None
    assert session.status == ConnectionSession.Status.DISCONNECTED
    assert session.disconnected_at is not None


@pytest.mark.django_db
def test_activation_key_can_be_used_only_once(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "connections.views.send_connection_status",
        lambda *args, **kwargs: None,
    )

    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )
    activation_key = user.refresh_activation_key()

    VirtualMachine.objects.create(
        name="proxy-1",
        host="127.0.0.1",
        port=1080,
        protocol=VirtualMachine.Protocol.SOCKS5,
        is_active=True,
    )

    first_response = client.post(
        "/api/activate-key/",
        {
            "activation_key": activation_key,
        },
        format="json",
    )

    assert first_response.status_code == 200
    assert first_response.data["status"] == "connected"

    second_response = client.post(
        "/api/activate-key/",
        {
            "activation_key": activation_key,
        },
        format="json",
    )

    assert second_response.status_code == 400
    assert second_response.data["status"] == "error"
    assert (
        second_response.data["detail"]
        == "Ключ активации не найден или уже был использован."
    )


@pytest.mark.django_db
def test_expired_activation_key_returns_error(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "connections.views.send_connection_status",
        lambda *args, **kwargs: None,
    )

    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )

    activation_key = user.refresh_activation_key()
    user.activation_key_expires = timezone.now() - timezone.timedelta(days=1)
    user.save(update_fields=["activation_key_expires", "updated_at"])

    VirtualMachine.objects.create(
        name="proxy-1",
        host="127.0.0.1",
        port=1080,
        protocol=VirtualMachine.Protocol.SOCKS5,
        is_active=True,
    )

    response = client.post(
        "/api/activate-key/",
        {
            "activation_key": activation_key,
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["status"] == "error"
    assert response.data["detail"] == "Ключ активации недействителен или истёк."

    user.refresh_from_db()

    assert user.activation_key == activation_key


@pytest.mark.django_db
def test_inactive_virtual_machine_is_not_assigned(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "connections.views.send_connection_status",
        lambda *args, **kwargs: None,
    )

    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )
    activation_key = user.refresh_activation_key()

    inactive_vm = VirtualMachine.objects.create(
        name="proxy-inactive",
        host="127.0.0.1",
        port=1080,
        protocol=VirtualMachine.Protocol.SOCKS5,
        is_active=False,
    )

    active_vm = VirtualMachine.objects.create(
        name="proxy-active",
        host="127.0.0.2",
        port=1081,
        protocol=VirtualMachine.Protocol.SOCKS5,
        is_active=True,
    )

    response = client.post(
        "/api/activate-key/",
        {
            "activation_key": activation_key,
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == "connected"
    assert response.data["proxy"]["id"] == active_vm.id
    assert response.data["proxy"]["name"] == "proxy-active"

    inactive_vm.refresh_from_db()
    active_vm.refresh_from_db()

    assert inactive_vm.current_user is None
    assert active_vm.current_user == user


@pytest.mark.django_db
def test_user_does_not_occupy_multiple_proxies_after_new_activation(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "connections.views.send_connection_status",
        lambda *args, **kwargs: None,
    )

    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )

    old_vm = VirtualMachine.objects.create(
        name="proxy-old",
        host="127.0.0.1",
        port=1080,
        protocol=VirtualMachine.Protocol.SOCKS5,
        is_active=True,
        current_user=user,
    )

    old_session = ConnectionSession.objects.create(
        user=user,
        virtual_machine=old_vm,
        status=ConnectionSession.Status.CONNECTED,
    )

    new_vm = VirtualMachine.objects.create(
        name="proxy-new",
        host="127.0.0.2",
        port=1081,
        protocol=VirtualMachine.Protocol.SOCKS5,
        is_active=True,
    )

    activation_key = user.refresh_activation_key()

    response = client.post(
        "/api/activate-key/",
        {
            "activation_key": activation_key,
        },
        format="json",
    )

    assert response.status_code == 200
    assert response.data["status"] == "connected"

    old_vm.refresh_from_db()
    new_vm.refresh_from_db()
    old_session.refresh_from_db()

    assigned_vms = VirtualMachine.objects.filter(current_user=user)

    assert assigned_vms.count() == 1

    assigned_vm = assigned_vms.first()

    assert assigned_vm in [old_vm, new_vm]

    assert old_session.status == ConnectionSession.Status.DISCONNECTED
    assert old_session.disconnected_at is not None

    connected_sessions = ConnectionSession.objects.filter(
        user=user,
        status=ConnectionSession.Status.CONNECTED,
    )

    assert connected_sessions.count() == 1
    assert connected_sessions.first().virtual_machine == assigned_vm


@pytest.mark.django_db
def test_desktop_disconnect_with_invalid_token_returns_error(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "connections.views.send_connection_status",
        lambda *args, **kwargs: None,
    )

    response = client.post(
        "/api/desktop/disconnect/",
        {
            "connection_token": "invalid-token",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.data["status"] == "error"
    assert response.data["detail"] == "Активная сессия подключения не найдена."


@pytest.mark.django_db
def test_desktop_disconnect_token_cannot_be_used_twice(monkeypatch):
    client = APIClient()

    monkeypatch.setattr(
        "connections.views.send_connection_status",
        lambda *args, **kwargs: None,
    )

    user = User.objects.create_user(
        email="user@example.com",
        password="StrongPassword123",
    )

    virtual_machine = VirtualMachine.objects.create(
        name="proxy-1",
        host="127.0.0.1",
        port=1080,
        protocol=VirtualMachine.Protocol.SOCKS5,
        is_active=True,
        current_user=user,
    )

    session = ConnectionSession.objects.create(
        user=user,
        virtual_machine=virtual_machine,
        status=ConnectionSession.Status.CONNECTED,
    )

    first_response = client.post(
        "/api/desktop/disconnect/",
        {
            "connection_token": session.token,
        },
        format="json",
    )

    assert first_response.status_code == 200
    assert first_response.data["status"] == "disconnected"

    second_response = client.post(
        "/api/desktop/disconnect/",
        {
            "connection_token": session.token,
        },
        format="json",
    )

    assert second_response.status_code == 400
    assert second_response.data["status"] == "error"
    assert second_response.data["detail"] == "Активная сессия подключения не найдена."

    virtual_machine.refresh_from_db()
    session.refresh_from_db()

    assert virtual_machine.current_user is None
    assert session.status == ConnectionSession.Status.DISCONNECTED
