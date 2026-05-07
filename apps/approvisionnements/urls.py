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

    # ─── BC ──────────────────────────────────────────────
    path("bc/", views.bc_liste, name="bc_liste"),
    path("bc/<int:pk>/", views.bc_detail, name="bc_detail"),
    path("bc/<int:pk>/valider/", views.bc_valider, name="bc_valider"),
    path("bc/<int:pk>/supprimer/", views.bc_supprimer, name="bc_supprimer"),
    path("bc/<int:pk>/pdf/", views.bc_pdf, name="bc_pdf"),
]