from django.contrib.auth.models import AbstractUser
from django.db import models

from .roles import Capability, has_capability


class User(AbstractUser):
    """Staff or registered user. Roles are Django groups (see roles.py)."""

    email = models.EmailField("email address", unique=True)
    organisation = models.CharField(max_length=200, blank=True)
    phone = models.CharField(max_length=40, blank=True)

    class Meta:
        ordering = ["username"]

    def can(self, capability: Capability) -> bool:
        return has_capability(self, capability)

    @property
    def role_names(self) -> list[str]:
        return sorted(self.groups.values_list("name", flat=True))
