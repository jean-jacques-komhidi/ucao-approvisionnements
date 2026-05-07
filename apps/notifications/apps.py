"""Configuration de l'app notifications."""
from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    """Application de notifications in-app + emails."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.notifications"
    verbose_name = "Notifications"

    def ready(self):
        """Enregistre les signaux automatiques au demarrage."""
        from . import signals  # noqa: F401