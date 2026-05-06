"""Configuration de l'app referentiels."""
from django.apps import AppConfig


class ReferentielsConfig(AppConfig):
    """Application de gestion des referentiels."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.referentiels"
    verbose_name = "Referentiels"

    def ready(self):
        """Import des signaux : code fournisseur auto F0001."""
        from . import signals  # noqa: F401