"""
Formulaires de l'app referentiels.
"""
from django import forms
from django.core.exceptions import ValidationError

from .models import Article, Devise, Fournisseur, ServiceExterieur


# ═══════════════════════════════════════════════════════════════════
# ARTICLE (avec upload d'image)
# ═══════════════════════════════════════════════════════════════════
class FormulaireArticle(forms.ModelForm):
    """Formulaire de creation/modification d'un article (avec image)."""

    class Meta:
        model = Article
        fields = ["designation", "unite", "nature", "description", "image", "est_actif"]
        widgets = {
            "designation": forms.TextInput(attrs={
                "class": "champ-formulaire",
                "placeholder": "Ex : Ramette de papier A4 80g",
            }),
            "unite": forms.Select(attrs={"class": "champ-formulaire"}),
            "nature": forms.Select(attrs={"class": "champ-formulaire"}),
            "description": forms.Textarea(attrs={
                "class": "champ-formulaire",
                "rows": 3,
                "placeholder": "Informations complementaires (optionnel)",
            }),
            "image": forms.ClearableFileInput(attrs={
                "class": "champ-fichier",
                "accept": "image/jpeg,image/png,image/webp",
            }),
            "est_actif": forms.CheckboxInput(attrs={"class": "champ-checkbox"}),
        }

    def clean_image(self):
        """Valide la taille et le type de l'image."""
        image = self.cleaned_data.get("image")

        if image and hasattr(image, "size"):
            # Limite a 5 Mo
            taille_max = 5 * 1024 * 1024
            if image.size > taille_max:
                raise ValidationError(
                    f"L'image ne doit pas depasser 5 Mo. "
                    f"Taille actuelle : {image.size / (1024*1024):.1f} Mo."
                )

            # Verifier le type MIME
            types_autorises = ["image/jpeg", "image/png", "image/webp"]
            type_image = getattr(image, "content_type", "")
            if type_image and type_image not in types_autorises:
                raise ValidationError(
                    "Format non autorise. Formats acceptes : JPG, PNG, WebP."
                )

        return image


# ═══════════════════════════════════════════════════════════════════
# SERVICE EXTERIEUR
# ═══════════════════════════════════════════════════════════════════
class FormulaireServiceExterieur(forms.ModelForm):
    """Formulaire de creation/modification d'un service exterieur."""

    class Meta:
        model = ServiceExterieur
        fields = ["designation", "description", "est_actif"]
        widgets = {
            "designation": forms.TextInput(attrs={
                "class": "champ-formulaire",
                "placeholder": "Ex : Maintenance climatisation",
            }),
            "description": forms.Textarea(attrs={
                "class": "champ-formulaire",
                "rows": 3,
            }),
            "est_actif": forms.CheckboxInput(attrs={"class": "champ-checkbox"}),
        }


# ═══════════════════════════════════════════════════════════════════
# FOURNISSEUR
# ═══════════════════════════════════════════════════════════════════
class FormulaireFournisseur(forms.ModelForm):
    """Formulaire de creation/modification d'un fournisseur."""

    class Meta:
        model = Fournisseur
        fields = [
            "nom", "type_personne", "telephone", "email",
            "adresse", "ninea", "rccm", "est_actif",
        ]
        widgets = {
            "nom": forms.TextInput(attrs={
                "class": "champ-formulaire",
                "placeholder": "Ex : SARL Bureau Plus",
            }),
            "type_personne": forms.Select(attrs={"class": "champ-formulaire"}),
            "telephone": forms.TextInput(attrs={
                "class": "champ-formulaire",
                "placeholder": "Ex : +221 33 123 45 67",
            }),
            "email": forms.EmailInput(attrs={
                "class": "champ-formulaire",
                "placeholder": "contact@fournisseur.sn",
            }),
            "adresse": forms.Textarea(attrs={
                "class": "champ-formulaire",
                "rows": 2,
                "placeholder": "Rue, ville, pays",
            }),
            "ninea": forms.TextInput(attrs={"class": "champ-formulaire"}),
            "rccm": forms.TextInput(attrs={"class": "champ-formulaire"}),
            "est_actif": forms.CheckboxInput(attrs={"class": "champ-checkbox"}),
        }


# ═══════════════════════════════════════════════════════════════════
# DEVISE
# ═══════════════════════════════════════════════════════════════════
class FormulaireDevise(forms.ModelForm):
    """Formulaire de creation/modification d'une devise (DFC uniquement)."""

    class Meta:
        model = Devise
        fields = [
            "code", "libelle", "symbole", "taux_tva",
            "est_devise_principale", "est_active",
        ]
        widgets = {
            "code": forms.TextInput(attrs={
                "class": "champ-formulaire",
                "placeholder": "Ex : XOF",
                "maxlength": 5,
            }),
            "libelle": forms.TextInput(attrs={
                "class": "champ-formulaire",
                "placeholder": "Ex : Franc CFA BCEAO",
            }),
            "symbole": forms.TextInput(attrs={
                "class": "champ-formulaire",
                "placeholder": "Ex : F CFA",
            }),
            "taux_tva": forms.NumberInput(attrs={
                "class": "champ-formulaire",
                "step": "0.01",
            }),
            "est_devise_principale": forms.CheckboxInput(attrs={"class": "champ-checkbox"}),
            "est_active": forms.CheckboxInput(attrs={"class": "champ-checkbox"}),
        }

    def clean_taux_tva(self):
        """Verifie que le taux est dans la liste autorisee (Senegal)."""
        from django.conf import settings

        taux = self.cleaned_data["taux_tva"]
        taux_autorises = getattr(settings, "TVA_AUTORISEES", [0, 10, 18])

        if int(taux) not in taux_autorises:
            raise ValidationError(
                f"Taux TVA non autorise. Au Senegal, seuls {taux_autorises} sont valides."
            )
        return taux

    def clean_code(self):
        """Force le code en majuscules."""
        return self.cleaned_data["code"].upper()