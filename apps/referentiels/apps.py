"""Configuration de l'app referentiels (Articles, Services, Fournisseurs, Devises)."""
from django.apps import AppConfig


class ReferentielsConfig(AppConfig):
    """Application de gestion des referentiels."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.referentiels"
    verbose_name = "Referentiels"