"""Configuration de l'app IoT."""
from django.apps import AppConfig


class IotConfig(AppConfig):
    """Application de suivi IoT des equipements."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.extensions.iot"
    verbose_name = "Extension IoT"
    label = "iot"

    def ready(self):
        """Enregistre les signaux automatiques au demarrage."""
        from . import signals  # noqa: F401