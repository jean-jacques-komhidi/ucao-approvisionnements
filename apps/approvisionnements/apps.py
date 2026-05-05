"""Configuration de l'app approvisionnements (FEB + BC + Paiement + Suivi)."""
from django.apps import AppConfig


class ApprovisionnementsConfig(AppConfig):
    """Application du cycle FEB -> BC -> Paiement."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.approvisionnements"
    verbose_name = "Cycle Approvisionnements"