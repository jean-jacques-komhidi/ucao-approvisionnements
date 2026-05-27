"""
Configuration de DEVELOPPEMENT LOCAL.
Active DEBUG, autorise localhost + ngrok, desactive HTTPS.
"""
from .base import *  # noqa: F401, F403

DEBUG = True

# Hotes autorises : localhost + ngrok (tous domaines)
ALLOWED_HOSTS = [
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    ".ngrok-free.app",
    ".ngrok-free.dev",
    ".ngrok.app",
    ".ngrok.io",
]

# Autoriser ngrok pour les POST (formulaires CSRF)
CSRF_TRUSTED_ORIGINS = [
    "https://*.ngrok-free.app",
    "https://*.ngrok-free.dev",
    "https://*.ngrok.app",
    "https://*.ngrok.io",
]

# Outils de developpement
INSTALLED_APPS += ["debug_toolbar"]  # noqa: F405
MIDDLEWARE += [  # noqa: F405
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]
INTERNAL_IPS = ["127.0.0.1", "localhost"]

# Securite relachee pour le developpement
SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False

# Logging plus verbeux
LOGGING["loggers"]["django"]["level"] = "DEBUG"  # noqa: F405
LOGGING["loggers"]["apps"]["level"] = "DEBUG"  # noqa: F405
