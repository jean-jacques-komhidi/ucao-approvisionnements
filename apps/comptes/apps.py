"""Configuration de l'app comptes (authentification + administration)."""
from django.apps import AppConfig


class ComptesConfig(AppConfig):
    """Application de gestion des utilisateurs et de l'authentification."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.comptes"
    verbose_name = "Comptes utilisateurs"

    def ready(self):
        """Import des signaux : 5 echecs -> blocage, alerte Admin."""
        from . import signals  # noqa: F401