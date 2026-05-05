"""Configuration de l'app Prediction (anticipation des besoins)."""
from django.apps import AppConfig


class PredictionConfig(AppConfig):
    """Application de prediction intelligente des besoins."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.extensions.prediction"
    label = "prediction"
    verbose_name = "Extension Prediction"