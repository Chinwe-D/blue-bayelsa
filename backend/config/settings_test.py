from .settings import *  # noqa: F401,F403

INSTALLED_APPS = INSTALLED_APPS + ["tests.testapp"]  # noqa: F405
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]  # fast tests only
REST_FRAMEWORK = {**REST_FRAMEWORK, "DEFAULT_THROTTLE_RATES": {"login": "1000/min"}}  # noqa: F405
