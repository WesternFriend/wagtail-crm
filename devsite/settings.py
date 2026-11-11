"""Development-only settings for synthetic data and local UI checks."""

import os
from pathlib import Path

import dj_database_url
from django.core.management.utils import get_random_secret_key

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / ".data"
DATA_DIR.mkdir(exist_ok=True)

# Persist a random local key across autoreloads without committing a shared key.
_secret_path = DATA_DIR / "secret-key"
if not os.environ.get("DJANGO_SECRET_KEY") and not _secret_path.exists():
    try:
        with _secret_path.open("x") as secret_file:
            _secret_path.chmod(0o600)
            secret_file.write(get_random_secret_key())
    except FileExistsError:
        pass
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY") or _secret_path.read_text()

DEBUG = True
ALLOWED_HOSTS = ["localhost", "127.0.0.1", "[::1]"]

INSTALLED_APPS = [
    "wagtail_crm.contacts",
    "wagtail_crm.payments",
    "wagtail_crm.letters",
    "devsite",
    "wagtail.contrib.forms",
    "wagtail.contrib.redirects",
    "wagtail.embeds",
    "wagtail.sites",
    "wagtail.users",
    "wagtail.snippets",
    "wagtail.documents",
    "wagtail.images",
    "wagtail.search",
    "wagtail.admin",
    "wagtail",
    "modelcluster",
    "taggit",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "wagtail.contrib.redirects.middleware.RedirectMiddleware",
]

ROOT_URLCONF = "devsite.urls"
WSGI_APPLICATION = "devsite.wsgi.application"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

DATABASES = {
    "default": dj_database_url.parse(os.environ["DATABASE_URL"])
    if os.environ.get("DATABASE_URL")
    else {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": str(DATA_DIR / "dev.sqlite3"),
        "OPTIONS": {"timeout": 20},
    }
}

if DATABASES["default"]["ENGINE"] == "django.db.backends.postgresql":
    INSTALLED_APPS.append("django.contrib.postgres")

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"
    },
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = os.environ.get("DJANGO_TIME_ZONE", "UTC")
USE_I18N = True
USE_TZ = True

STATIC_URL = "/static/"
STATIC_ROOT = DATA_DIR / "static"
MEDIA_URL = "/media/"
MEDIA_ROOT = DATA_DIR / "media"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    # Issued letter PDFs: outside MEDIA_ROOT, served only through a view that
    # checks the letter's view permission.
    "letters": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": DATA_DIR / "letters"},
    },
}

MAILERS = {"default": {"BACKEND": "django.core.mail.backends.console.EmailBackend"}}
WAGTAIL_SITE_NAME = "Wagtail CRM (development)"
WAGTAILADMIN_BASE_URL = "http://localhost:8000"
WAGTAILSEARCH_BACKENDS = {"default": {"BACKEND": "wagtail.search.backends.database"}}
WAGTAILDOCS_SERVE_METHOD = "serve_view"
SESSION_COOKIE_HTTPONLY = True
X_FRAME_OPTIONS = "DENY"
