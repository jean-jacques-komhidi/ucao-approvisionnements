"""
Formulaires de l'app approvisionnements.

- FormulaireFEB         : entete de FEB
- FormulaireLigneFiche  : ligne individuelle
- FormSetLignes         : formset dynamique
- FormulaireValidationBC : validation BC (avec option signature en PO)
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
        self.fields["fournisseur"].queryset = Fournisseur.objects.actifs()

        self.fields["taux_tva"] = forms.ChoiceField(
            choices=[("0", "0%"), ("10", "10%"), ("18", "18%")],
            widget=forms.Select(attrs={"class": "champ-formulaire"}),
            label="Taux TVA",
            initial="18",
        )


# ═══════════════════════════════════════════════════════════════════
# FORMULAIRE LIGNE FEB
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
            cleaned["service"] = None
        elif type_ligne == TypeLigne.SERVICE:
            if not service and not designation_libre:
                raise forms.ValidationError(
                    "Selectionner un service ou saisir une designation libre."
                )
            cleaned["article"] = None

        return cleaned


# ═══════════════════════════════════════════════════════════════════
# FORMSET DYNAMIQUE DE LIGNES
# ═══════════════════════════════════════════════════════════════════
FormSetLignes = inlineformset_factory(
    FicheExpression,
    LigneFiche,
    form=FormulaireLigneFiche,
    extra=1,
    can_delete=True,
    min_num=1,
    validate_min=True,
)


# ═══════════════════════════════════════════════════════════════════
# FORMULAIRE VALIDATION BC (DG ou DFC en PO)
# ═══════════════════════════════════════════════════════════════════
class FormulaireValidationBC(forms.Form):
    """Formulaire de validation d'un BC."""

    signe_en_po = forms.BooleanField(
        required=False,
        label="Je signe en Pour Ordre (DG absent)",
        help_text="A cocher si vous etes DFC et que le DG est absent.",
        widget=forms.CheckboxInput(attrs={"class": "champ-checkbox"}),
    )


# ═══════════════════════════════════════════════════════════════════
# FORMULAIRES PAIEMENTS
# ═══════════════════════════════════════════════════════════════════
class FormulaireOrdrePaiement(forms.ModelForm):
    """DFC cree un ordre de paiement pour un BC valide."""

    class Meta:
        from .models import ModePaiement, NaturePaiement, OrdrePaiement

        model = OrdrePaiement
        fields = ["montant", "nature", "mode", "motif"]
        widgets = {
            "montant": forms.NumberInput(attrs={
                "class": "champ-formulaire",
                "step": "0.01",
                "min": "1",
                "placeholder": "Ex : 295000.00",
            }),
            "nature": forms.Select(attrs={"class": "champ-formulaire"}),
            "mode": forms.Select(attrs={"class": "champ-formulaire"}),
            "motif": forms.Textarea(attrs={
                "class": "champ-formulaire",
                "rows": 3,
                "placeholder": "Motif de l'ordre (optionnel)",
            }),
        }


class FormulaireVisaDG(forms.Form):
    """DG vise un ordre de paiement (ou rejette)."""

    accepter = forms.BooleanField(
        required=False,
        label="Accorder le visa",
    )
    motif_rejet = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            "class": "champ-formulaire",
            "rows": 3,
            "placeholder": "Si rejet, indiquer le motif obligatoire",
        }),
        label="Motif de rejet (si refus)",
    )


class FormulaireExecutionPaiement(forms.ModelForm):
    """Comptable execute un paiement."""

    class Meta:
        from .models import ModePaiement, NaturePaiement, Paiement

        model = Paiement
        fields = ["montant_verse", "nature", "mode", "reference"]
        widgets = {
            "montant_verse": forms.NumberInput(attrs={
                "class": "champ-formulaire",
                "step": "0.01",
                "min": "1",
                "placeholder": "Montant a verser",
            }),
            "nature": forms.Select(attrs={"class": "champ-formulaire"}),
            "mode": forms.Select(attrs={"class": "champ-formulaire"}),
            "reference": forms.TextInput(attrs={
                "class": "champ-formulaire",
                "placeholder": "Ex : Cheque 123456 / Virement REF-2026-...",
            }),
        }