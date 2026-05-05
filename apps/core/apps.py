"""Configuration de l'app core (fondations partagees)."""
from django.apps import AppConfig


class CoreConfig(AppConfig):
    """Application des fondations transversales."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.core"
    verbose_name = "Fondations & Audit"