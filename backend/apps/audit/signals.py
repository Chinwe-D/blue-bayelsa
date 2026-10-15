from django.contrib.auth.signals import user_logged_in, user_logged_out, user_login_failed
from django.dispatch import receiver

from .models import AuditLog
from .services import log


@receiver(user_logged_in)
def on_login(sender, request, user, **kwargs):
    log(AuditLog.Action.LOGIN, actor=user, request=request)


@receiver(user_logged_out)
def on_logout(sender, request, user, **kwargs):
    if user is not None:
        log(AuditLog.Action.LOGOUT, actor=user, request=request)


@receiver(user_login_failed)
def on_login_failed(sender, credentials, request=None, **kwargs):
    log(AuditLog.Action.LOGIN_FAILED, request=request,
        actor_label=str(credentials.get("username", ""))[:200])
