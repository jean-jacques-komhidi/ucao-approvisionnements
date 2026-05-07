"""URLs de l'app notifications."""
from django.urls import path

from . import views

urlpatterns = [
    path("notifications/", views.liste, name="notifications_liste"),
    path("notifications/<int:pk>/lue/", views.marquer_lue, name="notification_marquer_lue"),
    path("notifications/toutes-lues/", views.marquer_toutes_lues, name="notifications_toutes_lues"),
    path("api/notifications/compteur/", views.compteur_non_lues, name="notifications_compteur"),
]