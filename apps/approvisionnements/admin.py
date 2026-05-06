"""Admin Django pour l'app approvisionnements."""
from django.contrib import admin

from .models import FicheExpression, LigneFiche


class LigneFicheInline(admin.TabularInline):
    """Lignes editables en inline dans la FEB."""

    model = LigneFiche
    extra = 0
    fields = (
        "type_ligne", "article", "service", "designation_libre",
        "quantite", "prix_unitaire", "montant_ligne",
    )
    readonly_fields = ("montant_ligne",)


@admin.register(FicheExpression)
class FicheExpressionAdmin(admin.ModelAdmin):
    list_display = (
        "numero", "objet", "demandeur", "fournisseur",
        "statut", "montant_ttc", "date_creation",
    )
    list_filter = ("statut", "origine", "est_supprimee")
    search_fields = ("numero", "objet", "demandeur__identifiant", "fournisseur__nom")
    ordering = ("-date_creation",)
    readonly_fields = (
        "numero", "montant_ht", "montant_tva", "montant_ttc",
        "date_creation", "date_modification", "date_validation", "date_suppression",
    )
    fieldsets = (
        ("Identification", {
            "fields": ("numero", "objet", "statut", "origine"),
        }),
        ("Acteurs", {
            "fields": ("demandeur", "fournisseur", "validateur"),
        }),
        ("Montants", {
            "fields": ("montant_ht", "taux_tva", "montant_tva", "montant_ttc"),
        }),
        ("Suppression / Motif", {
            "fields": ("est_supprimee", "motif_action"),
            "classes": ("collapse",),
        }),
        ("Tracabilite", {
            "fields": (
                "date_creation", "date_modification",
                "date_validation", "date_suppression",
            ),
            "classes": ("collapse",),
        }),
    )
    inlines = [LigneFicheInline]


@admin.register(LigneFiche)
class LigneFicheAdmin(admin.ModelAdmin):
    list_display = ("fiche", "type_ligne", "designation", "quantite", "prix_unitaire", "montant_ligne")
    list_filter = ("type_ligne",)
    search_fields = ("fiche__numero", "designation_libre")