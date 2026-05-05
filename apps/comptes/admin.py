"""Configuration de l'admin Django pour l'app comptes."""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Session, Utilisateur


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    """Interface admin enrichie pour le modele Utilisateur."""

    # Champs affiches dans la liste
    list_display = (
        "identifiant",
        "nom_complet",
        "email",
        "role",
        "est_actif",
        "tentatives_echecs",
        "date_creation",
    )
    list_filter = ("role", "est_actif", "is_staff", "is_superuser")
    search_fields = ("identifiant", "nom_complet", "email")
    ordering = ("nom_complet",)

    # Organisation des champs dans le formulaire d'edition
    fieldsets = (
        ("Identite", {
            "fields": ("identifiant", "password", "nom_complet", "email", "role"),
        }),
        ("Etat du compte", {
            "fields": (
                "est_actif",
                "tentatives_echecs",
                "date_dernier_echec",
                "date_blocage",
                "motif_blocage",
            ),
        }),
        ("Permissions", {
            "fields": (
                "is_staff",
                "is_superuser",
                "groups",
                "user_permissions",
            ),
            "classes": ("collapse",),
        }),
        ("Horodatage", {
            "fields": (
                "date_creation",
                "date_modification",
                "date_derniere_connexion_reussie",
                "last_login",
            ),
            "classes": ("collapse",),
        }),
    )

    readonly_fields = (
        "date_creation",
        "date_modification",
        "date_dernier_echec",
        "date_blocage",
        "date_derniere_connexion_reussie",
        "last_login",
    )

    # Formulaire de creation
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "identifiant",
                "nom_complet",
                "email",
                "role",
                "password1",
                "password2",
            ),
        }),
    )

    # Action admin pour debloquer en masse
    actions = ["debloquer_comptes"]

    @admin.action(description="Debloquer les comptes selectionnes")
    def debloquer_comptes(self, request, queryset):
        """Action admin pour debloquer plusieurs comptes a la fois."""
        nb = 0
        for utilisateur in queryset:
            utilisateur.debloquer()
            nb += 1
        self.message_user(request, f"{nb} compte(s) debloque(s).")


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    """Interface admin pour les sessions utilisateurs."""

    list_display = (
        "utilisateur",
        "adresse_ip",
        "est_active",
        "date_creation",
        "date_expiration",
    )
    list_filter = ("est_active",)
    search_fields = ("utilisateur__identifiant", "adresse_ip")
    readonly_fields = (
        "utilisateur",
        "jeton_jwt",
        "cle_session_django",
        "adresse_ip",
        "user_agent",
        "date_creation",
        "date_derniere_activite",
        "date_expiration",
    )
    ordering = ("-date_creation",)