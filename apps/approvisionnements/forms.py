"""
Formulaires de l'app approvisionnements.

- FormulaireFEB         : entete de FEB (objet, fournisseur, taux TVA)
- FormulaireLigneFiche  : ligne individuelle (Article ou Service + qte + prix)
- FormSetLignes         : formset dynamique (lignes ajoutees/supprimees en JS)
"""
from django import forms
from django.forms import inlineformset_factory

from apps.referentiels.models import Article, Fournisseur, ServiceExterieur

from .models import FicheExpression, LigneFiche, TypeLigne


# ═══════════════════════════════════════════════════════════════════
# FORMULAIRE ENTETE FEB
# ═══════════════════════════════════════════════════════════════════
class FormulaireFEB(forms.ModelForm):
    """Formulaire de creation/modification de l'entete d'une FEB."""

    motif_action = forms.CharField(
        widget=forms.Textarea(attrs={
            "class": "champ-formulaire",
            "rows": 2,
            "placeholder": "Obligatoire pour modification ou suppression",
        }),
        required=False,
        label="Motif",
    )

    class Meta:
        model = FicheExpression
        fields = ["objet", "fournisseur", "taux_tva"]
        widgets = {
            "objet": forms.TextInput(attrs={
                "class": "champ-formulaire",
                "placeholder": "Ex : Achat fournitures de bureau Q1",
            }),
            "fournisseur": forms.Select(attrs={"class": "champ-formulaire"}),
            "taux_tva": forms.Select(attrs={"class": "champ-formulaire"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Limite aux fournisseurs actifs
        self.fields["fournisseur"].queryset = Fournisseur.objects.actifs()

        # Choix TVA Senegal uniquement
        self.fields["taux_tva"] = forms.ChoiceField(
            choices=[("0", "0%"), ("10", "10%"), ("18", "18%")],
            widget=forms.Select(attrs={"class": "champ-formulaire"}),
            label="Taux TVA",
            initial="18",
        )


# ═══════════════════════════════════════════════════════════════════
# FORMULAIRE LIGNE FEB (utilise dans le formset)
# ═══════════════════════════════════════════════════════════════════
class FormulaireLigneFiche(forms.ModelForm):
    """Formulaire d'une ligne de FEB."""

    class Meta:
        model = LigneFiche
        fields = [
            "type_ligne", "article", "service",
            "designation_libre", "quantite", "prix_unitaire",
        ]
        widgets = {
            "type_ligne": forms.Select(attrs={
                "class": "champ-formulaire ligne-type",
            }),
            "article": forms.Select(attrs={
                "class": "champ-formulaire ligne-article",
            }),
            "service": forms.Select(attrs={
                "class": "champ-formulaire ligne-service",
            }),
            "designation_libre": forms.TextInput(attrs={
                "class": "champ-formulaire ligne-designation",
                "placeholder": "Ou designation libre...",
            }),
            "quantite": forms.NumberInput(attrs={
                "class": "champ-formulaire ligne-quantite",
                "step": "0.01",
                "min": "0",
                "placeholder": "Qte",
            }),
            "prix_unitaire": forms.NumberInput(attrs={
                "class": "champ-formulaire ligne-prix",
                "step": "0.01",
                "min": "0",
                "placeholder": "Prix unitaire",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["article"].queryset = Article.objects.actifs()
        self.fields["service"].queryset = ServiceExterieur.objects.actifs()
        self.fields["article"].required = False
        self.fields["service"].required = False
        self.fields["designation_libre"].required = False

    def clean(self):
        """Verifie qu'au moins une designation est fournie."""
        cleaned = super().clean()

        if self.cleaned_data.get("DELETE"):
            return cleaned

        type_ligne = cleaned.get("type_ligne")
        article = cleaned.get("article")
        service = cleaned.get("service")
        designation_libre = cleaned.get("designation_libre", "").strip()

        if type_ligne == TypeLigne.ARTICLE:
            if not article and not designation_libre:
                raise forms.ValidationError(
                    "Selectionner un article ou saisir une designation libre."
                )
            cleaned["service"] = None  # Force a None
        elif type_ligne == TypeLigne.SERVICE:
            if not service and not designation_libre:
                raise forms.ValidationError(
                    "Selectionner un service ou saisir une designation libre."
                )
            cleaned["article"] = None  # Force a None

        return cleaned


# ═══════════════════════════════════════════════════════════════════
# FORMSET DYNAMIQUE DE LIGNES
# ═══════════════════════════════════════════════════════════════════
FormSetLignes = inlineformset_factory(
    FicheExpression,
    LigneFiche,
    form=FormulaireLigneFiche,
    extra=1,           # 1 ligne vide initiale
    can_delete=True,
    min_num=1,         # Au moins 1 ligne obligatoire
    validate_min=True,
)