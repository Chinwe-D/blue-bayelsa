import pytest
from django.contrib.auth.models import Group
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.accounts.roles import Role


def make_user(username, role=None, **extra):
    user = User.objects.create_user(username=username, email=f"{username}@example.org",
                                    password="a-strong-test-password", **extra)
    if role:
        user.groups.add(Group.objects.get(name=role.value))
    return user


@pytest.fixture
def entry_user(db):
    return make_user("entry", Role.DATA_ENTRY)


@pytest.fixture
def reviewer(db):
    return make_user("reviewer", Role.REVIEWER)


@pytest.fixture
def reviewer2(db):
    return make_user("reviewer2", Role.REVIEWER)


@pytest.fixture
def administrator(db):
    return make_user("admin1", Role.ADMINISTRATOR)


@pytest.fixture
def plain_user(db):
    return make_user("plain")


@pytest.fixture
def client():
    return APIClient()


def client_for(user):
    c = APIClient()
    c.force_authenticate(user)
    return c
