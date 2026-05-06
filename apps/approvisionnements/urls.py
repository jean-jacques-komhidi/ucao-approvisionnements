"""URLs de l'app approvisionnements."""
from django.urls import path

from . import views

urlpatterns = [
    # ─── FEB ─────────────────────────────────────────────
    path("feb/", views.feb_liste, name="feb_liste"),
    path("feb/nouvelle/", views.feb_creer, name="feb_creer"),
    path("feb/<int:pk>/", views.feb_detail, name="feb_detail"),
    path("feb/<int:pk>/valider/", views.feb_valider, name="feb_valider"),
    path("feb/<int:pk>/rejeter/", views.feb_rejeter, name="feb_rejeter"),
    path("feb/<int:pk>/supprimer/", views.feb_supprimer, name="feb_supprimer"),
]