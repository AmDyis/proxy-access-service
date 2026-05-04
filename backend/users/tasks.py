from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail

from users.models import User


@shared_task
def send_activation_key_email(user_id):
    try:
        user = User.objects.get(id=user_id)
    except User.DoesNotExist:
        return "User not found"

    if not user.activation_key:
        return "User has no activation key"

    subject = "Ваш ключ активации для Proxy Access Service"

    message = (
        f"Здравствуйте!\n\n"
        f"Ваш ключ активации:\n\n"
        f"{user.activation_key}\n\n"
        f"Введите этот ключ в десктопном приложении, чтобы подключиться к прокси-серверу.\n\n"
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )

    return f"Activation key sent to {user.email}"
