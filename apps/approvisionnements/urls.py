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

    # ─── PAIEMENTS : BC a payer ──────────────────────────
    path("paiements/bc-a-payer/", views.paiements_bc_a_payer, name="paiements_bc_a_payer"),

    # ─── ORDRE DE PAIEMENT ───────────────────────────────
    path("paiements/ordres/", views.ordres_paiement_liste, name="ordres_paiement_liste"),
    path("paiements/ordre/creer/<int:bc_pk>/", views.ordre_paiement_creer, name="ordre_paiement_creer"),
    path("paiements/ordre/<int:pk>/", views.ordre_paiement_detail, name="ordre_paiement_detail"),
    path("paiements/ordre/<int:pk>/viser/", views.ordre_paiement_viser, name="ordre_paiement_viser"),

    # ─── PAIEMENT EXECUTION ──────────────────────────────
    path("paiements/executer/<int:ordre_pk>/", views.paiement_executer, name="paiement_executer"),
    path("paiements/<int:pk>/", views.paiement_detail, name="paiement_detail"),

    # ─── HISTORIQUE ──────────────────────────────────────
    path("paiements/historique/", views.paiements_historique, name="paiements_historique"),
]