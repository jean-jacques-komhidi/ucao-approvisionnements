"""Configuration admin Django pour les referentiels."""
from django.contrib import admin
from django.utils.html import format_html

from .models import Article, Devise, Fournisseur, ServiceExterieur


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ("apercu_image", "designation", "unite", "nature", "est_actif", "date_creation")
    list_filter = ("nature", "unite", "est_actif")
    search_fields = ("designation", "description")
    ordering = ("designation",)
    readonly_fields = ("apercu_grand", "date_creation", "date_modification", "cree_par")
    fieldsets = (
        ("Informations principales", {
            "fields": ("designation", "unite", "nature", "description"),
        }),
        ("Image", {
            "fields": ("image", "apercu_grand"),
        }),
        ("Etat", {
            "fields": ("est_actif",),
        }),
        ("Tracabilite", {
            "fields": ("cree_par", "date_creation", "date_modification"),
            "classes": ("collapse",),
        }),
    )

    def apercu_image(self, obj):
        """Affiche une mini-vignette dans la liste admin."""
        if obj.image:
            return format_html(
                '<img src="{}" style="height: 40px; width: 40px; '
                'object-fit: cover; border-radius: 6px;" />',
                obj.image.url,
            )
        return "—"
    apercu_image.short_description = "Image"

    def apercu_grand(self, obj):
        """Affiche un grand apercu dans le detail admin."""
        if obj.image:
            return format_html(
                '<img src="{}" style="max-height: 200px; max-width: 300px; '
                'border-radius: 8px;" />',
                obj.image.url,
            )
        return "Aucune image"
    apercu_grand.short_description = "Apercu"


@admin.register(ServiceExterieur)
class ServiceExterieurAdmin(admin.ModelAdmin):
    list_display = ("designation", "est_actif", "date_creation")
    list_filter = ("est_actif",)
    search_fields = ("designation", "description")
    ordering = ("designation",)
    readonly_fields = ("date_creation", "date_modification", "cree_par")


@admin.register(Fournisseur)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ("code", "nom", "type_personne", "email", "telephone", "est_actif")
    list_filter = ("type_personne", "est_actif")
    search_fields = ("code", "nom", "email", "ninea")
    ordering = ("code",)
    readonly_fields = ("code", "date_creation", "date_modification", "cree_par")


@admin.register(Devise)
class DeviseAdmin(admin.ModelAdmin):
    list_display = ("code", "libelle", "symbole", "taux_tva", "est_devise_principale", "est_active")
    list_filter = ("est_devise_principale", "est_active")
    search_fields = ("code", "libelle")
    ordering = ("-est_devise_principale", "code")
    readonly_fields = ("date_creation", "date_modification", "gere_par")