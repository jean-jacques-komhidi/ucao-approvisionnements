"""URLs de l'app referentiels."""
from django.urls import path


from . import views

urlpatterns = [
    # ─── Articles ─────────────────────────────────────────
    path("articles/", views.liste_articles, name="articles_liste"),
    path("articles/nouveau/", views.article_creer, name="article_creer"),
    path("articles/<int:pk>/modifier/", views.article_modifier, name="article_modifier"),
    path("articles/<int:pk>/supprimer/", views.article_supprimer, name="article_supprimer"),

    # ─── GESTION STOCK ──────────────────────────────────
    path("referentiels/stock/", views.articles_stock, name="articles_stock"),
    path("referentiels/stock/<int:pk>/ajuster/", views.article_ajuster_stock, name="article_ajuster_stock"),

    # ─── Services exterieurs ─────────────────────────────
    path("services/", views.liste_services, name="services_liste"),
    path("services/nouveau/", views.service_creer, name="service_creer"),
    path("services/<int:pk>/modifier/", views.service_modifier, name="service_modifier"),
    path("services/<int:pk>/supprimer/", views.service_supprimer, name="service_supprimer"),

    # ─── Fournisseurs ────────────────────────────────────
    path("fournisseurs/", views.liste_fournisseurs, name="fournisseurs_liste"),
    path("fournisseurs/nouveau/", views.fournisseur_creer, name="fournisseur_creer"),
    path("fournisseurs/<int:pk>/modifier/", views.fournisseur_modifier, name="fournisseur_modifier"),
    path("fournisseurs/<int:pk>/supprimer/", views.fournisseur_supprimer, name="fournisseur_supprimer"),

    # ─── Devises (DFC uniquement) ────────────────────────
    path("devises/", views.liste_devises, name="devises_liste"),
    path("devises/nouvelle/", views.devise_creer, name="devise_creer"),
    path("devises/<int:pk>/modifier/", views.devise_modifier, name="devise_modifier"),
]