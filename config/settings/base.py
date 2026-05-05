"""
Configuration de base — UCAO-ISG-CSM Approvisionnements.

Settings partagés entre development, production et testing.
Les valeurs sensibles sont chargées depuis les variables d'environnement.
"""
import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# ═══════════════════════════════════════════════════════════════════
# CHEMINS DE BASE
# ═══════════════════════════════════════════════════════════════════
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Chargement du fichier .env à la racine
load_dotenv(BASE_DIR / ".env")


# ═══════════════════════════════════════════════════════════════════
# SÉCURITÉ — Variables d'environnement obligatoires
# ═══════════════════════════════════════════════════════════════════
SECRET_KEY = os.getenv("SECRET_KEY", "django-insecure-CHANGEZ-MOI-EN-PROD")
DEBUG = False  # Surchargé en development.py
ALLOWED_HOSTS: list[str] = []


# ═══════════════════════════════════════════════════════════════════
# APPLICATIONS
# ═══════════════════════════════════════════════════════════════════
APPLICATIONS_DJANGO = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

APPLICATIONS_TIERCES = [
    "rest_framework",
    "rest_framework_simplejwt",
    "django_filters",
]

APPLICATIONS_LOCALES = [
    "apps.core",
    "apps.comptes",
    "apps.referentiels",
    "apps.approvisionnements",
    "apps.extensions.iot",
    "apps.extensions.prediction",
]

INSTALLED_APPS = APPLICATIONS_DJANGO + APPLICATIONS_TIERCES + APPLICATIONS_LOCALES


# ═══════════════════════════════════════════════════════════════════
# MIDDLEWARES
# ═══════════════════════════════════════════════════════════════════
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.comptes.middleware.ExpirationSession15MinMiddleware",
]


# ═══════════════════════════════════════════════════════════════════
# URLS ET WSGI
# ═══════════════════════════════════════════════════════════════════
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"


# ═══════════════════════════════════════════════════════════════════
# TEMPLATES — Jinja2
# ═══════════════════════════════════════════════════════════════════
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.jinja2.Jinja2",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "environment": "config.jinja2_env.environment",
        },
    },
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
    },
]


# ═══════════════════════════════════════════════════════════════════
# BASE DE DONNÉES — PostgreSQL 15
# ═══════════════════════════════════════════════════════════════════
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME", "appro_ucao"),
        "USER": os.getenv("DB_USER", "ucao_admin"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
        "CONN_MAX_AGE": 60,
        "OPTIONS": {
            "client_encoding": "UTF8",
        },
    }
}


# ═══════════════════════════════════════════════════════════════════
# AUTHENTIFICATION
# ═══════════════════════════════════════════════════════════════════
AUTH_USER_MODEL = "comptes.Utilisateur"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
     "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Backend custom : gere le compteur d'echecs et le blocage a 5 tentatives
AUTHENTICATION_BACKENDS = [
    "apps.comptes.backends.BackendCompteurEchecs",
    "django.contrib.auth.backends.ModelBackend",
]

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.Argon2PasswordHasher",
]

LOGIN_URL = "/connexion/"
LOGIN_REDIRECT_URL = "/tableau-de-bord/"
LOGOUT_REDIRECT_URL = "/connexion/"


# ═══════════════════════════════════════════════════════════════════
# SESSIONS
# ═══════════════════════════════════════════════════════════════════
SESSION_ENGINE = "django.contrib.sessions.backends.db"
SESSION_COOKIE_AGE = 15 * 60
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"


# ═══════════════════════════════════════════════════════════════════
# CSRF
# ═══════════════════════════════════════════════════════════════════
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SAMESITE = "Lax"
CSRF_USE_SESSIONS = False


# ═══════════════════════════════════════════════════════════════════
# JWT (SimpleJWT)
# ═══════════════════════════════════════════════════════════════════
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "ALGORITHM": "HS256",
    "SIGNING_KEY": SECRET_KEY,
    "AUTH_HEADER_TYPES": ("Bearer",),
}


# ═══════════════════════════════════════════════════════════════════
# REST FRAMEWORK
# ═══════════════════════════════════════════════════════════════════
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 50,
    "DEFAULT_FILTER_BACKENDS": (
        "django_filters.rest_framework.DjangoFilterBackend",
    ),
}


# ═══════════════════════════════════════════════════════════════════
# CACHE — local en mémoire
# ═══════════════════════════════════════════════════════════════════
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "appro-ucao-cache",
    }
}


# ═══════════════════════════════════════════════════════════════════
# EMAIL
# ═══════════════════════════════════════════════════════════════════
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
EMAIL_HOST = os.getenv("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.getenv("EMAIL_PORT", "587"))
EMAIL_USE_TLS = True
EMAIL_HOST_USER = os.getenv("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = os.getenv("EMAIL_HOST_PASSWORD", "")
DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "UCAO Approvisionnements <noreply@ucao-isg-csm.sn>",
)


# ═══════════════════════════════════════════════════════════════════
# INTERNATIONALISATION
# ═══════════════════════════════════════════════════════════════════
LANGUAGE_CODE = "fr-fr"
TIME_ZONE = "Africa/Dakar"
USE_I18N = True
USE_TZ = True

LOCALE_PATHS = [BASE_DIR / "locale"]


# ═══════════════════════════════════════════════════════════════════
# FICHIERS STATIQUES ET MEDIA
# ═══════════════════════════════════════════════════════════════════
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


# ═══════════════════════════════════════════════════════════════════
# CHAMP CLE PRIMAIRE PAR DÉFAUT
# ═══════════════════════════════════════════════════════════════════
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ═══════════════════════════════════════════════════════════════════
# CONSTANTES MÉTIER — UCAO-ISG-CSM
# ═══════════════════════════════════════════════════════════════════
SEUIL_BC_FCFA = 50_000
NB_TENTATIVES_AVANT_BLOCAGE = 5
DUREE_CONSERVATION_SUPPRIMES_JOURS = 365
TVA_AUTORISEES = [0, 10, 18]
DELAI_RELANCE_DRAFT_JOURS = 7
DELAI_ALERTE_GEOFENCING_SEC = 10


# ═══════════════════════════════════════════════════════════════════
# LOGGING
# ═══════════════════════════════════════════════════════════════════
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "verbose": {
            "format": "[{asctime}] {levelname} {name} {module}.{funcName}:{lineno} - {message}",
            "style": "{",
        },
        "simple": {
            "format": "{levelname} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "simple",
        },
        "fichier_django": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "django.log",
            "formatter": "verbose",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
        },
        "fichier_erreurs": {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": BASE_DIR / "logs" / "erreurs.log",
            "formatter": "verbose",
            "level": "ERROR",
            "maxBytes": 10 * 1024 * 1024,
            "backupCount": 5,
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console", "fichier_django"],
            "level": "INFO",
            "propagate": True,
        },
        "apps": {
            "handlers": ["console", "fichier_django", "fichier_erreurs"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
}