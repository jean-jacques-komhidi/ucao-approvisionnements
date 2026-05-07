"""Admin Django pour Notifications."""
from django.contrib import admin

from .models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("sujet", "destinataire", "type_notif", "niveau", "est_lue", "email_envoye", "date_creation")
    list_filter = ("type_notif", "niveau", "est_lue", "email_envoye")
    search_fields = ("sujet", "message", "destinataire__identifiant")
    readonly_fields = ("date_creation", "date_lecture")
    ordering = ("-date_creation",)