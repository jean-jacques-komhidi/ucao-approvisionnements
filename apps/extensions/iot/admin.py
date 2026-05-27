"""Admin Django pour IoT."""
from django.contrib import admin

from .models import AlerteIoT, Equipement, Localisation, ZoneGeographique


@admin.register(ZoneGeographique)
class ZoneGeographiqueAdmin(admin.ModelAdmin):
    list_display = ("nom", "batiment", "etage", "type_zone", "est_zone_autorisee", "est_active")
    list_filter = ("type_zone", "est_zone_autorisee", "est_active", "batiment")
    search_fields = ("nom", "batiment", "description")
    ordering = ("batiment", "etage", "nom")


@admin.register(Equipement)
class EquipementAdmin(admin.ModelAdmin):
    list_display = ("designation", "numero_serie", "rfid_tag", "zone_actuelle", "statut", "est_suivi_iot", "derniere_detection")
    list_filter = ("statut", "est_suivi_iot", "acces_bloque")
    search_fields = ("designation", "numero_serie", "rfid_tag")
    readonly_fields = ("token_capteur", "derniere_detection", "date_creation", "date_modification")
    ordering = ("-date_creation",)


@admin.register(Localisation)
class LocalisationAdmin(admin.ModelAdmin):
    list_display = ("equipement", "zone", "timestamp", "signal_force", "est_alerte")
    list_filter = ("est_alerte", "zone")
    date_hierarchy = "timestamp"
    ordering = ("-timestamp",)


@admin.register(AlerteIoT)
class AlerteIoTAdmin(admin.ModelAdmin):
    list_display = ("equipement", "type_alerte", "zone_actuelle", "est_traitee", "timestamp")
    list_filter = ("type_alerte", "est_traitee")
    search_fields = ("equipement__designation", "message")
    readonly_fields = ("timestamp", "date_traitement")
    ordering = ("-timestamp",)