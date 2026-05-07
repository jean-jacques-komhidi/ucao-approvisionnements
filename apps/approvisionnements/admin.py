"""Admin Django pour l'app approvisionnements."""
from django.contrib import admin

from .models import BonCommande, FicheExpression, LigneFiche
from .models import OrdrePaiement, Paiement


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
    inlines = [LigneFicheInline]


@admin.register(BonCommande)
class BonCommandeAdmin(admin.ModelAdmin):
    list_display = (
        "numero", "fiche", "fournisseur", "statut",
        "montant_ttc", "est_envoye_fournisseur", "date_creation",
    )
    list_filter = ("statut", "est_envoye_fournisseur", "signe_en_po", "est_supprime")
    search_fields = ("numero", "fiche__numero", "fournisseur__nom")
    ordering = ("-date_creation",)
    readonly_fields = (
        "numero", "fiche", "fournisseur",
        "montant_ht", "montant_tva", "montant_ttc",
        "date_creation", "date_modification",
        "date_validation", "date_envoi_fournisseur", "date_suppression",
    )
    fieldsets = (
        ("Identification", {
            "fields": ("numero", "statut", "fiche", "fournisseur"),
        }),
        ("Montants", {
            "fields": ("montant_ht", "taux_tva", "montant_tva", "montant_ttc"),
        }),
        ("Validation", {
            "fields": ("validateur", "signe_en_po", "est_verrouille", "date_validation"),
        }),
        ("Envoi fournisseur", {
            "fields": ("est_envoye_fournisseur", "date_envoi_fournisseur"),
        }),
        ("Suppression", {
            "fields": ("est_supprime", "motif_suppression", "date_suppression"),
            "classes": ("collapse",),
        }),
        ("Dates systeme", {
            "fields": ("date_creation", "date_modification"),
            "classes": ("collapse",),
        }),
    )


@admin.register(LigneFiche)
class LigneFicheAdmin(admin.ModelAdmin):
    list_display = ("fiche", "type_ligne", "designation", "quantite", "prix_unitaire", "montant_ligne")
    list_filter = ("type_ligne",)
    search_fields = ("fiche__numero", "designation_libre")


@admin.register(OrdrePaiement)
class OrdrePaiementAdmin(admin.ModelAdmin):
    list_display = ("numero", "bc", "montant", "nature", "mode", "statut", "dfc", "dg", "date_creation")
    list_filter = ("statut", "nature", "mode")
    search_fields = ("numero", "bc__numero", "bc__fournisseur__nom")
    readonly_fields = ("numero", "date_creation", "date_modification", "date_visa")
    ordering = ("-date_creation",)


@admin.register(Paiement)
class PaiementAdmin(admin.ModelAdmin):
    list_display = ("numero", "bc", "montant_verse", "nature", "mode", "statut", "comptable", "date_execution")
    list_filter = ("statut", "nature", "mode", "est_acompte")
    search_fields = ("numero", "bc__numero", "reference")
    readonly_fields = ("numero", "solde_restant", "date_creation", "date_modification", "date_execution")
    ordering = ("-date_creation",)