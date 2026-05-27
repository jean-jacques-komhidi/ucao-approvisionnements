"""URLs de l'extension IoT."""
from django.urls import path

from . import views

urlpatterns = [
    # ─── DASHBOARD ──────────────────────────────────────
    path("iot/", views.dashboard_iot, name="iot_dashboard"),

    # ─── EQUIPEMENTS ────────────────────────────────────
    path("iot/equipements/", views.equipements_liste, name="iot_equipements_liste"),
    path("iot/equipement/<int:pk>/", views.equipement_detail, name="iot_equipement_detail"),

    # ─── ALERTES ────────────────────────────────────────
    path("iot/alertes/", views.alertes_liste, name="iot_alertes_liste"),
    path("iot/alerte/<int:pk>/traiter/", views.alerte_traiter, name="iot_alerte_traiter"),
    path("iot/alertes/<int:pk>/", views.alerte_detail, name="iot_alerte_detail"),

    # ─── ZONES ──────────────────────────────────────────
    path("iot/zones/", views.zones_liste, name="iot_zones_liste"),

    # ─── API CAPTEURS (pour les capteurs externes) ──────
    path("api/iot/signal/", views.api_signal_capteur, name="iot_api_signal"),
]