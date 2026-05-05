"""Configuration de l'app IoT (suivi equipements RFID/BLE)."""
from django.apps import AppConfig


class IoTConfig(AppConfig):
    """Application de suivi IoT des equipements."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.extensions.iot"
    label = "iot"
    verbose_name = "Extension IoT"