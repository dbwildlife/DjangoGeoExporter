"""Settings used by the Django/PostGIS integration test suite."""

import os

os.environ["SECRET_KEY"] = "test-only-secret-key"
os.environ["DEBUG"] = "False"
os.environ.setdefault("DBNAME", "djangogeoexporter_test")
os.environ.setdefault("DBUSER", "postgres")
os.environ.setdefault("DBPASSWORD", "postgres")
os.environ.setdefault("DBHOST", "localhost")
os.environ.setdefault("DBPORT", "5432")
os.environ["EMAIL_HOST"] = "localhost"
os.environ["EMAIL_PORT"] = "25"
os.environ["EMAIL_HOST_PASSWORD"] = ""
os.environ["EMAIL_HOST_USER"] = ""
os.environ["EMAIL_USE_TLS"] = "False"

from .settings import *  # noqa: E402,F403,F401

PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
